import requests
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import CustomUserSerializer
from rest_framework.permissions import AllowAny


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