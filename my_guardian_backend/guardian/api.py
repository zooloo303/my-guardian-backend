import asyncio
from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from .models import Guardian
from .bungie_client import BungieClient
from .bungie_public import BungieClient as BungiePublicClient
from .serializers import CompleteDataSerializer, GuardianListSerializer, CharacterSerializer

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


@api_view(['GET'])
@permission_classes([])
@authentication_classes([])
def player_data(request):
    player_id = request.GET.get('player_id', None)
    if not player_id:
        return Response({"error": "Player ID is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Your existing code to use the player_id
    client = BungiePublicClient()
    
    # Fetch data from Bungie API asynchronously
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(client.get_player_data(player_id))
    print(data['CharacterEquipment'])
    loop.close()

    if data:
        # Serialize and return data
        serializer = CompleteDataSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"error": "Data not found"}, status=status.HTTP_404_NOT_FOUND)