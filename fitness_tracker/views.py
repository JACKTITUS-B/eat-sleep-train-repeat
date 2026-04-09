

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Workout
from datetime import date, timedelta
import google.generativeai as genai
import os
from .utils import get_muscle_groups_from_db 
from .models import Workout, Exercise 
import json
from .forms import RegistrationForm 
from django.db.models import Sum
from collections import defaultdict
from django.db.models import Sum, Max, F
from .models import UserProfile
from .forms import UserProfileForm
API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyADl3Ush84deh5CkhKGo6nE8iK4w1qR3RM")

# Configure the API key globally for the library
genai.configure(api_key=API_KEY)

# Configure the API key
# Get your API key for free from https://ai.google.dev/


# Define a simple way to categorize workouts
def get_workout_type(workout_name):
    push_keywords = ['push', 'chest', 'shoulder', 'tricep', 'bench', 'press']
    pull_keywords = ['pull', 'back', 'bicep', 'row', 'chin', 'pullup']
    leg_keywords = ['leg', 'squat', 'deadlift', 'lunge', 'quad', 'hamstring']
    
    workout_name = workout_name.lower()
    if any(keyword in workout_name for keyword in push_keywords):
        return 'push'
    if any(keyword in workout_name for keyword in pull_keywords):
        return 'pull'
    if any(keyword in workout_name for keyword in leg_keywords):
        return 'leg'
    return 'other'

# A more detailed categorization for the heatmap

# In your fitness_tracker/views.py file
# In fitness_tracker/views.py

def get_muscle_groups_from_db(workout_name):
    try:
        exercise = Exercise.objects.get(name__iexact=workout_name.strip())
        # Splits 'quads;glutes' into ['quads', 'glutes']
        return exercise.muscle_group.split(';')
    except Exercise.DoesNotExist:
        return [] # --- Add any other exercises you log here ---
    # Example:
    # if 'bicep curl' in name:
    #     return ['left_bicep', 'right_bicep']

    # If no match is found, return an empty list
    return []

# Create your views here.

# In fitness_tracker/views.py

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            # This now correctly sends new users to the profile setup page
            return redirect('profile_setup') 
    else:
        form = RegistrationForm()
    
    context = {'form': form}
    return render(request, 'fitness_tracker/register.html', context)
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'fitness_tracker/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')



# --- NEW HELPER FUNCTION TO CALCULATE STATS FOR ANY DATE RANGE ---
# --- UPDATED HELPER FUNCTION ---
def calculate_stats_for_period(user, start_date, end_date):
    workouts = Workout.objects.filter(user=user, date__gte=start_date, date__lte=end_date)
    
    total_volume = 0
    for workout in workouts:
        total_volume += workout.sets * workout.reps * workout.weight
        
    workout_count = workouts.values('date').distinct().count()
    
    heaviest_lift_data = workouts.aggregate(max_weight=Max('weight'))
    heaviest_lift = heaviest_lift_data['max_weight'] or 0
    
    return {
        'total_volume': total_volume,
        'workout_count': workout_count,
        'heaviest_lift': heaviest_lift,
    }

