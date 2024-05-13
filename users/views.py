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
    
    
class BungieTokenExchange(APIView):
    def post(self, request, *args, **kwargs):
        code = request.data.get('code')
        url = "https://www.bungie.net/platform/app/oauth/token/"
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': settings.SOCIAL_AUTH_BUNGIE_KEY,
            'client_secret': settings.SOCIAL_AUTH_BUNGIE_SECRET,
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.json(), status=response.status_code)
        

class BungieSignup(APIView):
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

            # Create and save the refresh token
            RefreshToken.objects.create(user=user, token=refresh_token, application=application)

            return Response({'message': 'User and tokens created', 'membership_id': membership_id}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Missing data in the response'}, status=status.HTTP_400_BAD_REQUEST)