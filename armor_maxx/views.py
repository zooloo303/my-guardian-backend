import re
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
from django.core.exceptions import ObjectDoesNotExist
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from .models import ArmorDefinition, ArmorPiece, ArmorModifier, ArmorOptimizationRequest
from .utils import get_element_from_subclass, SUBCLASS_TO_ELEMENT_MAP, get_armor_type, get_item_class

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
        except Exception as e:
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
            return Response({'error': 'Error generating optimization suggestion'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        claude_response = self.call_claude_api(prompt)
        logger.info(f"Claude's response details: {claude_response}")
        # Parse and enhance Claude's response
        enhanced_response = self.enhance_response(claude_response.completion)
        logger.info(f"Enhanced response: {enhanced_response}")

        if enhanced_response is None:
            return Response({'error': 'Failed to parse optimization suggestion'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save the optimization request and result
        ArmorOptimizationRequest.objects.create(
            user=user,
            exotic_id=exotic_id,
            subclass=subclass_id,
            character_id=character_id,
            result=json.dumps(enhanced_response)  # Store the enhanced response as JSON string
        )

        return Response(enhanced_response)  

    def enhance_response(self, claude_response):
        logger.info("Starting to enhance Claude's response")
        logger.debug(f"Claude's full response: {claude_response}")

        try:
            # Find the JSON object using regex
            json_match = re.search(r'```json\s*({\s*"armor_pieces":.+?})\s*```', claude_response, re.DOTALL)
            if not json_match:
                logger.error("No JSON object found in Claude's response")
                raise ValueError("No JSON object found in Claude's response")
            
            # Extract the JSON string
            json_str = json_match.group(1)
            logger.debug(f"Extracted JSON string: {json_str}")

            # Parse the JSON
            enhanced_response = json.loads(json_str)
            logger.info("Successfully parsed JSON")
            
            # Validate the structure
            required_keys = ['armor_pieces', 'fragments', 'mods', 'total_stats', 'explanation']
            for key in required_keys:
                if key not in enhanced_response:
                    logger.error(f"Missing required key in response: {key}")
                    raise ValueError(f"Missing required key in response: {key}")
            
            # Add item_hash to armor pieces
            for armor_piece in enhanced_response['armor_pieces']:
                instance_id = armor_piece['instanceId']
                try:
                    db_armor_piece = ArmorPiece.objects.get(item_id=instance_id)
                    armor_piece['item_hash'] = db_armor_piece.item_hash
                    
                    try:
                        armor_def = ArmorDefinition.objects.get(item_hash=db_armor_piece.item_hash)
                        armor_piece['name'] = armor_def.name
                    except ArmorDefinition.DoesNotExist:
                        logger.warning(f"ArmorDefinition not found for item_hash: {db_armor_piece.item_hash}")
                except ArmorPiece.DoesNotExist:
                    logger.error(f"ArmorPiece not found for instance_id: {instance_id}")
                    armor_piece['item_hash'] = None

            # Add item_hash to mods
            for mod in enhanced_response['mods']:
                try:
                    db_mod = ArmorModifier.objects.get(name__iexact=mod['name'], modifier_type='ARMOR_MOD')
                    mod['item_hash'] = db_mod.item_hash
                except ArmorModifier.DoesNotExist:
                    logger.warning(f"ArmorModifier not found for mod: {mod['name']}")
                    mod['item_hash'] = None

            # Add item_hash to fragments
            for fragment in enhanced_response['fragments']:
                try:
                    db_fragment = ArmorModifier.objects.get(name__iexact=fragment['name'], modifier_type='SUBCLASS_FRAGMENT')
                    fragment['item_hash'] = db_fragment.item_hash
                except ArmorModifier.DoesNotExist:
                    logger.warning(f"ArmorModifier not found for fragment: {fragment['name']}")
                    fragment['item_hash'] = None

            logger.info("Response structure validation passed")
            logger.debug(f"Final enhanced response: {enhanced_response}")
            return enhanced_response

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude's response: {e}")
            logger.error(f"Problematic JSON string: {json_str if 'json_str' in locals() else 'Not extracted'}")
            return None
        except ValueError as e:
            logger.error(str(e))
            return None
        except Exception as e:
            logger.error(f"Unexpected error in enhance_response: {str(e)}")
            return None

    def parse_armor_pieces(self, section, enhanced_response):
        lines = section.split('\n')[1:]  # Skip the "1. Armor Pieces:" line
        for line in lines:
            match = re.match(r"- (.+): (.+) \((.+)\)", line)
            if match:
                armor_type, name, stats_string = match.groups()
                armor_piece = {
                    "type": armor_type.strip(),
                    "name": name.strip(),
                    "stats": {}
                }
                
                # Split stats and handle potential formatting issues
                stats = stats_string.split(', ')
                for stat in stats:
                    stat_parts = stat.split(': ')
                    if len(stat_parts) == 2:
                        stat_name, stat_value = stat_parts
                        try:
                            armor_piece["stats"][stat_name.strip()] = int(stat_value)
                        except ValueError:
                            # If we can't convert to int, skip this stat
                            logger.warning(f"Could not parse stat value for {stat_name}: {stat_value}")
                    else:
                        # Log unexpected stat format
                        logger.warning(f"Unexpected stat format: {stat}")
                
                # Here we would typically set instanceId and itemHash
                # For now, we'll set them to placeholder values
                armor_piece["instanceId"] = "placeholder_instance_id"
                armor_piece["itemHash"] = "placeholder_item_hash"
                
                enhanced_response["armor_pieces"].append(armor_piece)
            else:
                # Log lines that don't match the expected format
                logger.warning(f"Could not parse armor piece line: {line}")

    def parse_fragments(self, section, enhanced_response):
        lines = section.split('\n')[1:]  # Skip the "2. Fragments:" line
        for line in lines:
            fragment_name = line.replace("-", "").strip()
            enhanced_response["fragments"].append({"name": fragment_name})

    def parse_mods(self, section, enhanced_response):
        lines = section.split('\n')[1:]  # Skip the "3. Mods:" line
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                slot = parts[0].replace("-", "").strip()
                mod = parts[1].strip()
                enhanced_response["mods"].append({"slot": slot, "name": mod})

    def parse_stats(self, section, enhanced_response):
        lines = section.split('\n')[1:]  # Skip the "4. Stats:" line
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                stat = parts[0].replace("-", "").strip()
                value = int(parts[1].strip())
                enhanced_response["total_stats"][stat] = value

    def get_item_hash_from_instance_id(self, instance_id):
        try:
            armor_piece = ArmorPiece.objects.get(item_id=instance_id)
            return armor_piece.item_hash
        except ArmorPiece.DoesNotExist:
            return None  # or a default value, or raise an exception

    def handle_chat(self, user, chat_input):
        prompt = f"{HUMAN_PROMPT} As a Destiny 2 expert, please respond to the following question or comment: {chat_input}\n\n{AI_PROMPT}"
        try:
            response = self.call_claude_api(prompt)
            return Response({'response': response.completion})
        except Exception as e:
            return Response({'error': 'Error processing chat request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def sync_armor_data(self, user, character_id, chosen_exotic_id):
        try:
            access_token = refresh_bungie_token(user.username)
        except Exception as e:
            raise Exception(f"Failed to refresh token: {str(e)}")

        headers = {
            'X-API-Key': settings.SOCIAL_AUTH_BUNGIE_API_KEY,
            'Authorization': f'Bearer {access_token}',
        }

        url = f"https://www.bungie.net/Platform/Destiny2/{user.membership_type}/Profile/{user.primary_membership_id}/?components=102,200,201,205,304"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()['Response']
        except requests.RequestException as e:
            raise

        if 'characters' not in data:
            raise KeyError("'characters' key not found in API response")

        if character_id not in data['characters']['data']:
            raise KeyError(f"Character ID {character_id} not found in API response")

        armor_pieces = []

        def process_armor(item, inventory_type):
            item_hash = item['itemHash']
            item_instance_id = item.get('itemInstanceId')
            
            if not item_instance_id or item_instance_id not in data['itemComponents']['stats']['data']:
                return

            try:
                armor_def = ArmorDefinition.objects.get(item_hash=str(item_hash))
            except ArmorDefinition.DoesNotExist:
                return

            item_stats = data['itemComponents']['stats']['data'][item_instance_id]['stats']
            
            armor_type = get_armor_type(armor_def.item_category_hashes)
            if not armor_type:
                return

            item_class = get_item_class(armor_def.item_category_hashes)
            is_exotic = armor_def.tier_type == 6

            # Check if the armor is suitable for the current character
            character_class_type = data['characters']['data'][character_id]['classType']
            character_class = ['TITAN', 'HUNTER', 'WARLOCK'][character_class_type]
            
            if item_class not in [character_class, 'ALL']:
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
                
        # Process all inventories (corrected indentation)
        for inventory_type, inventory_data in [
            ('profile', data['profileInventory']['data']['items']),
            ('character', data['characterInventories']['data'][character_id]['items']),
            ('equipped', data['characterEquipment']['data'][character_id]['items'])
        ]:
            for item in inventory_data:
                process_armor(item, inventory_type)

        # Update or create ArmorPiece objects in the database
        saved_count = 0
        for armor in armor_pieces:
            try:
                if not armor['armor_type']:
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
            except Exception as e:
                logger.error(f"Error saving armor piece {armor['item_id']}: {str(e)}")

        # Remove old armor pieces that are no longer in the inventory
        current_item_ids = [armor['item_id'] for armor in armor_pieces]
        deleted_count, _ = ArmorPiece.objects.filter(user=user, character_id=character_id).exclude(item_id__in=current_item_ids).delete()
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
        
        prompt = f'''{HUMAN_PROMPT} As a Destiny 2 armor optimization expert and grumpy sweeper robot, please analyze the following armor pieces, subclass fragments, and armor mods to suggest the best loadout for maximizing overall stats. The player is using the {subclass_name} subclass and must use the exotic armor piece with ID {exotic_id}. The stat priorities are (in order): {', '.join(priority_names)}. Here's the data:

        Armor Pieces: {json.dumps(armor_data, indent=2)}

        Subclass Fragments: {json.dumps(fragment_data, indent=2)}

        Armor Mods: {json.dumps(armor_mod_data, indent=2)}

        User's input: {chat_input}

        Please provide your suggestion in the following JSON format, enclosed in a code block:

        ```json
        {{
            "armor_pieces": [
                {{
                    "type": "Helmet",
                    "instanceId": "item_instance_id",
                    "name": "Item Name"
                }},
                // ... other armor pieces
            ],
            "fragments": [
                {{
                    "name": "Fragment Name"
                }},
                // ... other fragments (max 4)
            ],
            "mods": [
                {{
                    "slot": "Helmet",
                    "name": "Mod Name"
                }},
                // ... other mods
            ],
            "total_stats": {{
                "mobility": 0,
                "resilience": 0,
                "recovery": 0,
                "discipline": 0,
                "intellect": 0,
                "strength": 0
            }},
            "explanation": "Your explanation here"
        }}
        ```
        
        Ensure that you follow this JSON structure exactly in your response, enclosed in the code block as shown.

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

   