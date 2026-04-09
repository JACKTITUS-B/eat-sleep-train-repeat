from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('log-workout/', views.log_workout_view, name='log_workout'),
    path('heatmap/', views.heatmap_view, name='heatmap'),
    path('ai-suggestion/', views.ai_suggestion_view, name='ai_suggestion'),
    path('profile-setup/', views.profile_setup_view, name='profile_setup'),
]
