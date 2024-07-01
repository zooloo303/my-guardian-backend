from django.db import models
from users.models import NewUser

class ArmorDefinition(models.Model):
    item_hash = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=255)
    tier_type = models.IntegerField()
    item_type = models.CharField(max_length=50)
    item_sub_type = models.CharField(max_length=50)
    item_category_hashes = models.JSONField(default=list)  # New field

    class Meta:
        indexes = [
            models.Index(fields=['tier_type']),
            models.Index(fields=['item_type']),
        ]

class ArmorPiece(models.Model):
    ARMOR_TYPES = [
        ('HELMET', 'Helmet'),
        ('GAUNTLETS', 'Gauntlets'),
        ('CHEST_ARMOR', 'Chest Armor'),
        ('LEG_ARMOR', 'Leg Armor'),
        ('CLASS_ARMOR', 'Class Armor'),
    ]

    CLASS_TYPES = [
        ('TITAN', 'Titan'),
        ('HUNTER', 'Hunter'),
        ('WARLOCK', 'Warlock'),
        ('ALL', 'All Classes'),
    ]

    INVENTORY_TYPES = [
        ('profile', 'Profile'),
        ('character', 'Character'),
        ('equipped', 'Equipped'),
    ]

    user = models.ForeignKey(NewUser, on_delete=models.CASCADE, related_name='armor_pieces')
    character_id = models.CharField(max_length=100)
    item_id = models.CharField(max_length=100)
    item_hash = models.CharField(max_length=100)
    armor_type = models.CharField(max_length=20, choices=ARMOR_TYPES)
    class_type = models.CharField(max_length=10, choices=CLASS_TYPES)
    inventory_type = models.CharField(max_length=10, choices=INVENTORY_TYPES)
    is_exotic = models.BooleanField(default=False)
    mobility = models.IntegerField()
    resilience = models.IntegerField()
    recovery = models.IntegerField()
    discipline = models.IntegerField()
    intellect = models.IntegerField()
    strength = models.IntegerField()

    class Meta:
        unique_together = ('user', 'item_id', 'character_id')
        indexes = [
            models.Index(fields=['user', 'character_id']),
            models.Index(fields=['armor_type']),
            models.Index(fields=['class_type']),
            models.Index(fields=['is_exotic']),
        ]

class ArmorModifier(models.Model):
    MODIFIER_TYPES = (
        ('SUBCLASS_FRAGMENT', 'Subclass Fragment'),
        ('ARMOR_MOD', 'Armor Mod'),
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    modifier_type = models.CharField(max_length=20, choices=MODIFIER_TYPES)
    item_hash = models.CharField(max_length=20, unique=True)
    icon_url = models.URLField(blank=True)
    subclass = models.CharField(max_length=50, blank=True)  # Only for fragments

    # Stats
    mobility = models.IntegerField(default=0)
    resilience = models.IntegerField(default=0)
    recovery = models.IntegerField(default=0)
    discipline = models.IntegerField(default=0)
    intellect = models.IntegerField(default=0)
    strength = models.IntegerField(default=0)

    # Additional fields
    item_type_display_name = models.CharField(max_length=255, blank=True)
    is_conditionally_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.get_modifier_type_display()})"

    class Meta:
        ordering = ['name']

class ArmorOptimizationRequest(models.Model):
    user = models.ForeignKey(NewUser, on_delete=models.CASCADE)
    exotic_id = models.CharField(max_length=100)
    subclass = models.CharField(max_length=50)
    character_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    result = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'character_id']),
            models.Index(fields=['created_at']),
        ]