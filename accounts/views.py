# accounts/views.py

from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView, FormView # Import FormView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import get_user_model, login as auth_login, authenticate # Import authenticate
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str

from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages # Import the messages framework

from .forms import CustomUserCreationForm, UsernameEmailAuthenticationForm, ResendActivationEmailForm # Import the new forms
from .models import UserProfile # Import the new UserProfile model

User = get_user_model()


class HomeView(TemplateView):
    """
    View for the project's homepage/dashboard.
    Renders the public homepage for unauthenticated users
    and the dashboard for authenticated users.
    """
    def get_template_names(self):
        """
        Returns the template name based on user authentication status.
        """
        if self.request.user.is_authenticated:
            return ['accounts/dashboard.html']
        else:
            return ['home.html']


class SignUpView(CreateView):
    """
    View for user registration.
    Creates an inactive user, a UserProfile, and sends an activation email
    with a unique activation key.
    """
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:account_activation_sent')

    def form_valid(self, form):
        # Save the user but don't commit to the database yet
        user = form.save(commit=False)
        # Set the user as inactive initially
        user.is_active = False
        user.save()

        # Create a UserProfile for the new user
        profile = UserProfile.objects.create(user=user)
        # Generate and save the activation key in the profile
        profile.generate_activation_key() # This also saves the profile

        current_site = get_current_site(self.request)
        mail_subject = 'Activate your LifeLedger account.'

        # Build the activation link URL using the activation key
        # The 'activate' URL name needs to be defined in accounts/urls.py
        activation_link = reverse('accounts:activate', kwargs={
            'activation_key': profile.activation_key, # Use the activation key
        })
        # Prepend the domain to make it a full URL
        activation_url = f'http://{current_site.domain}{activation_link}'


        message_text = render_to_string('accounts/account_activation_email.txt', {
            'user': user,
            'domain': current_site.domain,
            'activation_url': activation_url, # Pass the full URL to the template
        })
        message_html = render_to_string('accounts/account_activation_email.html', {
             'user': user,
             'domain': current_site.domain,
             'activation_url': activation_url,
        })


        send_mail(
            mail_subject,
            message_text,
            settings.EMAIL_HOST_USER, # Use the email address used for SMTP authentication
            [user.email],
            fail_silently=False,
            html_message=message_html,
        )

        # Redirect to the success URL (informing user to check email)
        return super().form_valid(form)


class CustomLoginView(LoginView):
    """
    View for user login using username or email.
    Provides a specific error message if the user is inactive.
    """
    template_name = 'accounts/login.html'
    form_class = UsernameEmailAuthenticationForm

    def form_invalid(self, form):
        """
        Called when form data is invalid.
        Checks if the user exists but is inactive and adds a specific message.
        """
        # Get the username/email entered by the user
        username_or_email = form.cleaned_data.get('username') # Use 'username' as it's the field name in the form

        # Try to find the user based on the entered value
        if username_or_email:
            try:
                # Use authenticate to check if the user exists but is inactive
                # authenticate returns None if authentication fails (including inactive users)
                # We need to find the user first to check is_active status separately
                 user = User.objects.get(
                    Q(username__iexact=username_or_email) | Q(email__iexact=username_or_email)
                )
                 # If user is found but is inactive, add a specific message
                 if not user.is_active:
                    messages.error(
                        self.request,
                        "Your account is not active. Please check your email for the activation link or use the 'Resend Activation Email' option."
                    )
                    # Return the response from the parent class (which re-renders the form with errors)
                    return super().form_invalid(form)

            except User.DoesNotExist:
                # User not found, let the parent class handle the standard invalid login message
                pass # Continue to the parent's form_invalid

        # For all other invalid login attempts (incorrect password, user not found, etc.),
        # let the parent class handle the standard error message.
        return super().form_invalid(form)


class LogoutConfirmView(LoginRequiredMixin, TemplateView):
    """
    View to display the logout confirmation page.
    Requires user to be logged in.
    """
    template_name = 'accounts/logout_confirm.html'


