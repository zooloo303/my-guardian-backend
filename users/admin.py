from django.contrib import admin
from users.models import NewUser, UserFaves, OAuthToken
from django.contrib.auth.admin import UserAdmin
from django.forms import Textarea
from django.db import models


class UserAdminConfig(UserAdmin):
    model = NewUser
    search_fields = ('username', 'primary_membership_id', 'membership_type',)
    list_filter = ('username', 'primary_membership_id', 'membership_type', 'is_active', 'is_staff')
    ordering = ('-start_date',)
    list_display = ('username', 'primary_membership_id', 'membership_type',
                    'is_active', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'primary_membership_id', 'membership_type',)}),
        ('Permissions', {'fields': ('is_staff', 'is_active')}),
        ('Personal', {'fields': ('about',)}),
    )
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 20, 'cols': 60})},
    }
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'primary_membership_id', 'membership_type', 'password1', 'password2', 'is_active', 'is_staff')}
         ),
    )


admin.site.register(NewUser, UserAdminConfig)


class UserFavesAdmin(admin.ModelAdmin):
    list_display = ('username', 'itemInstanceId', 'itemHash')
    search_fields = ('username__username', 'itemInstanceId', 'itemHash')

admin.site.register(UserFaves, UserFavesAdmin)


class OAuthTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'access_token', 'refresh_token', 'expires_in', 'created_at')
    search_fields = ('user__username', 'access_token')
    list_filter = ('user', 'created_at')
    readonly_fields = ('created_at',)

admin.site.register(OAuthToken, OAuthTokenAdmin)
