# armor_maxx/serializers.py
from rest_framework import serializers
from .models import ArmorPiece, ArmorModifier, ArmorOptimizationRequest

class ArmorPieceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArmorPiece
        fields = '__all__'

class ArmorModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArmorModifier
        fields = '__all__'

class ArmorOptimizationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArmorOptimizationRequest
        fields = '__all__'