class CustomLogoutView(LogoutView):
    """
    View to handle the actual user logout POST request.
    Redirects to the specified page after logout.
    """
    next_page = reverse_lazy('accounts:home')


class UsernameEmailBackend(ModelBackend):
    """
    Custom authentication backend that authenticates users using
    either their username or email address.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticates the user by attempting lookup based on username or email,
        then checking the password.
        """
        try:
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except User.DoesNotExist:
            return None

        # Check if the password is correct AND the user is active
        # The inactive check is already here, which prevents login.
        # The view's form_invalid method will add the specific message.
        if user.check_password(password) and user.is_active:
            return user
        else:
            return None


class AccountActivateView(View):
    """
    View to activate a user account via email link using an activation key.
    Processes the activation_key from the URL.
    """
    def get(self, request, activation_key, *args, **kwargs):
        """
        Handles GET requests for the activation link.
        Finds user by activation key and activates the user.
        """
        try:
            profile = UserProfile.objects.get(activation_key=activation_key)
            user = profile.user
        except UserProfile.DoesNotExist:
            profile = None
            user = None

        if profile is not None and not user.is_active:
            profile.activate_user()

            messages.success(request, 'Your account has been successfully activated! You can now log in.')

            # Redirect to the success page
            return redirect('accounts:account_activation_success')


        else:
            messages.error(request, 'The activation link is invalid or has expired.')
            # Redirect to an error page
            return redirect('accounts:account_activation_invalid')


# View to inform the user that the activation email has been sent
class AccountActivationSentView(TemplateView):
    """
    View to inform the user that the activation email has been sent.
    """
    template_name = 'accounts/account_activation_sent.html'

# View for the account activation success page
class AccountActivationSuccessView(TemplateView):
    """
    View for the account activation success page.
    """
    template_name = 'accounts/account_activation_success.html'

# View for the account activation invalid page
class AccountActivationInvalidView(TemplateView):
    """
    View for the account activation invalid page.
    """
    template_name = 'accounts/account_activation_invalid.html'


# View for requesting a new activation email
class ResendActivationEmailView(FormView):
    """
    View to display the form for requesting a new activation email
    and handle the form submission.
    """
    template_name = 'accounts/resend_activation_email.html'
    form_class = ResendActivationEmailForm
    success_url = reverse_lazy('accounts:resend_activation_email_sent')


    def form_valid(self, form):
        user = form.user # Get the user object from the form's clean method

        # Get the user's profile
        # Since we have a OneToOneField with related_name='profile', we can access it like this
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            # This case should ideally not happen if user was found but inactive,
            # but adding a check for robustness.
            messages.error(self.request, 'An unexpected error occurred. Please contact support.')
            return redirect('accounts:signup') # Or a dedicated error page

        # Generate a new activation key and save it
        profile.generate_activation_key() # This generates a new key and saves the profile

        current_site = get_current_site(self.request)
        mail_subject = 'Activate your LifeLedger account (Resent).' # Subject indicates it's a resend

        # Build the new activation link URL using the new activation key
        activation_link = reverse('accounts:activate', kwargs={
            'activation_key': profile.activation_key, # Use the NEW activation key
        })
        activation_url = f'http://{current_site.domain}{activation_link}'

        # Render email content (can reuse the same templates)
        message_text = render_to_string('accounts/account_activation_email.txt', {
            'user': user,
            'domain': current_site.domain,
            'activation_url': activation_url,
        })
        message_html = render_to_string('accounts/account_activation_email.html', {
             'user': user,
             'domain': current_site.domain,
             'activation_url': activation_url,
        })

        send_mail(
            mail_subject,
            message_text,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
            html_message=message_html,
        )

        messages.success(self.request, 'A new activation email has been sent. Please check your inbox.')

        # Call the parent class's form_valid to handle the redirect to success_url
        return super().form_valid(form)

