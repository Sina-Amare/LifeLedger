# user_profile/urls.py
from django.urls import path
from .views import (
    ProfileUpdateView,
    CustomPasswordChangeView,
    EmailChangeRequestView,     
    EmailChangeSentView,        
    EmailChangeConfirmView,     
    EmailChangeCompleteView,
    EmailChangeInvalidView      
)

app_name = 'user_profile'

urlpatterns = [
    path('update/', ProfileUpdateView.as_view(), name='profile_update'),
    path('change-password/', CustomPasswordChangeView.as_view(), name='change_password'),

    # URLs for Email Change Process
    path('change-email/', EmailChangeRequestView.as_view(), name='change_email_request'),
    path('change-email/sent/', EmailChangeSentView.as_view(), name='change_email_sent'),
    path(
        'change-email/confirm/<str:uidb64>/<str:token>/', # Using <str:...> for modern Django
        EmailChangeConfirmView.as_view(),
        name='change_email_confirm'
    ),
    # These are optional if EmailChangeConfirmView renders the success/invalid pages directly.
    # However, having named URLs can be useful for redirects or direct access if needed.
    path('change-email/complete/', EmailChangeCompleteView.as_view(), name='change_email_complete'),
    path('change-email/invalid/', EmailChangeInvalidView.as_view(), name='change_email_invalid'),
]