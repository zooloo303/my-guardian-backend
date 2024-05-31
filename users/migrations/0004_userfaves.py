# Generated by Django 5.0.6 on 2024-05-23 17:33

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_newuser_membership_type_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserFaves',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('itemInstanceId', models.IntegerField()),
                ('itemHash', models.IntegerField()),
                ('username', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]