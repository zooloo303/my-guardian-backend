import base64
import requests
from .models import UserFaves
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .serializers import CustomUserSerializer, UserFavesSerializer
from oauth2_provider.models import AccessToken, RefreshToken, Application


class CustomUserCreate(APIView):
    permission_classes = [AllowAny]

    def post(self, request, format='json'):
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if user:
                json = serializer.data
                return Response(json, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class BungieAuth(APIView):
    def post(self, request, *args, **kwargs):
        code = request.data.get('code')
        url = "https://www.bungie.net/platform/app/oauth/token/"
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': settings.SOCIAL_AUTH_BUNGIE_KEY,
            'client_secret': settings.SOCIAL_AUTH_BUNGIE_SECRET,
        }
        response = requests.post(url, data=payload)
        response_data = response.json()
        membership_id = response_data.get('membership_id')

        access_token = response_data.get('access_token')
        refresh_token = response_data.get('refresh_token')
        expires_in = response_data.get('expires_in')

        if membership_id and access_token and refresh_token and expires_in:
            User = get_user_model()
            user, created = User.objects.get_or_create(username=membership_id)

            expires = timezone.now() + timedelta(seconds=expires_in)

            # Update or create the access token
            AccessToken.objects.update_or_create(user=user, defaults={'token': access_token, 'expires': expires})

            # Get or create the application
            application, _ = Application.objects.get_or_create(
                name='Bungie',
                client_type=Application.CLIENT_CONFIDENTIAL,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            )

            headers = {
                'X-API-Key': settings.SOCIAL_AUTH_BUNGIE_API_KEY,
                'Authorization': f'Bearer {access_token}',
            }
            response = requests.get('https://www.bungie.net/Platform/User/GetMembershipsForCurrentUser/', headers=headers)
            response_data = response.json()
            primary_membership_id = response_data.get('Response', {}).get('primaryMembershipId')
            user.primary_membership_id = primary_membership_id
            destiny_memberships = response_data.get('Response', {}).get('destinyMemberships', [])
            for membership in destiny_memberships:
                if membership.get('membershipId') == primary_membership_id:
                    user.membership_type = membership.get('membershipType')
                    break

            user.save()
            displayName = response_data.get('Response', {}).get('bungieNetUser', {}).get('displayName')

            # Update or create the refresh token
            RefreshToken.objects.update_or_create(user=user, application=application, defaults={'token': refresh_token})

            return Response({
                'message': 'User and tokens created',
                'membership_id': membership_id,
                'displayName': displayName,
                'access_token': access_token,
                'refresh_token': refresh_token}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Missing data in the response'}, status=status.HTTP_400_BAD_REQUEST)       


def refresh_bungie_token(username):
    user_model = get_user_model()
    user = user_model.objects.get(username=username)
    refresh_token = RefreshToken.objects.get(user=user).token
    url = "https://www.bungie.net/platform/app/oauth/token/"

    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    client_id_secret = f"{settings.SOCIAL_AUTH_BUNGIE_KEY}:{settings.SOCIAL_AUTH_BUNGIE_SECRET}"
    client_id_secret_base64 = base64.b64encode(client_id_secret.encode()).decode()
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {client_id_secret_base64}'
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        response_data = response.json()
        access_token = response_data.get('access_token')
        expires_in = response_data.get('expires_in')
        expires = timezone.now() + timedelta(seconds=expires_in)
        AccessToken.objects.filter(user=username).update(token=access_token, expires=expires)
        RefreshToken.objects.filter(user=username).update(token=refresh_token)
        return access_token
    else:
        raise Exception('Failed to refresh Bungie token')   
        

# gets the bungie profile data
class BungieProfile(APIView):
    def get(self, request, *args, **kwargs):
        username = request.query_params.get('username')
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=username)
        except ObjectDoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        primary_membership_id = user.primary_membership_id
        membership_type = user.membership_type
        try:
            access_token = refresh_bungie_token(username)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        headers = {
            'X-API-Key': settings.SOCIAL_AUTH_BUNGIE_API_KEY,
            'Authorization': f'Bearer {access_token}',
        }
        response = requests.get(f'https://www.bungie.net/Platform/Destiny2/{membership_type}/Profile/{primary_membership_id}/?components=100,102,200,201,205,300', headers=headers)
        response_data = response.json()

        # Call the sync_user_faves function
        profile_items = response_data.get('Response', {}).get('profileInventory', {}).get('data', {}).get('items', [])
        sync_user_faves(username, profile_items)

        return Response(response_data, status=status.HTTP_200_OK)
    

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from django.conf import settings

class TransferItem(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        itemReferenceHash = request.data.get('itemReferenceHash')
        stackSize = request.data.get('stackSize')
        transferToVault = request.data.get('transferToVault')
        itemId = request.data.get('itemId')
        characterId = request.data.get('characterId')
        membershipType = request.data.get('membershipType')

        # Check if any field is None
        if None in [username, itemReferenceHash, stackSize, transferToVault, itemId, characterId, membershipType]:
            return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            access_token = refresh_bungie_token(username)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        headers = {
            'X-API-Key': settings.SOCIAL_AUTH_BUNGIE_API_KEY,
            'Authorization': f'Bearer {access_token}',
        }

        body = {
            'itemReferenceHash': itemReferenceHash,
            'stackSize': stackSize,
            'transferToVault': transferToVault,
            'itemId': itemId,
            'characterId': characterId,
            'membershipType': membershipType,
        }

        response = requests.post('https://www.bungie.net/Platform/Destiny2/Actions/Items/TransferItem/', headers=headers, json=body)

        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.json(), status=status.HTTP_400_BAD_REQUEST)

        
        
# Get all favorite items for a user
class GetFaveItems(APIView):
    def get(self, request, *args, **kwargs):
        username = request.query_params.get('username')
        user_model = get_user_model()
        try:
            username = user_model.objects.get(username=username)
        except ObjectDoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)      
        if not username:
            return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Get the User object first
            user_faves = UserFaves.objects.filter(username=username)
            serializer = UserFavesSerializer(user_faves, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({'error': 'No favorite items found'}, status=status.HTTP_404_NOT_FOUND)

# Add a new favorite item for a user
class SetFaveItem(APIView):
    def post(self, request, *args, **kwargs):
        serializer = UserFavesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# Delete a favorite item for a user
class DeleteFaveItem(APIView):
    def delete(self, request, *args, **kwargs):
        data = request.data
        itemInstanceId = data.get('itemInstanceId')
        try:
            user_fave = UserFaves.objects.get(itemInstanceId=itemInstanceId)
        except ObjectDoesNotExist:
            return Response({'error': 'Favorite item not found'}, status=status.HTTP_404_NOT_FOUND)
        user_fave.delete()
        return Response({'message': 'Favorite item deleted'}, status=status.HTTP_200_OK)

    
def sync_user_faves(username, profile_items):
    user_faves = UserFaves.objects.filter(username=username)
    for fave in user_faves:
        if not any(item['itemInstanceId'] == fave.itemInstanceId for item in profile_items):
            fave.delete()    