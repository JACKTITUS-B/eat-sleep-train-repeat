from .models import Exercise

def get_muscle_groups_from_db(workout_name):
    """
    Finds an exercise in the database and returns its primary muscle group.
    """
    try:
        # Use a case-insensitive lookup to be more flexible
        exercise = Exercise.objects.get(name__iexact=workout_name)
        # Return it as a list to match the old function's format
        return [exercise.muscle_group]
    except Exercise.DoesNotExist:
        # If the workout isn't in our database, return an empty list
        return []