# --- MAIN DASHBOARD VIEW ---
@login_required
def dashboard_view(request):
    # 1. GET THE SELECTED PERIOD FROM URL
    period = request.GET.get('period', '7days') # Default to '7days'
    today = date.today()

    # 2. CALCULATE DATE RANGES
    if period == 'week':
        # Current Week (Mon-Sun)
        current_start = today - timedelta(days=today.weekday())
        current_end = current_start + timedelta(days=6)
        # Previous Week
        previous_start = current_start - timedelta(days=7)
        previous_end = current_start - timedelta(days=1)
    elif period == 'month':
        # Current Month
        current_start = today.replace(day=1)
        next_month_start = (current_start + timedelta(days=32)).replace(day=1)
        current_end = next_month_start - timedelta(days=1)
        # Previous Month
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end.replace(day=1)
    else: # Default is '7days'
        current_start = today - timedelta(days=6)
        current_end = today
        previous_start = today - timedelta(days=13)
        previous_end = today - timedelta(days=7)

    # 3. CALCULATE STATS FOR BOTH PERIODS
    current_stats = calculate_stats_for_period(request.user, current_start, current_end)
    previous_stats = calculate_stats_for_period(request.user, previous_start, previous_end)

    # 4. CALCULATE PERCENTAGE CHANGES
    # 4. CALCULATE PERCENTAGE CHANGES
    def get_percentage_change(current, previous):
        if previous > 0:
            return round(((current - previous) / previous) * 100)
        return 0 if current == 0 else 100

    percentage_changes = {
        'volume': get_percentage_change(current_stats['total_volume'], previous_stats['total_volume']),
        'workouts': get_percentage_change(current_stats['workout_count'], previous_stats['workout_count']),
        'heaviest_lift': get_percentage_change(current_stats['heaviest_lift'], previous_stats['heaviest_lift']),
    }
    
    # 5. GET DATA FOR CHARTS AND LOGS
    workouts_for_period = Workout.objects.filter(user=request.user, date__gte=current_start, date__lte=current_end)
    
    # Data for Muscle Balance Chart
    muscle_group_sets = defaultdict(int)
    for workout in workouts_for_period:
        general_groups = get_muscle_groups_from_db(workout.workout_name)
        for group in general_groups:
            muscle_group_sets[group.strip().capitalize()] += workout.sets
    muscle_labels = list(muscle_group_sets.keys())
    muscle_data = list(muscle_group_sets.values())

    # Data for Daily Volume Chart
    volume_by_day = defaultdict(float)
    for workout in workouts_for_period:
        day_label = workout.date.strftime('%b %d')
        volume_by_day[day_label] += float(workout.sets * workout.reps * workout.weight)
    daily_volume_labels = list(volume_by_day.keys())
    daily_volume_data = list(volume_by_day.values())

    # Data for Consistency Calendar (last 6 months)
    six_months_ago = today - timedelta(days=180)
    consistency_workouts = Workout.objects.filter(user=request.user, date__gte=six_months_ago).values_list('date', flat=True).distinct()
    consistency_dates = [d.strftime('%Y-%m-%d') for d in consistency_workouts]

    # 6. PASS EVERYTHING TO THE TEMPLATE
    context = {
        'current_stats': current_stats,
        'percentage_changes': percentage_changes,
        'muscle_labels': muscle_labels,
        'muscle_data': muscle_data,
        'daily_volume_labels': daily_volume_labels,
        'daily_volume_data': daily_volume_data,
        'consistency_dates': consistency_dates,
        'selected_period': period,
    }
    return render(request, 'fitness_tracker/dashboard.html', context)


@login_required
def log_workout_view(request):
    if request.method == 'POST':
        workout_name = request.POST.get('workout_name')
        sets = request.POST.get('sets')
        reps = request.POST.get('reps')
        weight = request.POST.get('weight')
        duration = request.POST.get('duration')
        notes = request.POST.get('notes')

        Workout.objects.create(
            user=request.user,
            workout_name=workout_name,
            sets=int(sets) if sets else 0,
            reps=int(reps) if reps else 0,
            weight=float(weight) if weight else 0.0,
            duration=int(duration) if duration else 0,
            notes=notes
        )
        return redirect('dashboard')
    
    # --- ADD THIS LOGIC ---
    # 1. Get all exercise names from the database
    all_exercises = Exercise.objects.values_list('name', flat=True).order_by('name')
    
    # 2. Convert the list to a JSON string
    exercise_names_json = json.dumps(list(all_exercises))

    # 3. Create a context dictionary to pass data to the template
    context = {
        'exercise_names_json': exercise_names_json,
    }
    
    # 4. Pass the context to the render function
    return render(request, 'fitness_tracker/log_workout.html', context)




 # CORRECT placement for the decorator
#
# ... (all your other views like register_view, login_view, dashboard_view, etc. remain unchanged) ...
#

