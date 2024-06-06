# models.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class CustomAccountManager(BaseUserManager):

    def create_superuser(self, username, first_name, password, **other_fields):

        other_fields.setdefault('is_staff', True)
        other_fields.setdefault('is_superuser', True)
        other_fields.setdefault('is_active', True)

        if other_fields.get('is_staff') is not True:
            raise ValueError(
                'Superuser must be assigned to is_staff=True.')
        if other_fields.get('is_superuser') is not True:
            raise ValueError(
                'Superuser must be assigned to is_superuser=True.')

        return self.create_user(username, first_name, password, **other_fields)

    def create_user(self, username, first_name, password, **other_fields):

        user = self.model(username=username,
                          first_name=first_name, **other_fields)
        user.set_password(password)
        user.save()
        return user


class NewUser(AbstractBaseUser, PermissionsMixin):

    email = models.EmailField(_('email address'), unique=True, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    about = models.TextField(_('about'), max_length=500, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    primary_membership_id = models.CharField(max_length=255, null=True, blank=True)
    membership_type = models.CharField(max_length=1, null=True, blank=True)  

    objects = CustomAccountManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name']

    def __str__(self):
        return self.username


class OAuthToken(models.Model):
    user = models.ForeignKey(NewUser, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=512)
    refresh_token = models.CharField(max_length=512, null=True, blank=True)
    expires_in = models.IntegerField()
    refresh_expires_in = models.IntegerField()
    token_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)


class UserFaves(models.Model):
    username = models.ForeignKey(NewUser, on_delete=models.CASCADE)
    itemInstanceId = models.CharField(max_length=255, unique=True)
    itemHash = models.IntegerField()
