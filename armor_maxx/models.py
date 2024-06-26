# armor_maxx/models.py
from django.db import models
from users.models import NewUser

class ArmorPiece(models.Model):
    user = models.ForeignKey(NewUser, on_delete=models.CASCADE, related_name='armor_pieces')
    item_id = models.CharField(max_length=100)
    item_hash = models.CharField(max_length=100)
    armor_type = models.CharField(max_length=20)
    is_exotic = models.BooleanField(default=False)
    mobility = models.IntegerField()
    resilience = models.IntegerField()
    recovery = models.IntegerField()
    discipline = models.IntegerField()
    intellect = models.IntegerField()
    strength = models.IntegerField()

class SubclassFragment(models.Model):
    name = models.CharField(max_length=100)
    subclass = models.CharField(max_length=50)
    mobility_mod = models.IntegerField(default=0)
    resilience_mod = models.IntegerField(default=0)
    recovery_mod = models.IntegerField(default=0)
    discipline_mod = models.IntegerField(default=0)
    intellect_mod = models.IntegerField(default=0)
    strength_mod = models.IntegerField(default=0)

class ArmorOptimizationRequest(models.Model):
    user = models.ForeignKey(NewUser, on_delete=models.CASCADE)
    exotic_id = models.CharField(max_length=100)
    subclass = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    result = models.TextField(null=True, blank=True)