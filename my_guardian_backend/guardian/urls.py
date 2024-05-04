from django.urls import path
from . import api

urlpatterns = [
    path('', api.my_guardian, name='my_guardian'),
    path('characters/', api.get_characters, name='get-characters'),
    path('player_data/', api.player_data, name='get_player_data'),
]

