from django.test import TestCase, Client
from django.urls import reverse

class BungieAPITests(TestCase):
    def setUp(self):
        # Setup code here, if necessary (e.g., create user, set up auth)
        self.client = Client()

    def test_player_data_endpoint(self):
        # You need to have a player ID that you know will return data
        player_id = 'zooloo#7766'  # Replace with a valid player ID
        response = self.client.get(reverse('player_data', kwargs={'player_id': player_id}))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Profile', response.json())  # Check for keys or values expected in response

        print(response.json())

