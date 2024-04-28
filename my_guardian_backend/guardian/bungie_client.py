import os
from bungio import Client
from bungio.models import BungieMembershipType
from dotenv import load_dotenv
# from .models import Guardian

class BungieClient:
    def __init__(self):
        load_dotenv()
        self.client = Client(
            bungie_client_id=os.getenv('OAUTH_CLIENT_ID'),
            bungie_client_secret=os.getenv('OAUTH_CLIENT_SECRET'),
            bungie_token=os.getenv('BUNGIE_API_KEY'),
        )

    async def get_my_characters(self):
        #  # Fetch the Guardian object for the user
        # guardian = Guardian.objects.get(user=self.user)

        # # Use the membership_id and membership_type from the Guardian object
        # membership_id = guardian.membership_id
        # membership_type = BungieMembershipType[guardian.membership_type]

        membership_id = '4611686018433783788'
        membership_type = BungieMembershipType.TIGER_PSN

        my_characters = []
        try:
            user_profile = await self.client.api.get_profile(
                destiny_membership_id=membership_id,
                membership_type=membership_type,
                components=["Profiles", "Characters"]
            )
            
            for character_id, character_data in user_profile.characters.data.items():
                character_info = {
                    "Character_ID": character_id,
                    "Class_Type": getattr(character_data.class_type, 'name', 'Class Type not found'),
                    "Race_Type": getattr(character_data.race_type, 'name', 'Race Type not found'),
                    "Light_Level": getattr(character_data, 'light', 'Light Level not available')
                }
                my_characters.append(character_info)

        except Exception as e:
            print(f"Failed to fetch user data due to: {e}")

        return my_characters