@login_required
def heatmap_view(request):
    # --- 1. DEFINE THE NEW SCIENCE-BASED THRESHOLDS ---
    # These are based on the weekly set volumes you provided.
    # 'undertrained' is the minimum for optimal.
    # 'overtrained' is the maximum for optimal (anything above is overtrained).
    SCIENCE_BASED_THRESHOLDS = {
        # Upper Body
        'traps':      {'undertrained': 6, 'overtrained': 15}, # Mapped from Neck
        'delts':      {'undertrained': 8, 'overtrained': 22}, # Combined Shoulders
        'chest':      {'undertrained': 8, 'overtrained': 22},
        'back':       {'undertrained': 10, 'overtrained': 22},
        'biceps':     {'undertrained': 6, 'overtrained': 18},
        'triceps':    {'undertrained': 6, 'overtrained': 18},
        'forearms':   {'undertrained': 4, 'overtrained': 15},
        # Lower Body
        'quads':      {'undertrained': 8, 'overtrained': 22},
        'hams':       {'undertrained': 6, 'overtrained': 20},
        'glutes':     {'undertrained': 8, 'overtrained': 22},
        'calves':     {'undertrained': 6, 'overtrained': 18},
        # Core
        'abs':        {'undertrained': 4, 'overtrained': 15},
    }

    # --- 2. MAP GENERAL GROUPS TO THEIR CONSTITUENT SVG PARTS ---
    # This is crucial for applying the status correctly.
    MUSCLE_GROUP_TO_SVG_PARTS = {
        'traps':    ['right_trap', 'left_trap'],
        'delts':    ['left_front_delt', 'right_front_delt', 'left_side_delt', 'right_side_delt', 'left_rear_delt', 'right_rear_delt'],
        'chest':    ['chest'],
        'back':     ['back'],
        'biceps':   ['right_bicep', 'left_bicep'],
        'triceps':  ['right_tricep', 'left_tricep'],
        'forearms': ['right_forearm', 'left_forearm', 'backside_forearm_right', 'backside_forearm_left'],
        'quads':    ['right_quad', 'left_quad'],
        'hams':     ['right_hams', 'left_hams'],
        'glutes':   ['glutes'],
        'calves':   ['right_calf', 'left_calf', 'right_calf_back', 'left_calf_back'],
        'abs':      ['abs'],
    }

    # --- 3. FETCH WORKOUTS AND AGGREGATE SETS PER GENERAL MUSCLE GROUP ---
    last_7_days = date.today() - timedelta(days=7)
    workouts = Workout.objects.filter(user=request.user, date__gte=last_7_days)
    
    # We need to handle combined groups like 'shoulders'
    # The DB stores front_delt, side_delt, rear_delt. We'll map them to a single 'delts' key.
    GENERAL_GROUP_MAP = {
        'front_delt': 'delts',
        'side_delt': 'delts',
        'rear_delt': 'delts',
    }

    muscle_group_sets = defaultdict(int)
    for workout in workouts:
        # e.g., ['quads', 'glutes']
        groups_from_db = get_muscle_groups_from_db(workout.workout_name)
        for group in groups_from_db:
            # Normalize the group name (e.g., 'front_delt' becomes 'delts')
            normalized_group = GENERAL_GROUP_MAP.get(group.strip(), group.strip())
            muscle_group_sets[normalized_group] += workout.sets
            
    # --- 4. DETERMINE THE STATUS FOR EACH GENERAL MUSCLE GROUP ---
    muscle_group_status = {}
    for group, total_sets in muscle_group_sets.items():
        if group in SCIENCE_BASED_THRESHOLDS:
            th = SCIENCE_BASED_THRESHOLDS[group]
            if total_sets >= th['overtrained']:
                muscle_group_status[group] = 'overtrained'
            elif total_sets >= th['undertrained']:
                muscle_group_status[group] = 'well-trained' # This is the optimal range
            else:
                muscle_group_status[group] = 'undertrained'
        else:
            muscle_group_status[group] = '' # No threshold defined

    # --- 5. MAP THE STATUS FROM GENERAL GROUPS TO SPECIFIC SVG PARTS FOR THE TEMPLATE ---
    heatmap_status = {}
    # Initialize all parts to 'not-trained'
    for parts_list in MUSCLE_GROUP_TO_SVG_PARTS.values():
        for part in parts_list:
            heatmap_status[part] = '' # Default: not trained

    # Apply the calculated status
    for group, status in muscle_group_status.items():
        if group in MUSCLE_GROUP_TO_SVG_PARTS:
            for svg_part in MUSCLE_GROUP_TO_SVG_PARTS[group]:
                heatmap_status[svg_part] = status

    return render(request, 'fitness_tracker/heatmap.html', {'heatmap_status': heatmap_status})

