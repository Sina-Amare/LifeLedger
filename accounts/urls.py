# accounts/urls.py

from django.urls import path, re_path
# Import necessary views
from django.views.generic import TemplateView
# Import Django's built-in authentication views, including password reset views
from django.contrib.auth import views as auth_views

from .views import (
    SignUpView, CustomLoginView, CustomLogoutView, HomeView,
    LogoutConfirmView, AccountActivationSentView, AccountActivateView,
    AccountActivationSuccessView, AccountActivationInvalidView,
    ResendActivationEmailView
)

app_name = 'accounts'  # Namespace for these app-specific URL names

urlpatterns = [
    # --- Existing URLs ---
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('logout/confirm/', LogoutConfirmView.as_view(), name='logout_confirm'),
    path('account-activation-sent/', AccountActivationSentView.as_view(), name='account_activation_sent'),
    path('activate/<str:activation_key>/', AccountActivateView.as_view(), name='activate'),
    path('account-activation-success/', AccountActivationSuccessView.as_view(), name='account_activation_success'),
    path('account-activation-invalid/', AccountActivationInvalidView.as_view(), name='account_activation_invalid'),
    path('resend-activation-email/', ResendActivationEmailView.as_view(), name='resend_activation_email'),
    path('resend-activation-email/sent/', TemplateView.as_view(template_name='accounts/resend_activation_email_sent.html'), name='resend_activation_email_sent'),
    # --- End Existing URLs ---


    # --- Password Reset URLs ---
    # 1. Password reset form (request email)
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset_form.html',
             email_template_name='accounts/password_reset_email.txt', # Plain text email template
             subject_template_name='accounts/password_reset_subject.txt',
             html_email_template_name='accounts/password_reset_email.html', # Explicitly set HTML email template
             success_url=('/accounts/password-reset/done/') # Redirect after successful email
         ),
         name='password_reset'),

    # 2. Password reset done (inform user email sent)
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),

    # 3. Password reset confirm (set new password)
    # uidb64: user's ID encoded in base 64
    # token: token to check validity
    # Using a broader regex for uidb64 and token to avoid NoReverseMatch
    re_path(r'^password-reset/confirm/(?P<uidb64>[^/]+)/(?P<token>[^/]+)/$',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url=('/accounts/password-reset/complete/') # Redirect after successful password change
         ),
         name='password_reset_confirm'),

    # 4. Password reset complete (inform user password changed)
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    # --- End Password Reset URLs ---


    # --- Homepage URL ---
    path('', HomeView.as_view(), name='home'),
    # --- End Homepage URL ---
]
