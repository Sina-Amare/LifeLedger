# accounts/views.py

from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView, FormView # Import FormView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView # Import specific password reset views
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
        print("SignUpView: form_valid method reached.") # Debug print
        # Save the user but don't commit to the database yet
        user = form.save(commit=False)
        # Set the user as inactive initially
        user.is_active = False
        user.save()
        print(f"SignUpView: User '{user.username}' created (inactive).") # Debug print


        # Create a UserProfile for the new user
        profile, created = UserProfile.objects.get_or_create(user=user)
        if created:
             print(f"SignUpView: UserProfile created for '{user.username}'.") # Debug print
        # Generate and save the activation key in the profile
        profile.generate_activation_key() # This also saves the profile
        print(f"SignUpView: Activation key generated for '{user.username}'.") # Debug print


        current_site = get_current_site(self.request)
        mail_subject = 'Activate your LifeLedger account.'

        # Build the activation link URL using the activation key
        # The 'activate' URL name needs to be defined in accounts/urls.py
        activation_link = reverse('accounts:activate', kwargs={
            'activation_key': profile.activation_key, # Use the activation key
        })
        # Prepend the domain to make it a full URL
        activation_url = f'http://{current_site.domain}{activation_link}'
        print(f"SignUpView: Activation URL: {activation_url}") # Debug print


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

        try:
            print("SignUpView: Attempting to send activation email...") # Debug print
            send_mail(
                mail_subject,
                message_text,
                settings.EMAIL_HOST_USER, # Use the email address used for SMTP authentication
                [user.email],
                fail_silently=False,
                html_message=message_html,
            )
            print(f"SignUpView: Activation email sent to {user.email}.") # Debug print
        except Exception as e:
            print(f"SignUpView: Failed to send activation email: {e}") # Debug print
            # Optionally add a message to the user
            messages.error(self.request, "There was an error sending the activation email. Please try again later.")
            # Or handle the error differently


        # Redirect to the success URL (informing user to check email)
        print(f"SignUpView: Redirecting to {self.get_success_url()}") # Debug print
        return super().form_valid(form)


class CustomLoginView(LoginView):
    """
    View for user login using username or email.
    Provides a specific error message if the user is inactive.
    """
    template_name = 'accounts/login.html'
    form_class = UsernameEmailAuthenticationForm

    # Note: The inactive user check and specific error message logic
    # is now handled within the form's clean method.
    # The form_invalid method will still be called for any form errors,
    # including the inactive user error raised by the form.
    # We can keep this form_invalid method if we need to add messages
    # for other types of login errors in the future, but for now,
    # the form handles the inactive user message.
    # def form_invalid(self, form):
    #     return super().form_invalid(form)


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
        print(f"UsernameEmailBackend: Attempting to authenticate user: {username}") # Debug print
        try:
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
            print(f"UsernameEmailBackend: User '{user.username}' found.") # Debug print
        except User.DoesNotExist:
            print(f"UsernameEmailBackend: User with username/email '{username}' not found.") # Debug print
            return None

        # Check if the password is correct AND the user is active
        # The inactive check is already here, which prevents login.
        # The form's clean method will now add the specific message for inactive users.
        if user.check_password(password) and user.is_active:
            print(f"UsernameEmailBackend: Authentication successful for '{user.username}'.") # Debug print
            return user
        else:
            print(f"UsernameEmailBackend: Authentication failed for '{user.username}' (incorrect password or inactive).") # Debug print
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
        print(f"AccountActivateView: Activation key received: {activation_key}") # Debug print
        try:
            profile = UserProfile.objects.get(activation_key=activation_key)
            user = profile.user
            print(f"AccountActivateView: UserProfile and User found for key: {activation_key}") # Debug print
        except UserProfile.DoesNotExist:
            profile = None
            user = None
            print(f"AccountActivateView: UserProfile not found for key: {activation_key}") # Debug print


        if profile is not None and not user.is_active:
            profile.activate_user()
            print(f"AccountActivateView: User '{user.username}' activated.") # Debug print

            messages.success(request, 'Your account has been successfully activated! You can now log in.')
            print("AccountActivateView: Redirecting to activation success page.") # Debug print
            # Redirect to the success page
            return redirect('accounts:account_activation_success')


        else:
            print(f"AccountActivateView: Activation failed for key: {activation_key} (invalid key or user already active).") # Debug print
            messages.error(request, 'The activation link is invalid or has expired.')
            # Redirect to an error page
            print("AccountActivateView: Redirecting to activation invalid page.") # Debug print
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
        print("ResendActivationEmailView: form_valid method reached.") # Debug print
        user = form.user # Get the user object from the form's clean method
        print(f"ResendActivationEmailView: User found in form: {user.username}") # Debug print

        # Get the user's profile
        # Since we have a OneToOneField with related_name='profile', we can access it like this
        try:
            profile = user.profile
            print(f"ResendActivationEmailView: UserProfile found for {user.username}.") # Debug print
        except UserProfile.DoesNotExist:
            print(f"ResendActivationEmailView: UserProfile not found for {user.username}.") # Debug print
            messages.error(self.request, 'An unexpected error occurred. Please contact support.')
            return redirect('accounts:signup') # Or a dedicated error page

        # Generate a new activation key and save it
        profile.generate_activation_key() # This generates a new key and saves the profile
        print(f"ResendActivationEmailView: New activation key generated for {user.username}.") # Debug print


        current_site = get_current_site(self.request)
        mail_subject = 'Activate your LifeLedger account (Resent).' # Subject indicates it's a resend

        # Build the new activation link URL using the new activation key
        activation_link = reverse('accounts:activate', kwargs={
            'activation_key': profile.activation_key, # Use the NEW activation key
        })
        activation_url = f'http://{current_site.domain}{activation_link}'
        print(f"ResendActivationEmailView: New activation URL: {activation_url}") # Debug print


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

        try:
            print("ResendActivationEmailView: Attempting to send resent activation email...") # Debug print
            send_mail(
                mail_subject,
                message_text,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
                html_message=message_html,
            )
            print(f"ResendActivationEmailView: Resent activation email sent to {user.email}.") # Debug print
        except Exception as e:
            print(f"ResendActivationEmailView: Failed to send resent activation email: {e}") # Debug print
            messages.error(self.request, "There was an error sending the activation email. Please try again later.")


        messages.success(self.request, 'A new activation email has been sent. Please check your inbox.')

        # Call the parent class's form_valid to handle the redirect to success_url
        print(f"ResendActivationEmailView: Redirecting to {self.get_success_url()}") # Debug print
        return super().form_valid(form)

# Custom Password Reset Views (using Django's built-in views with custom templates)
# We don't need custom view classes unless we override methods like form_valid
# The templates specified in urls.py handle the rendering.

# Example if you needed to override PasswordResetView form_valid:
# class CustomPasswordResetView(PasswordResetView):
#     template_name = 'accounts/password_reset_form.html'
#     email_template_name = 'accounts/password_reset_email.txt'
#     subject_template_name = 'accounts/password_reset_subject.txt'
#     html_email_template_name = 'accounts/password_reset_email.html'
#     success_url = reverse_lazy('accounts:password_reset_done')
#
#     def form_valid(self, form):
#         print("CustomPasswordResetView: form_valid method reached.") # Debug print
#         # The parent class's form_valid handles sending the email
#         response = super().form_valid(form)
#         print("CustomPasswordResetView: Email sending triggered by parent.") # Debug print
#         return response

# Add debug prints to the built-in PasswordResetView if needed,
# but this requires overriding the view or inspecting Django's source.
# For now, rely on the mail.outbox check in the test.

