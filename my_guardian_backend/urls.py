from django.contrib import admin
from django.urls import path, re_path, include

urlpatterns = [
     # Oauth
    re_path(r'^auth/', include('drf_social_oauth2.urls', namespace='drf')),
    # Admin
    path('admin/', admin.site.urls),
    # User Management
    path('api/user/', include('users.urls', namespace='users')),
]
