from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    # Guardian API
    path('api/user/', include('users.urls', namespace='users')),
    path('api/armor_maxx/', include('armor_maxx.urls')),
]
