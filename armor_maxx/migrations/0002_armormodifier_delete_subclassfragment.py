# Generated by Django 5.0.6 on 2024-06-29 17:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('armor_maxx', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArmorModifier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('modifier_type', models.CharField(choices=[('SUBCLASS_FRAGMENT', 'Subclass Fragment'), ('ARMOR_MOD', 'Armor Mod')], max_length=20)),
                ('item_hash', models.CharField(max_length=20, unique=True)),
                ('icon_url', models.URLField(blank=True)),
                ('subclass', models.CharField(blank=True, max_length=50)),
                ('mobility', models.IntegerField(default=0)),
                ('resilience', models.IntegerField(default=0)),
                ('recovery', models.IntegerField(default=0)),
                ('discipline', models.IntegerField(default=0)),
                ('intellect', models.IntegerField(default=0)),
                ('strength', models.IntegerField(default=0)),
                ('item_type_display_name', models.CharField(blank=True, max_length=255)),
                ('is_conditionally_active', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.DeleteModel(
            name='SubclassFragment',
        ),
    ]
