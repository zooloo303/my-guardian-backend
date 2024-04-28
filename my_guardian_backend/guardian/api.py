import asyncio
from asgiref.sync import async_to_sync
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from .models import Guardian
from .bungie_client import BungieClient
from .serializers import GuardianListSerializer, CharacterSerializer

@api_view(['GET'])
@permission_classes([])
@authentication_classes([])
def my_guardian(request):
    guardian = Guardian.objects.all()
    serializer = GuardianListSerializer(guardian, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([])
@authentication_classes([])
def get_characters(request):
    asyncio.new_event_loop()
    bungie_client = BungieClient()
    characters = async_to_sync(bungie_client.get_my_characters)()
    # characters = asyncio.run(bungie_client.get_my_characters())
    serializer = CharacterSerializer(characters, many=True)
    return Response(serializer.data)