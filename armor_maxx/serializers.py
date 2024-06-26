# armor_maxx/serializers.py
from rest_framework import serializers
from .models import ArmorPiece, SubclassFragment, ArmorOptimizationRequest

class ArmorPieceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArmorPiece
        fields = '__all__'

class SubclassFragmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubclassFragment
        fields = '__all__'

class ArmorOptimizationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArmorOptimizationRequest
        fields = '__all__'