import json
import requests
from users.models import NewUser
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from users.views import refresh_bungie_token
from .models import ArmorPiece, SubclassFragment, ArmorOptimizationRequest


class OptimizeArmor(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        exotic_id = request.data.get('exotic_id')
        subclass = request.data.get('subclass')

        try:
            user = NewUser.objects.get(username=username)
        except NewUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Sync armor data
        self.sync_armor_data(user)

        armor_pieces = ArmorPiece.objects.filter(user=user)
        fragments = SubclassFragment.objects.filter(subclass=subclass)

        # Prepare data for Claude
        armor_data = [
            {
                'id': piece.item_id,
                'hash': piece.item_hash,
                'type': piece.armor_type,
                'is_exotic': piece.is_exotic,
                'stats': {
                    'mobility': piece.mobility,
                    'resilience': piece.resilience,
                    'recovery': piece.recovery,
                    'discipline': piece.discipline,
                    'intellect': piece.intellect,
                    'strength': piece.strength
                }
            } for piece in armor_pieces
        ]

        fragment_data = [
            {
                'name': fragment.name,
                'stat_mods': {
                    'mobility': fragment.mobility_mod,
                    'resilience': fragment.resilience_mod,
                    'recovery': fragment.recovery_mod,
                    'discipline': fragment.discipline_mod,
                    'intellect': fragment.intellect_mod,
                    'strength': fragment.strength_mod
                }
            } for fragment in fragments
        ]

        # Prepare prompt for Claude
        prompt = f'''{HUMAN_PROMPT} As a Destiny 2 armor optimization expert, please analyze the following armor pieces and subclass fragments to suggest the best loadout for maximizing overall stats. The player must use the exotic armor piece with ID {exotic_id}. Here's the data:

        Armor Pieces: {json.dumps(armor_data, indent=2)}

        Subclass Fragments: {json.dumps(fragment_data, indent=2)}

        Please provide your suggestion in the following format:
        1. List of recommended armor pieces (including the specified exotic)
        2. List of recommended subclass fragments
        3. Resulting stat totals
        4. Brief explanation of your choices

        {AI_PROMPT}'''

        # Call Claude API
        anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = anthropic.completions.create(
            model="claude-2",
            prompt=prompt,
            max_tokens_to_sample=1000,
        )

        # Save the optimization request and result
        ArmorOptimizationRequest.objects.create(
            user=user,
            exotic_id=exotic_id,
            subclass=subclass,
            result=response.completion
        )

        # Process and return Claude's response
        return Response({
            'suggestion': response.completion
        })

    def sync_armor_data(self, user):
        try:
            access_token = refresh_bungie_token(user.username)
        except Exception as e:
            raise Exception(f"Failed to refresh token: {str(e)}")

        headers = {
            'X-API-Key': settings.BUNGIE_API_KEY,
            'Authorization': f'Bearer {access_token}',
        }

        # Fetch profile data
        url = f"https://www.bungie.net/Platform/Destiny2/{user.membership_type}/Profile/{user.primary_membership_id}/?components=102,201,205,304"
        response = requests.get(url, headers=headers)
        data = response.json()['Response']

        armor_pieces = []

        # Function to process armor items
        def process_armor(item, inventory_type):
            item_hash = item['itemHash']
            item_instance_id = item.get('itemInstanceId')
            
            if item_instance_id and item_instance_id in data['itemComponents']['stats']['data']:
                item_stats = data['itemComponents']['stats']['data'][item_instance_id]['stats']
                item_details = data['itemComponents']['instances']['data'][item_instance_id]
                
                armor_type_hash = item_details['bucketHash']
                is_exotic = item_details['tierType'] == 6  # 6 is the tierType for Exotic items
                
                stats = {
                    'mobility': item_stats['2996146975']['value'],
                    'resilience': item_stats['392767087']['value'],
                    'recovery': item_stats['1943323491']['value'],
                    'discipline': item_stats['1735777505']['value'],
                    'intellect': item_stats['144602215']['value'],
                    'strength': item_stats['4244567218']['value']
                }
                
                armor_pieces.append({
                    'item_id': item_instance_id,
                    'item_hash': item_hash,
                    'armor_type': armor_type_hash,
                    'is_exotic': is_exotic,
                    'inventory_type': inventory_type,
                    **stats
                })

        # Process profile inventory
        for item in data['profileInventory']['data']['items']:
            process_armor(item, 'profile')

        # Process character inventories and equipment
        for character_id, inventory in data['characterInventories']['data'].items():
            for item in inventory['items']:
                process_armor(item, 'character')

        for character_id, equipment in data['characterEquipment']['data'].items():
            for item in equipment['items']:
                process_armor(item, 'equipped')

        # Update or create ArmorPiece objects
        for armor in armor_pieces:
            ArmorPiece.objects.update_or_create(
                user=user,
                item_id=armor['item_id'],
                defaults={
                    'item_hash': armor['item_hash'],
                    'armor_type': armor['armor_type'],
                    'is_exotic': armor['is_exotic'],
                    'mobility': armor['mobility'],
                    'resilience': armor['resilience'],
                    'recovery': armor['recovery'],
                    'discipline': armor['discipline'],
                    'intellect': armor['intellect'],
                    'strength': armor['strength']
                }
            )

        # Optionally, remove any armor pieces that no longer exist in the player's inventory
        current_item_ids = [armor['item_id'] for armor in armor_pieces]
        ArmorPiece.objects.filter(user=user).exclude(item_id__in=current_item_ids).delete()

        return len(armor_pieces)