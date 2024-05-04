import pydest
import os
from dotenv import load_dotenv

class BungieClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('BUNGIE_API_KEY')

    async def get_player_data(self, player_id):
        bungie_name, bungie_code = player_id.split("#")
        destiny = pydest.Pydest(self.api_key)

        # Search for the player
        response = await destiny.api.search_destiny_player(-1, f"{bungie_name}#{bungie_code}")
        if response['ErrorCode'] != 1:
            print(f"Error searching player: {response['Message']}")
            await destiny.close()
            return

        # Get the player's membership ID and type
        membership_id = response['Response'][0]['membershipId']
        membership_type = response['Response'][0]['membershipType']

        # Get the player's profile
        response = await destiny.api.get_profile(membership_type, membership_id, [100, 200, 205])
        if response['ErrorCode'] != 1:
            print(f"Error getting profile: {response['Message']}")
            await destiny.close()
            return

        # Close the Pydest client
        await destiny.close()

        # Return the player's profile, characters, and character equipment
        return {
            "Profile": response['Response']['profile'],
            "Characters": response['Response']['characters'],
            "CharacterEquipment": response['Response']['characterEquipment']
        }
