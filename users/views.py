import base64
import requests
from typing import Dict, Any
from .models import UserFaves, OAuthToken
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
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if not is_destiny_api_enabled():
            return Response({'error': 'Destiny 2 API is currently disabled for maintenance'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        code = request.data.get('code')
        if not code:
            return Response({'error': 'Authorization code is missing'}, status=status.HTTP_400_BAD_REQUEST)

        url = "https://www.bungie.net/platform/app/oauth/token/"
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': settings.SOCIAL_AUTH_BUNGIE_KEY,
            'client_secret': settings.SOCIAL_AUTH_BUNGIE_SECRET,
        }

        response = requests.post(url, data=payload)
        response_data = response.json()

        if response.status_code != 200:
            return Response({'error': 'Failed to fetch token from Bungie'}, status=response.status_code)

        membership_id = response_data.get('membership_id')
        access_token = response_data.get('access_token')
        refresh_token = response_data.get('refresh_token')
        expires_in = response_data.get('expires_in')
        refresh_expires_in = response_data.get('refresh_expires_in')  # Get refresh_expires_in

        if not all([membership_id, access_token, refresh_token, expires_in, refresh_expires_in]):
            return Response({'error': 'Missing data in the response'}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()
        user, created = User.objects.get_or_create(username=membership_id)

        expires = timezone.now() + timedelta(seconds=expires_in)

        try:
            OAuthToken.objects.update_or_create(
                user=user,
                defaults={
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'expires_in': expires_in,
                    'refresh_expires_in': refresh_expires_in,
                    'created_at': timezone.now(),
                }
            )

            headers = {
                'X-API-Key': settings.SOCIAL_AUTH_BUNGIE_API_KEY,
                'Authorization': f'Bearer {access_token}',
            }
            response = requests.get('https://www.bungie.net/Platform/User/GetMembershipsForCurrentUser/', headers=headers)
            response_data = response.json()

            primary_membership_id = response_data.get('Response', {}).get('primaryMembershipId')
            destiny_memberships = response_data.get('Response', {}).get('destinyMemberships', [])
            if primary_membership_id:
                user.primary_membership_id = primary_membership_id
                for membership in destiny_memberships:
                    if membership.get('membershipId') == primary_membership_id:
                        user.membership_type = membership.get('membershipType')
                        break
            else:
                if len(destiny_memberships) == 1:
                    single_membership = destiny_memberships[0]
                    user.primary_membership_id = single_membership.get('membershipId')
                    user.membership_type = single_membership.get('membershipType')

            user.save()

            displayName = response_data.get('Response', {}).get('bungieNetUser', {}).get('displayName')

            return Response({
                'message': 'User and tokens created',
                'membership_id': membership_id,
                'displayName': displayName,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in,
                'refresh_expires_in': refresh_expires_in
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def refresh_bungie_token(username):
    user_model = get_user_model()
    user = user_model.objects.get(username=username)
    token = OAuthToken.objects.get(user=user)
    refresh_token = token.refresh_token
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
        refresh_expires_in = response_data.get('refresh_expires_in')  # Get refresh_expires_in
        expires = timezone.now() + timedelta(seconds=expires_in)
        OAuthToken.objects.filter(user=user).update(
            access_token=access_token, expires_in=expires_in, refresh_expires_in=refresh_expires_in, created_at=timezone.now())
        return access_token
    else:
        raise Exception('Failed to refresh Bungie token')


def is_destiny_api_enabled():
    url = "https://www.bungie.net/Platform/Settings/"
    response = requests.get(url)
    if response.status_code == 200:
        settings_data = response.json().get('Response', {})
        destiny_settings = settings_data.get('Destiny2', {})
        return destiny_settings.get('enabled', True)
    return True


class RefreshTokenView(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=username)
        except user_model.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            access_token = refresh_bungie_token(user)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        token = OAuthToken.objects.get(user=user)
        return Response({
            'access_token': token.access_token,
            'refresh_token': token.refresh_token,
            'expires_in': token.expires_in,
            'refresh_expires_in': token.refresh_expires_in
        }, status=status.HTTP_200_OK)


class BungieProfile(APIView):
    def get(self, request, *args, **kwargs):
        if not is_destiny_api_enabled():
            return Response({'error': 'Destiny 2 API is currently disabled for maintenance'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

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
        response = requests.get(f'https://www.bungie.net/Platform/Destiny2/{membership_type}/Profile/{primary_membership_id}/?components=100,102,200,201,205,300,302,304,305,308', headers=headers)
        response_data = response.json()

        # Call the sync_user_faves function
        profile_items = response_data.get('Response', {}).get('itemComponents', {}).get('instances', {}).get('data', [])
        sync_user_faves(user, profile_items)

        return Response(response_data, status=status.HTTP_200_OK)


class TransferItem(APIView):
    def post(self, request, *args, **kwargs):
        if not is_destiny_api_enabled():
            return Response({'error': 'Destiny 2 API is currently disabled for maintenance'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        username = request.data.get('username')
        itemReferenceHash = request.data.get('itemReferenceHash')
        stackSize = request.data.get('stackSize')
        transferToVault = request.data.get('transferToVault')
        itemId = request.data.get('itemId')
        characterId = request.data.get('characterId')
        membershipType = request.data.get('membershipType')

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


class EquipItem(APIView):
    def post(self, request, *args, **kwargs):
        if not is_destiny_api_enabled():
            return Response({'error': 'Destiny 2 API is currently disabled for maintenance'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        username = request.data.get('username')
        itemId = request.data.get('itemId')
        characterId = request.data.get('characterId')
        membershipType = request.data.get('membershipType')

        if None in [username, itemId, characterId, membershipType]:
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
            'itemId': itemId,
            'characterId': characterId,
            'membershipType': membershipType,
        }

        response = requests.post('https://www.bungie.net/Platform/Destiny2/Actions/Items/EquipItem/', headers=headers, json=body)

        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.json(), status=status.HTTP_400_BAD_REQUEST)


class EquipItems(APIView):
    def post(self, request, *args, **kwargs):
        if not is_destiny_api_enabled():
            return Response({'error': 'Destiny 2 API is currently disabled for maintenance'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        username = request.data.get('username')
        itemIds = request.data.get('itemIds', [])
        characterId = request.data.get('characterId')
        membershipType = request.data.get('membershipType')

        if not username or not itemIds or not characterId or not membershipType:
            return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(itemIds, list):
            return Response({'error': 'itemIds must be an array'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            access_token = refresh_bungie_token(username)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        headers = {
            'X-API-Key': settings.SOCIAL_AUTH_BUNGIE_API_KEY,
            'Authorization': f'Bearer {access_token}',
        }

        body = {
            'itemIds': itemIds,  # Use itemIds directly, no need for list comprehension
            'characterId': characterId,
            'membershipType': membershipType,
        }

        response = requests.post('https://www.bungie.net/Platform/Destiny2/Actions/Items/EquipItems/', headers=headers, json=body)

        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.json(), status=status.HTTP_400_BAD_REQUEST)
        

class GetFaveItems(APIView):
    def get(self, request, *args, **kwargs):
        username = request.query_params.get('username')
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=username)
        except ObjectDoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            user_faves = UserFaves.objects.filter(username=user)
            serializer = UserFavesSerializer(user_faves, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({'error': 'No favorite items found'}, status=status.HTTP_404_NOT_FOUND)


class SetFaveItem(APIView):
    def post(self, request, *args, **kwargs):
        serializer = UserFavesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

def sync_user_faves(user, profile_items: Dict[str, Any]):
    user_faves = UserFaves.objects.filter(username=user)    
    item_instance_ids = set(profile_items.keys())
    for fave in user_faves:
        if str(fave.itemInstanceId) not in item_instance_ids:
            fave.delete()