#
# ... (ai_suggestion_view, profile_setup_view, etc. remain unchanged) ...
#
@login_required
def ai_suggestion_view(request):
    if request.method == 'POST':
        try:
            # --- Steps 1 and 2: Fetching profile and history (No changes) ---
            try:
                profile = UserProfile.objects.get(user=request.user)
                profile_text = (
                    f"My primary goal is '{profile.get_goal_display()}'. "
                    f"My training style is '{profile.get_training_style_display()}'. "
                )
            except UserProfile.DoesNotExist:
                profile_text = "My profile is not set up yet."

            three_days_ago = date.today() - timedelta(days=3)
            past_workouts = Workout.objects.filter(user=request.user, date__gte=three_days_ago).order_by('-date')
            
            workout_history_text = "Here is my workout history from the last 3 days:\n"
            if past_workouts:
                for workout in past_workouts:
                    workout_history_text += f"- On {workout.date.strftime('%A')}, I did: {workout.workout_name}.\n"
            else:
                workout_history_text = "I have not logged any workouts in the last 3 days."

            # --- Step 3: Building the prompt (No changes) ---
            user_prompt = request.POST.get('user_prompt')
            
            if user_prompt:
                prompt = (
                    f"You are an expert fitness coach. Use the user's profile and workout history as context to give a smart, personalized answer. "
                    f"Keep the response helpful and encouraging. Directly answer the user's question.\n\n"
                    f"USER PROFILE: {profile_text}\n"
                    f"WORKOUT HISTORY:\n{workout_history_text}\n\n"
                    f"USER'S QUESTION: '{user_prompt}'"
                )
            else:
                prompt = (
                    f"You are an expert fitness coach. Based on my profile and recent workout history, suggest a detailed workout plan for me for today. "
                    f"Tailor the exercises, sets, and reps to my specific goal and training style.\n\n"
                    f"USER PROFILE: {profile_text}\n"
                    f"RECENT HISTORY:\n{workout_history_text}\n\n"
                    f"The plan you create must include three distinct sections formatted with markdown:\n"
                    f"1. **Warm-up:** A brief warm-up routine.\n"
                    f"2. **Main Workout:** A list of exercises. For EACH exercise, provide a short explanation of how to perform the movement correctly.\n"
                    f"3. **Cool-down:** A brief cool-down routine."
                )
            
            # --- Step 4: Calling the AI Model (No changes) ---
            generation_config = genai.types.GenerationConfig(
                temperature=0.6,
                max_output_tokens=8192,
            )
            model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            response = model.generate_content(prompt, generation_config=generation_config)

            # --- THE FIX IS HERE: Robustly handle the response ---
            try:
                suggestion = response.text
            except ValueError:
                # This block runs if response.text fails, which happens on empty/blocked responses.
                suggestion = ("Sorry, the AI could not generate a response. This is often due to the safety filter "
                              "blocking the content. Please try asking in a different way.")

        except Exception as e:
            # This outer block catches other errors, like network issues.
            suggestion = f"Sorry, an unexpected error occurred: {e}"

        return JsonResponse({'suggestion': suggestion})

    return render(request, 'fitness_tracker/ai_suggestion.html')

@login_required
def profile_setup_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Check if the user wants to edit, or if their profile is incomplete
    edit_mode = request.GET.get('edit', 'false').lower() == 'true'
    profile_is_complete = profile.goal is not None

    # Show the form if in edit mode OR if the profile has never been filled out
    show_form = edit_mode or not profile_is_complete

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile_setup') # Redirect back to the same page to see the summary
    else:
        form = UserProfileForm(instance=profile)

    context = {
        'form': form,
        'profile': profile,
        'show_form': show_form,
    }
    return render(request, 'fitness_tracker/profile_setup.html', context)