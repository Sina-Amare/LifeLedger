from django.urls import path
# Make sure to import CustomPasswordChangeView if it's not already imported
from .views import ProfileUpdateView, CustomPasswordChangeView 

app_name = 'user_profile' # Application namespace

urlpatterns = [
    path('update/', ProfileUpdateView.as_view(), name='profile_update'),
    # URL pattern for the custom password change view
    path('change-password/', CustomPasswordChangeView.as_view(), name='change_password'), 
]
