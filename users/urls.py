from django.urls import path
from .views import CustomUserCreate, BungieTokenExchange, BungieSignup

app_name = 'users'

urlpatterns = [
    path('create/', CustomUserCreate.as_view(), name="create_user"),
    path('bungie/', BungieTokenExchange.as_view(), name="bungie_token_exchange"),
    path('bungie/signup/', BungieSignup.as_view(), name="bungie_signup"),
    
]