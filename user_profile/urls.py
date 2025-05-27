from django.urls import path
from .views import ProfileUpdateView, CustomPasswordChangeView

app_name = 'user_profile'

urlpatterns = [
    path('update/', ProfileUpdateView.as_view(), name='profile_update'),
    path('change-password/', CustomPasswordChangeView.as_view(), name='change_password'),
]