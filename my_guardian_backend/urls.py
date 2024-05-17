from django.contrib import admin
from django.urls import path, re_path, include

urlpatterns = [
     # Oauth
    re_path(r'^auth/', include('drf_social_oauth2.urls', namespace='drf')),
    # Admin
    path('admin/', admin.site.urls),
    # Guardian API
    path('api/user/', include('users.urls', namespace='users')),
    path('api/def/', include('d2_defs.urls', namespace='d2_defs')),
]
