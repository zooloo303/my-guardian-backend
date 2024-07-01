# armor_maxx/management/commands/populate_armor_modifiers.py
import requests
from django.core.management.base import BaseCommand
from armor_maxx.models import ArmorModifier
from django.conf import settings

class Command(BaseCommand):
    help = 'Fetches mod data from Bungie API and populates the ArmorModifier table'

    def handle(self, *args, **options):
        destiny_item_defs_url = "http://www.bungie.net/common/destiny2_content/json/en/DestinyInventoryItemDefinition-c2aab5db-09a6-4170-85dd-91599475546b.json"
        destiny_stat_defs_url = "http://www.bungie.net/common/destiny2_content/json/en/DestinyStatDefinition-c2aab5db-09a6-4170-85dd-91599475546b.json"

        # Fetch the JSON data from the URLs
        self.stdout.write("Fetching item definitions...")
        response_item_defs = requests.get(destiny_item_defs_url)
        destiny_item_defs = response_item_defs.json()

        self.stdout.write("Fetching stat definitions...")
        response_stat_defs = requests.get(destiny_stat_defs_url)
        destiny_stat_defs = response_stat_defs.json()

        self.stdout.write("Processing mod data...")
        mods = self.get_mods_from_destiny_item_defs(destiny_item_defs, destiny_stat_defs)

        self.stdout.write(f"Populating ArmorModifier table with {len(mods)} mods...")
        for item_hash, mod_data in mods.items():
            ArmorModifier.objects.update_or_create(
                item_hash=item_hash,
                defaults={
                    'name': mod_data['displayProperties']['name'],
                    'description': mod_data['displayProperties'].get('description', ''),
                    'modifier_type': 'ARMOR_MOD' if 'General Armor Mod' in mod_data['itemTypeDisplayName'] else 'SUBCLASS_FRAGMENT',
                    'icon_url': f"https://www.bungie.net{mod_data['displayProperties'].get('icon', '')}",
                    'subclass': mod_data['itemTypeDisplayName'].split()[0] if 'Fragment' in mod_data['itemTypeDisplayName'] else '',
                    'mobility': next((stat['value'] for stat in mod_data['investmentStats'] if stat['statName'] == 'Mobility'), 0),
                    'resilience': next((stat['value'] for stat in mod_data['investmentStats'] if stat['statName'] == 'Resilience'), 0),
                    'recovery': next((stat['value'] for stat in mod_data['investmentStats'] if stat['statName'] == 'Recovery'), 0),
                    'discipline': next((stat['value'] for stat in mod_data['investmentStats'] if stat['statName'] == 'Discipline'), 0),
                    'intellect': next((stat['value'] for stat in mod_data['investmentStats'] if stat['statName'] == 'Intellect'), 0),
                    'strength': next((stat['value'] for stat in mod_data['investmentStats'] if stat['statName'] == 'Strength'), 0),
                    'item_type_display_name': mod_data['itemTypeDisplayName'],
                    'is_conditionally_active': any(stat['isConditionallyActive'] for stat in mod_data['investmentStats'])
                }
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated ArmorModifier table'))

    def get_mods_from_destiny_item_defs(self, destiny_item_defs, destiny_stat_defs):
        mods = {}
        target_categories = {4104513227, 1043342778}  # armor mods and subclass mods
        
        self.stdout.write(f"Total items in destiny_item_defs: {len(destiny_item_defs)}")
        
        for item_hash, item_def in destiny_item_defs.items():
            item_category_hashes = set(item_def.get('itemCategoryHashes', []))
            investment_stats = item_def.get('investmentStats', [])
            
            if target_categories.intersection(item_category_hashes):
                self.stdout.write(f"Found item in target category: {item_def['displayProperties']['name']}")
                
                valid_investment_stats = []
                for stat in investment_stats:
                    if stat['value'] >= 5:
                        stat_name = destiny_stat_defs[str(stat['statTypeHash'])]['displayProperties']['name']
                        valid_investment_stats.append({
                            'statTypeHash': stat['statTypeHash'],
                            'statName': stat_name,
                            'value': stat['value'],
                            'isConditionallyActive': stat['isConditionallyActive']
                        })
                
                if valid_investment_stats:
                    mods[item_hash] = {
                        'displayProperties': item_def['displayProperties'],
                        'itemTypeDisplayName': item_def.get('itemTypeDisplayName', ''),
                        'itemCategoryHashes': item_def.get('itemCategoryHashes', []),
                        'perks': item_def.get('perks', []),
                        'investmentStats': valid_investment_stats
                    }
                    self.stdout.write(f"Added mod: {item_def['displayProperties']['name']}")
        
        self.stdout.write(f"Total mods found: {len(mods)}")
        return mods