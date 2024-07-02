from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Updates armor definitions and armor modifiers'

    def handle(self, *args, **options):
        self.stdout.write("Starting data update process...")

        self.stdout.write("Updating armor definitions...")
        call_command('update_armor_definitions')

        self.stdout.write("Updating armor modifiers...")
        call_command('populate_armor_modifiers')

        self.stdout.write(self.style.SUCCESS("All data updated successfully!"))