from django.db import models
from django.contrib.auth.models import User

class Workout(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workout_name = models.CharField(max_length=100)
    sets = models.IntegerField(default=0)
    reps = models.IntegerField(default=0)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    duration = models.IntegerField(help_text="Duration in minutes")
    notes = models.TextField(blank=True)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s workout on {self.date}"

class Exercise(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # This field will help us map exercises to the heatmap
    muscle_group = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    GOAL_CHOICES = [
        ('lose_weight', 'Lose Weight'),
        ('maintain_weight', 'Maintain Weight'),
        ('gain_weight', 'Gain Weight'),
    ]
    
    STYLE_CHOICES = [
        ('hypertrophy', 'Muscle Building'),
        ('strength', 'Powerlifting'),
    ]

    goal = models.CharField(max_length=20, choices=GOAL_CHOICES, null=True, blank=True)
    training_style = models.CharField(max_length=20, choices=STYLE_CHOICES, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Height in cm")
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Weight in kg")

    def __str__(self):
        return f"{self.user.username}'s Profile"