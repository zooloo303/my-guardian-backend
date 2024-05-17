from django.contrib import admin
from users.models import NewUser
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