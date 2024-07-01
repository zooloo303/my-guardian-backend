import json
import logging
import requests
from django.conf import settings
from users.models import NewUser
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from users.views import refresh_bungie_token
from armor_maxx.models import ArmorDefinition
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from .utils import get_element_from_subclass, SUBCLASS_TO_ELEMENT_MAP, get_armor_type, get_item_class
from .models import ArmorPiece, ArmorModifier, ArmorOptimizationRequest

logger = logging.getLogger(__name__)

class OptimizeArmor(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        exotic_id = request.data.get('exoticId', {}).get('instanceId')
        exotic_hash = request.data.get('exoticId', {}).get('itemHash')
        subclass_id = request.data.get('subclass')
        stat_priorities = request.data.get('statPriorities', [])
        chat_input = request.data.get('chatInput')
        character_id = request.data.get('characterId')

        try:
            user = NewUser.objects.get(username=username)
        except NewUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if this is a chat-only request
        if not exotic_id and not subclass_id:
            return self.handle_chat(user, chat_input)

        # Get the element type from the subclass ID
        element_type = get_element_from_subclass(subclass_id)

         # Sync armor data
        try:
            armor_count = self.sync_armor_data(user, character_id, exotic_id)
            # logger.info(f"Synced {armor_count} armor pieces for user {username}, character {character_id}")
        except Exception as e:
            # logger.error(f"Error syncing armor data: {str(e)}")
            return Response({'error': 'Error syncing armor data'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Fetch armor pieces, fragments, and mods
        armor_pieces = ArmorPiece.objects.filter(user=user, character_id=character_id)
        fragments = ArmorModifier.objects.filter(modifier_type='SUBCLASS_FRAGMENT', subclass=element_type)
        armor_mods = ArmorModifier.objects.filter(modifier_type='ARMOR_MOD')

        # Prepare data for Claude
        armor_data, fragment_data, armor_mod_data = self.prepare_data_for_claude(
            armor_pieces, fragments, armor_mods, exotic_id, exotic_hash, stat_priorities
        )

        # Prepare prompt for Claude
        prompt = self.prepare_claude_prompt(armor_data, fragment_data, armor_mod_data, exotic_id, stat_priorities, chat_input, subclass_id)

        # Call Claude API
        try:
            response = self.call_claude_api(prompt)
        except Exception as e:
            # logger.error(f"Error calling Claude API: {str(e)}")
            return Response({'error': 'Error generating optimization suggestion'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        # Save the optimization request and result
        ArmorOptimizationRequest.objects.create(
            user=user,
            exotic_id=exotic_id,
            subclass=subclass_id,
            character_id=character_id,
            result=response.completion
        )

        return Response({
            'suggestion': response.completion
        })

    def handle_chat(self, user, chat_input):
        prompt = f"{HUMAN_PROMPT} As a Destiny 2 expert, please respond to the following question or comment: {chat_input}\n\n{AI_PROMPT}"
        try:
            response = self.call_claude_api(prompt)
            return Response({'response': response.completion})
        except Exception as e:
            # logger.error(f"Error handling chat request: {str(e)}")
            return Response({'error': 'Error processing chat request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def sync_armor_data(self, user, character_id, chosen_exotic_id):
        # logger.info(f"Starting armor sync for user {user.username}, character {character_id}")
        try:
            access_token = refresh_bungie_token(user.username)
            # logger.info(f"Successfully refreshed token for user {user.username}")
        except Exception as e:
            # logger.error(f"Failed to refresh token for user {user.username}: {str(e)}")
            raise Exception(f"Failed to refresh token: {str(e)}")

        headers = {
            'X-API-Key': settings.SOCIAL_AUTH_BUNGIE_API_KEY,
            'Authorization': f'Bearer {access_token}',
        }

        url = f"https://www.bungie.net/Platform/Destiny2/{user.membership_type}/Profile/{user.primary_membership_id}/?components=102,200,201,205,304"
        
        try:
            # logger.info(f"Sending request to Bungie API for user {user.username}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()['Response']
            # logger.info(f"Successfully received data from Bungie API for user {user.username}")
        except requests.RequestException as e:
            # logger.error(f"Error fetching data from Bungie API: {str(e)}")
            raise

        if 'characters' not in data:
            # logger.error(f"'characters' key not found in API response for user {user.username}")
            raise KeyError("'characters' key not found in API response")

        if character_id not in data['characters']['data']:
            # logger.error(f"Character ID {character_id} not found in API response for user {user.username}")
            raise KeyError(f"Character ID {character_id} not found in API response")

        armor_pieces = []

        def process_armor(item, inventory_type):
            item_hash = item['itemHash']
            item_instance_id = item.get('itemInstanceId')
            
            # logger.debug(f"Processing item: hash={item_hash}, instance_id={item_instance_id}, inventory_type={inventory_type}")
            
            if not item_instance_id or item_instance_id not in data['itemComponents']['stats']['data']:
                # logger.debug(f"Skipping item {item_hash}: No instance ID or stats data")
                return

            try:
                armor_def = ArmorDefinition.objects.get(item_hash=str(item_hash))
                # logger.debug(f"Found armor definition for item {item_hash}")
            except ArmorDefinition.DoesNotExist:
                # logger.warning(f"Armor definition not found for item hash: {item_hash}")
                return

            item_stats = data['itemComponents']['stats']['data'][item_instance_id]['stats']
            
            armor_type = get_armor_type(armor_def.item_category_hashes)
            if not armor_type:
                # logger.warning(f"Could not determine armor type for item {item_hash}. Item category hashes: {armor_def.item_category_hashes}")
                return

            item_class = get_item_class(armor_def.item_category_hashes)
            is_exotic = armor_def.tier_type == 6

            # logger.debug(f"Item details: armor_type={armor_type}, item_class={item_class}, is_exotic={is_exotic}, tier_type={armor_def.tier_type}")

            # Check if the armor is suitable for the current character
            character_class_type = data['characters']['data'][character_id]['classType']
            character_class = ['TITAN', 'HUNTER', 'WARLOCK'][character_class_type]
            
            if item_class not in [character_class, 'ALL']:
                # logger.info(f"Skipping armor for different class: {item_hash} (Class: {item_class}, Current: {character_class})")
                return

            # Process only Legendary armor and the chosen Exotic
            if armor_def.tier_type == 5 or (is_exotic and item_instance_id == chosen_exotic_id):
                stats = {
                    'mobility': item_stats.get('2996146975', {}).get('value', 0),
                    'resilience': item_stats.get('392767087', {}).get('value', 0),
                    'recovery': item_stats.get('1943323491', {}).get('value', 0),
                    'discipline': item_stats.get('1735777505', {}).get('value', 0),
                    'intellect': item_stats.get('144602215', {}).get('value', 0),
                    'strength': item_stats.get('4244567218', {}).get('value', 0)
                }
                
                armor_pieces.append({
                    'item_id': item_instance_id,
                    'item_hash': item_hash,
                    'armor_type': armor_type,
                    'is_exotic': is_exotic,
                    'inventory_type': inventory_type,
                    'character_id': character_id,
                    'class_type': item_class,
                    **stats
                })
                # logger.info(f"Added armor piece: {item_instance_id} (Type: {armor_type}, Class: {item_class}, Exotic: {is_exotic})")
            
        # Process all inventories (corrected indentation)
        for inventory_type, inventory_data in [
            ('profile', data['profileInventory']['data']['items']),
            ('character', data['characterInventories']['data'][character_id]['items']),
            ('equipped', data['characterEquipment']['data'][character_id]['items'])
        ]:
            # logger.info(f"Processing {inventory_type} inventory with {len(inventory_data)} items")
            for item in inventory_data:
                process_armor(item, inventory_type)

        # logger.info(f"Processed {len(armor_pieces)} armor pieces for character {character_id}")

        # Update or create ArmorPiece objects in the database
        saved_count = 0
        for armor in armor_pieces:
            try:
                if not armor['armor_type']:
                    # logger.warning(f"Skipping save for armor piece {armor['item_id']} due to missing armor_type")
                    continue

                ArmorPiece.objects.update_or_create(
                    user=user,
                    item_id=armor['item_id'],
                    character_id=character_id,
                    defaults={
                        'item_hash': armor['item_hash'],
                        'armor_type': armor['armor_type'],
                        'is_exotic': armor['is_exotic'],
                        'inventory_type': armor['inventory_type'],
                        'class_type': armor['class_type'],
                        'mobility': armor['mobility'],
                        'resilience': armor['resilience'],
                        'recovery': armor['recovery'],
                        'discipline': armor['discipline'],
                        'intellect': armor['intellect'],
                        'strength': armor['strength']
                    }
                )
                saved_count += 1
                # logger.debug(f"Saved/updated armor piece: {armor['item_id']}")
            except Exception as e:
                logger.error(f"Error saving armor piece {armor['item_id']}: {str(e)}")

        # logger.info(f"Saved {saved_count} armor pieces to the database")

        # Remove old armor pieces that are no longer in the inventory
        current_item_ids = [armor['item_id'] for armor in armor_pieces]
        deleted_count, _ = ArmorPiece.objects.filter(user=user, character_id=character_id).exclude(item_id__in=current_item_ids).delete()
        # logger.info(f"Deleted {deleted_count} old armor pieces for character {character_id}")

        return len(armor_pieces)

    def prepare_data_for_claude(self, armor_pieces, fragments, armor_mods, exotic_id, exotic_hash, stat_priorities):
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
                    'mobility': fragment.mobility,
                    'resilience': fragment.resilience,
                    'recovery': fragment.recovery,
                    'discipline': fragment.discipline,
                    'intellect': fragment.intellect,
                    'strength': fragment.strength
                }
            } for fragment in fragments
        ]

        armor_mod_data = [
            {
                'name': mod.name,
                'stat_mods': {
                    'mobility': mod.mobility,
                    'resilience': mod.resilience,
                    'recovery': mod.recovery,
                    'discipline': mod.discipline,
                    'intellect': mod.intellect,
                    'strength': mod.strength
                }
            } for mod in armor_mods
        ]

        return armor_data, fragment_data, armor_mod_data

    def prepare_claude_prompt(self, armor_data, fragment_data, armor_mod_data, exotic_id, stat_priorities, chat_input, subclass_id):
        stat_names = {
            '2996146975': 'mobility',
            '392767087': 'resilience',
            '1943323491': 'recovery',
            '1735777505': 'discipline',
            '144602215': 'intellect',
            '4244567218': 'strength'
        }
        priority_names = [stat_names.get(stat, stat) for stat in stat_priorities]
        subclass_name = SUBCLASS_TO_ELEMENT_MAP.get(subclass_id, "Unknown Subclass")
        
        prompt = f'''{HUMAN_PROMPT} As a Destiny 2 armor optimization expert, please analyze the following armor pieces, subclass fragments, and armor mods to suggest the best loadout for maximizing overall stats. The player is using the {subclass_name} subclass and must use the exotic armor piece with ID {exotic_id}. The stat priorities are (in order): {', '.join(priority_names)}. Here's the data:

        Armor Pieces: {json.dumps(armor_data, indent=2)}

        Subclass Fragments: {json.dumps(fragment_data, indent=2)}

        Armor Mods: {json.dumps(armor_mod_data, indent=2)}

        User's input: {chat_input}

        Please provide your suggestion in the following format:
        1. List of recommended armor pieces (including the specified exotic)
        - Ensure you include one piece for each armor slot: Helmet, Gauntlets, Chest Armor, Leg Armor, and Class Item
        - Remember that only one exotic can be equipped at a time
        2. List of recommended subclass fragments, no more than four allowed
        3. List of recommended armor mods, only one mod per armor piece allowed
        4. Resulting stat totals (ordered by priority)
        5. Brief explanation of your choices and how they align with the user's priorities

        Rules for optimization:
        - The total of all stats must not exceed 340 points (34 tiers)
        - Each individual stat can't exceed 100 points (10 tiers)
        - Prioritize stats according to the given order, but aim for a balanced build, unless the user specifies otherwise
        - Consider synergies between armor pieces, mods, and fragments
        - Explain any trade-offs made in your choices
        - Ensure the recommendations are compatible with the {subclass_name} subclass

        {AI_PROMPT}'''
        return prompt

    def call_claude_api(self, prompt):
        anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return anthropic.completions.create(
            model="claude-2",
            prompt=prompt,
            max_tokens_to_sample=1000,
        )

   