from django.contrib import admin
from .models import Workout, Exercise,UserProfile

# Register your models here to make them visible in the admin panel
admin.site.register(Workout)
admin.site.register(Exercise)
admin.site.register(UserProfile)