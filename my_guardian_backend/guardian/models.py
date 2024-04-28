import uuid

from django.conf import settings
from django.db import models
from useraccount.models import User


class BungieAuth(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_in = models.DateTimeField()


class Guardian(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    membership_id = models.CharField(max_length=255)
    membership_type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

