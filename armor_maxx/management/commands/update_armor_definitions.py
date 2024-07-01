from django.core.management.base import BaseCommand
import requests
from armor_maxx.models import ArmorDefinition

class Command(BaseCommand):
    help = 'Updates the armor definitions from the Destiny 2 manifest'

    def handle(self, *args, **options):
        # Fetch the manifest
        manifest_url = "https://www.bungie.net/Platform/Destiny2/Manifest/"
        response = requests.get(manifest_url)
        manifest = response.json()

        # Get the URL for the DestinyInventoryItemDefinition
        item_definition_url = f"https://www.bungie.net{manifest['Response']['jsonWorldComponentContentPaths']['en']['DestinyInventoryItemDefinition']}"

        # Fetch the item definitions
        item_definitions = requests.get(item_definition_url).json()

        # Process and store armor definitions
        armor_count = 0
        for item_hash, item_data in item_definitions.items():
            if item_data['itemType'] == 2:  # 2 is for Armor
                ArmorDefinition.objects.update_or_create(
                    item_hash=item_hash,
                    defaults={
                        'name': item_data['displayProperties']['name'],
                        'tier_type': item_data['inventory']['tierType'],
                        'item_type': item_data['itemTypeDisplayName'],
                        'item_sub_type': item_data['itemSubType'],
                        'item_category_hashes': item_data.get('itemCategoryHashes', [])
                    }
                )
                armor_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {armor_count} armor definitions'))