from django.db import models

class DefinitionTables(models.Model):
    version = models.CharField(max_length=255, blank=False, null=False)
    table = models.CharField(max_length=255, blank=False, null=False)
    language = models.CharField(max_length=255, blank=False, null=False)
    content = models.JSONField(blank=False, null=False)