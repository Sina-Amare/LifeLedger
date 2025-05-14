# accounts/views.py

from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import get_user_model, login as auth_login
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

from .forms import CustomUserCreationForm, UsernameEmailAuthenticationForm
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
             'activation_url': activation_url, # Pass the full URL to the template
        })

        # --- FIX: Use settings.EMAIL_HOST_USER explicitly as the sender ---
        send_mail(
            mail_subject,
            message_text,
            settings.EMAIL_HOST_USER, # Use the email address used for SMTP authentication
            [user.email],
            fail_silently=False,
            html_message=message_html,
        )
        # --- End FIX ---


        # Redirect to the success URL (informing user to check email)
        return super().form_valid(form)


class CustomLoginView(LoginView):
    """View for user login using username or email."""
    template_name = 'accounts/login.html'
    form_class = UsernameEmailAuthenticationForm


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
            return None # No user found

        # Check if the password is correct AND the user is active
        if user.check_password(password) and user.is_active:
            return user # Password is correct and user is active
        else:
            return None # Password incorrect or user is inactive


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
            # Find the UserProfile with the given activation key
            profile = UserProfile.objects.get(activation_key=activation_key)
            user = profile.user # Get the related User object
        except UserProfile.DoesNotExist:
            # If no profile found with this key
            profile = None
            user = None # Ensure user is None if profile not found

        # Check if a profile with the key was found and the user is not already active
        if profile is not None and not user.is_active:
            # Activate the user and clear the activation key
            profile.activate_user() # This activates the user and clears the key

            # Redirect to a success page (e.g., login page with a message)
            return redirect('accounts:account_activation_success')
        else:
            # Key is invalid, user already active, or user does not exist
            # Redirect to an error page
            return redirect('accounts:account_activation_invalid')


class AccountActivationSentView(TemplateView):
    """
    View to inform the user that the activation email has been sent.
    """
    template_name = 'accounts/account_activation_sent.html'

    # This page is typically public, no LoginRequiredMixin needed.

class AccountActivationSuccessView(TemplateView):
    """
    View for the account activation success page.
    """
    template_name = 'accounts/account_activation_success.html'

class AccountActivationInvalidView(TemplateView):
    """
    View for the account activation invalid page.
    """
    template_name = 'accounts/account_activation_invalid.html'
