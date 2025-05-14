# accounts/urls.py

from django.urls import path, re_path
# Import necessary views and TemplateView
from django.views.generic import TemplateView # Import TemplateView
from .views import (
    SignUpView, CustomLoginView, CustomLogoutView, HomeView,
    LogoutConfirmView, AccountActivationSentView, AccountActivateView,
    AccountActivationSuccessView, AccountActivationInvalidView,
    ResendActivationEmailView # Import the new resend view
)

app_name = 'accounts'  # Namespace for these app-specific URL names

urlpatterns = [
    # URL pattern for the signup page
    path('signup/', SignUpView.as_view(), name='signup'),

    # URL pattern for the login page
    path('login/', CustomLoginView.as_view(), name='login'),

    # URL pattern for the actual logout action (handles POST request)
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # URL pattern for the logout confirmation page (handles GET request)
    path('logout/confirm/', LogoutConfirmView.as_view(), name='logout_confirm'),

    # URL pattern for the "Activation Email Sent" page
    path('account-activation-sent/', AccountActivationSentView.as_view(), name='account_activation_sent'),

    # URL pattern for the email activation link processing using activation key
    path('activate/<str:activation_key>/', AccountActivateView.as_view(), name='activate'),

    # URL pattern for activation success page
    path('account-activation-success/', AccountActivationSuccessView.as_view(), name='account_activation_success'),
    # URL pattern for activation invalid page
    path('account-activation-invalid/', AccountActivationInvalidView.as_view(), name='account_activation_invalid'),

    # URL patterns for resending activation email
    path('resend-activation-email/', ResendActivationEmailView.as_view(), name='resend_activation_email'),
    # Use TemplateView directly here, so it needs to be imported
    path('resend-activation-email/sent/', TemplateView.as_view(template_name='accounts/resend_activation_email_sent.html'), name='resend_activation_email_sent'),


    # URL pattern for the homepage/dashboard
    path('', HomeView.as_view(), name='home'),
]
