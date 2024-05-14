import base64
import requests
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import CustomUserSerializer
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from oauth2_provider.models import AccessToken, RefreshToken, Application
from django.utils import timezone
from datetime import timedelta

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
        # Your code to send the request to the Bungie OAuth2 API
        # Assuming you get a response with a 'membership_id' field
        response = requests.post(url, data=payload)
        response_data = response.json()
        membership_id = response_data.get('membership_id')

        access_token = response_data.get('access_token')
        refresh_token = response_data.get('refresh_token')
        expires_in = response_data.get('expires_in')

        if membership_id and access_token and refresh_token and expires_in:
            User = get_user_model()
            user, created = User.objects.get_or_create(username=membership_id)
            if created:
                # You can set any additional fields on the user here
                user.save()

            # Create and save the access token
            expires = timezone.now() + timedelta(seconds=expires_in)
            AccessToken.objects.create(user=user, token=access_token, expires=expires)

            # Get or create the application
            application, _ = Application.objects.get_or_create(
                name='Bungie',
                client_type=Application.CLIENT_CONFIDENTIAL,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            )

             # Send a GET request to the Bungie API to get the current user
            headers = {
                'X-API-Key': settings.SOCIAL_AUTH_BUNGIE_API_KEY,
                'Authorization': f'Bearer {access_token}',
            }
            response = requests.get('https://www.bungie.net/Platform/User/GetMembershipsForCurrentUser/', headers=headers)
            response_data = response.json()
            # Get the primaryMembershipId from the response
            primary_membership_id = response_data.get('Response', {}).get('primaryMembershipId')
            # Store the primaryMembershipId in the user model
            user.primary_membership_id = primary_membership_id
             # Get the destinyMemberships from the response
            destiny_memberships = response_data.get('Response', {}).get('destinyMemberships', [])
            # Find the membershipType where primaryMembershipId equals membershipId
            for membership in destiny_memberships:
                if membership.get('membershipId') == primary_membership_id:
                    user.membership_type = membership.get('membershipType')
                    break

            user.save()
            # Get the displayName from the response
            displayName = response_data.get('Response', {}).get('bungieNetUser', {}).get('displayName')

            # Create and save the refresh token
            RefreshToken.objects.create(user=user, token=refresh_token, application=application)

            return Response({'message': 'User and tokens created', 'membership_id': membership_id, 'displayName': displayName}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Missing data in the response'}, status=status.HTTP_400_BAD_REQUEST)
        

def refresh_bungie_token(user):
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
        AccessToken.objects.filter(user=user).update(token=access_token, expires=expires)
        RefreshToken.objects.filter(user=user).update(token=refresh_token)
    else:
        raise Exception('Failed to refresh Bungie token')   
        

# gets the bungie profile data

class BungieProfile(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        print(f'this is the user data: {user}')
        # from the username get the refresh _token from the database and pass into the  refresh function
        # ?????
        try:
            refresh_bungie_token(user)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        access_token = AccessToken.objects.get(user=user)
        # get the memship type and membership id from the user
        headers = {
            'X-API-Key': settings.SOCIAL_AUTH_BUNGIE_API_KEY,
            'Authorization': f'Bearer {access_token.token}',
        }
        response = requests.get('https://www.bungie.net/Platform/Destiny2/{membershipType}/Profile/{destinyMembershipId}/', headers=headers)
        response_data = response.json()
        print(f'this is the response: {response_data}')
