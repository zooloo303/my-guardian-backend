# armor_maxx/admin.py
from django.contrib import admin
from .models import ArmorDefinition, ArmorModifier, ArmorPiece, ArmorOptimizationRequest

@admin.register(ArmorModifier)
class ArmorModifierAdmin(admin.ModelAdmin):
    list_display = ('name', 'modifier_type', 'subclass', 'mobility', 'resilience', 'recovery', 'discipline', 'intellect', 'strength')
    list_filter = ('modifier_type', 'subclass')
    search_fields = ('name', 'description')
    readonly_fields = ('item_hash',)  # Assuming item_hash should not be editable

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'modifier_type', 'subclass', 'item_hash', 'icon_url')
        }),
        ('Stats', {
            'fields': ('mobility', 'resilience', 'recovery', 'discipline', 'intellect', 'strength')
        }),
        ('Additional Info', {
            'fields': ('item_type_display_name', 'is_conditionally_active')
        }),
    )

@admin.register(ArmorPiece)
class ArmorPieceAdmin(admin.ModelAdmin):
    list_display = ('user', 'character_id', 'armor_type', 'is_exotic', 'mobility', 'resilience', 'recovery', 'discipline', 'intellect', 'strength')
    list_filter = ('armor_type', 'is_exotic')
    search_fields = ('user__username', 'character_id', 'item_id', 'item_hash')

@admin.register(ArmorOptimizationRequest)
class ArmorOptimizationRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'exotic_id', 'subclass', 'character_id', 'created_at')
    list_filter = ('subclass', 'created_at')
    search_fields = ('user__username', 'exotic_id', 'character_id')
    readonly_fields = ('created_at',)

@admin.register(ArmorDefinition)
class ArmorDefinitionAdmin(admin.ModelAdmin):
    list_display = ('item_hash', 'name', 'tier_type', 'item_type', 'item_sub_type')
    list_filter = ('tier_type', 'item_type')
    search_fields = ('item_hash', 'name')
    readonly_fields = ('item_hash',)

    fieldsets = (
        (None, {
            'fields': ('item_hash', 'name', 'tier_type')
        }),
        ('Item Details', {
            'fields': ('item_type', 'item_sub_type', 'item_category_hashes')
        }),
    )