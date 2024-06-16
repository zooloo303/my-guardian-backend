from django.urls import path
from .views import CustomUserCreate, BungieAuth, BungieProfile, GetFaveItems, SetFaveItem, DeleteFaveItem, TransferItem, RefreshTokenView, EquipItem

app_name = 'users'

urlpatterns = [
    # users
    path('create/', CustomUserCreate.as_view(), name="create_user"),
    # auth
    path('bungie/auth/', BungieAuth.as_view(), name="bungie_auth"),
    path('bungie/refresh/', RefreshTokenView.as_view(), name="refresh_token"),
    # guardians
    path('bungie/get/', BungieProfile.as_view(), name="get_bungie_profile"),
    path('bungie/post/transfer/', TransferItem.as_view(), name="transfer_item"),
    path('bungie/post/equip/', EquipItem.as_view(), name='equip-item'),
    # faves
    path('faveItems/get', GetFaveItems.as_view(), name="get_faves"),
    path('faveItem/set', SetFaveItem.as_view(), name="set_fave"),
    path('faveItem/unset', DeleteFaveItem.as_view(), name='unset_fave_item'),
]
