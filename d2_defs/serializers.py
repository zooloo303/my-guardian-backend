from rest_framework import serializers
from .models import DefinitionTables

class DefinitionTablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefinitionTables
        fields = ['content']
