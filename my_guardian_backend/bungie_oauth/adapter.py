# bungie_oauth/adapter.py
import requests
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter
from .provider import BungieProvider

class BungieOAuth2Adapter(OAuth2Adapter):
    provider_id = BungieProvider.id
    access_token_url = 'https://www.bungie.net/platform/app/oauth/token/'
    authorize_url = 'https://www.bungie.net/en/oauth/authorize'
    profile_url = 'https://www.bungie.net/platform/User/GetBungieAccount/'

    def complete_login(self, request, app, token, **kwargs):
        response = requests.get(self.profile_url, headers={'Authorization': 'Bearer ' + token.token})
        extra_data = response.json()
        return self.get_provider().sociallogin_from_response(request, extra_data)
