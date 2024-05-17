from django.contrib import admin
from .models import DefinitionTables

class DefinitionTablesAdmin(admin.ModelAdmin):
    list_display = ('version', 'table')

admin.site.register(DefinitionTables, DefinitionTablesAdmin)