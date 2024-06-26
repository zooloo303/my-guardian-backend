from rest_framework import serializers
from users.models import NewUser, UserFaves


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Currently unused in preference of the below.
    """
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=True)
    password = serializers.CharField(min_length=8, write_only=True)

    class Meta:
        model = NewUser
        fields = ('email', 'username', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        # as long as the fields are the same, we can just use this
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance
    
    
class UserFavesSerializer(serializers.ModelSerializer):
    username = serializers.SlugRelatedField(
        queryset=NewUser.objects.all(),
        slug_field='username'
    )

    class Meta:
        model = UserFaves
        fields = ['username', 'itemInstanceId', 'itemHash']