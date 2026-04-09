# fitness_tracker/management/commands/load_exercises.py

import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from fitness_tracker.models import Exercise 

class Command(BaseCommand):
    help = 'Loads and updates exercises from exercise.csv into the database'

    def handle(self, *args, **kwargs):
        csv_file_path = os.path.join(settings.BASE_DIR, 'fitness_tracker', 'data', 'exercise.csv')
        self.stdout.write(f"Syncing exercises from {csv_file_path}")

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                
                for row in reader:
                    if not row:
                        continue
                        
                    workout_name, muscle_group = row
                    
                    # --- THIS IS THE FIX ---
                    # update_or_create will update existing exercises and create new ones.
                    obj, created = Exercise.objects.update_or_create(
                        name=workout_name.strip(),
                        defaults={'muscle_group': muscle_group.strip()}
                    )
                    
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Successfully CREATED: {workout_name}'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'Successfully UPDATED: {workout_name}'))

            self.stdout.write(self.style.SUCCESS('Finished syncing exercises.'))
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Error: The file was not found at {csv_file_path}"))