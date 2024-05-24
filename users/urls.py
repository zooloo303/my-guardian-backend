from django.urls import path
from .views import CustomUserCreate, BungieAuth, BungieProfile, GetFaveItems, SetFaveItem, DeleteFaveItem

app_name = 'users'

urlpatterns = [
    path('create/', CustomUserCreate.as_view(), name="create_user"),
    path('bungie/get/', BungieProfile.as_view(), name="get_bungie_profile"),
    path('bungie/auth/', BungieAuth.as_view(), name="bungie_auth"),
    path('faveItems/get', GetFaveItems.as_view(), name="get_faves"),
    path('faveItem/set', SetFaveItem.as_view(), name="set_fave"),
    path('faveItem/unset', DeleteFaveItem.as_view(), name='unset_fave_item'),
    
    
]