# bungie_oauth/apps.py
from django.apps import AppConfig

class BungieOAuthConfig(AppConfig):
    name = 'bungie_oauth'
    verbose_name = 'Bungie OAuth'

    def ready(self):
        from allauth.socialaccount import providers
        from .provider import BungieProvider
        from .adapter import BungieOAuth2Adapter
        providers.registry.register(BungieProvider, BungieOAuth2Adapter)
