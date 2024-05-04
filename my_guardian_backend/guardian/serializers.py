from rest_framework import serializers

from .models import Guardian

from useraccount.serializers import UserDetailSerializer

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
    id = serializers.CharField(max_length=200)
    Class_Type = serializers.CharField(max_length=200)
    Race_Type = serializers.CharField(max_length=200)
    Light_Level = serializers.CharField(max_length=200)


class UserInfoSerializer(serializers.Serializer):
    crossSaveOverride = serializers.IntegerField()
    applicableMembershipTypes = serializers.ListField(child=serializers.IntegerField())
    isPublic = serializers.BooleanField()
    membershipType = serializers.IntegerField()
    membershipId = serializers.CharField()
    displayName = serializers.CharField()
    bungieGlobalDisplayName = serializers.CharField()
    bungieGlobalDisplayNameCode = serializers.IntegerField()

class ProfileDataSerializer(serializers.Serializer):
    userInfo = UserInfoSerializer()
    dateLastPlayed = serializers.DateTimeField()
    versionsOwned = serializers.IntegerField()
    characterIds = serializers.ListField(child=serializers.CharField())
    seasonHashes = serializers.ListField(child=serializers.IntegerField())
    eventCardHashesOwned = serializers.ListField(child=serializers.IntegerField())
    currentSeasonHash = serializers.IntegerField()
    currentSeasonRewardPowerCap = serializers.IntegerField()
    currentGuardianRank = serializers.IntegerField()
    lifetimeHighestGuardianRank = serializers.IntegerField()
    renewedGuardianRank = serializers.IntegerField()

class ProfileSerializer(serializers.Serializer):
    data = ProfileDataSerializer()
    privacy = serializers.IntegerField()

class StatSerializer(serializers.Serializer):
    value = serializers.IntegerField()

class CharacterDataSerializer(serializers.Serializer):
    membershipId = serializers.CharField()
    membershipType = serializers.IntegerField()
    characterId = serializers.CharField()
    dateLastPlayed = serializers.DateTimeField()
    minutesPlayedThisSession = serializers.CharField()
    minutesPlayedTotal = serializers.CharField()
    light = serializers.IntegerField()
    stats = serializers.DictField(child=StatSerializer())
    raceHash = serializers.IntegerField()
    genderHash = serializers.IntegerField()
    classHash = serializers.IntegerField()
    raceType = serializers.IntegerField()
    classType = serializers.IntegerField()
    genderType = serializers.IntegerField()
    emblemPath = serializers.CharField()
    emblemBackgroundPath = serializers.CharField()
    emblemHash = serializers.IntegerField()
    emblemColor = serializers.DictField()
    levelProgression = serializers.DictField()
    baseCharacterLevel = serializers.IntegerField()
    percentToNextLevel = serializers.FloatField()
    titleRecordHash = serializers.IntegerField()

class CharactersSerializer(serializers.Serializer):
    data = serializers.DictField(child=CharacterDataSerializer())
    privacy = serializers.IntegerField()

class ItemSerializer(serializers.Serializer):
    itemHash = serializers.IntegerField()
    itemInstanceId = serializers.CharField()
    quantity = serializers.IntegerField()
    bindStatus = serializers.IntegerField()
    location = serializers.IntegerField()
    bucketHash = serializers.IntegerField()
    transferStatus = serializers.IntegerField()
    lockable = serializers.BooleanField()
    state = serializers.IntegerField()
    dismantlePermission = serializers.IntegerField()
    isWrapper = serializers.BooleanField()
    tooltipNotificationIndexes = serializers.ListField(child=serializers.IntegerField())
    versionNumber = serializers.IntegerField()

class CharacterEquipmentSerializer(serializers.Serializer):
    items = serializers.ListField(child=ItemSerializer())
    privacy = serializers.IntegerField()

class CompleteDataSerializer(serializers.Serializer):
    Profile = ProfileSerializer()
    Characters = CharactersSerializer()
    CharacterEquipment = serializers.DictField(child=CharacterEquipmentSerializer())

#  views can now use this CompleteDataSerializer to handle all data.

