# bungie_oauth/provider.py
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider

class BungieProvider(OAuth2Provider):
    id = 'bungie'  # Unique identifier for your provider
    name = 'Bungie'

    def get_default_scope(self):
        return ['ReadBasicUserProfile']

    def extract_uid(self, data):
        return str(data['membership_id'])

    def extract_common_fields(self, data):
        return dict(username=data['displayName'], email=data.get('email', ''))
