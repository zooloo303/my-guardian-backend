from users.serializers import CustomUserSerializer
from rest_framework import serializers
from .models import Chat, Conversation

class ConversationListSerializer(serializers.ModelSerializer):
    users = CustomUserSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ('id', 'users', 'modified_at',)

class ConversationDetailSerializer(serializers.ModelSerializer):
    users = CustomUserSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ('id', 'users', 'modified_at',)

class ChatSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    class Meta:
        model = Chat
        fields = ['id', 'prompt', 'response', 'created_at', 'author']
        extra_kwargs = {
            'author': {'read_only': True},
            'response': {'required': False, 'allow_null': True, 'allow_blank': True}
        }