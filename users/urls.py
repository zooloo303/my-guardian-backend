from django.urls import path
from .views import CustomUserCreate, BungieAuth, BungieProfile

app_name = 'users'

urlpatterns = [
    path('create/', CustomUserCreate.as_view(), name="create_user"),
    path('bungie/get/', BungieProfile.as_view(), name="get_bungie_profile"),
    path('bungie/auth/', BungieAuth.as_view(), name="bungie_auth"),
    
]