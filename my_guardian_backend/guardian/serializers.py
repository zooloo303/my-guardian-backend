from rest_framework import serializers

from .models import Guardian

# from useraccount.serializers import UserDetailSerializer

class GuardianListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = (
            'id',
            'user',
            'name',
            'membership_id',
            'membership_type',
        )


class CharacterSerializer(serializers.Serializer):
    Character_ID = serializers.CharField(max_length=200)
    Class_Type = serializers.CharField(max_length=200)
    Race_Type = serializers.CharField(max_length=200)
    Light_Level = serializers.CharField(max_length=200)