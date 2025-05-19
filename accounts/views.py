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
from django.http import Http404, HttpResponseRedirect # Import HttpResponseRedirect if needed, but redirect is simpler

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
# from django.utils.http import urlsafe_base64_encode # Not used in your code, but common for activation links

from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages # Import the messages framework

from .forms import CustomUserCreationForm, UsernameEmailAuthenticationForm, ResendActivationEmailForm # Import the new forms
from .models import UserProfile # Import the new UserProfile model
from journal.models import JournalEntry  # Added import

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

    def get_context_data(self, **kwargs):
        """
        Adds latest journal entry to context for authenticated users.
        """
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['latest_entry'] = JournalEntry.objects.filter(user=self.request.user).order_by('-created_at').first()
        return context

class SignUpView(CreateView):
    """
    View for user registration.
    Creates an inactive user, a UserProfile, and sends an activation email
    with a unique activation key.
    """
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:account_activation_sent') # URL to redirect after successful signup (informing user email sent)

    def form_valid(self, form):
        print("SignUpView: form_valid method reached.") # Debug print
        # Save the user but don't commit to the database yet
        user = form.save(commit=False)
        # Set the user as inactive initially
        user.is_active = False
        user.save()
        print(f"SignUpView: User '{user.username}' created (inactive).") # Debug print

        # Set self.object with the saved user instance
        # This is necessary when manually saving the form instance in form_valid
        self.object = user # <--- Added this line

        # Create a UserProfile for the new user
        # Use get_or_create in case a profile was somehow created earlier (e.g., in a signal)
        # Although in this flow, it should always be 'created'.
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
        # The domain comes from the Sites framework (django.contrib.sites)
        # You need to update the domain for Site ID 1 in Django Admin
        activation_url = f'http://{current_site.domain}{activation_link}'
        print(f"SignUpView: Activation URL: {activation_url}") # Debug print


        # Render email templates
        message_text = render_to_string('accounts/account_activation_email.txt', {
            'user': user,
            'domain': current_site.domain, # This variable is still available but the URL uses activation_url
            'activation_url': activation_url, # Pass the full URL to the template
        })
        message_html = render_to_string('accounts/account_activation_email.html', {
            'user': user,
            'domain': current_site.domain, # This variable is still available but the URL uses activation_url
            'activation_url': activation_url,
        })

        # Send email
        try:
            print("SignUpView: Attempting to send activation email...") # Debug print
            send_mail(
                mail_subject,
                message_text, # Plain text body
                settings.EMAIL_HOST_USER, # Use the email address used for SMTP authentication
                [user.email], # Recipient list
                fail_silently=False, # Raise exception if email fails
                html_message=message_html, # HTML body
            )
            print(f"SignUpView: Activation email sent to {user.email}.") # Debug print
            messages.success(self.request, 'A confirmation email has been sent. Please check your inbox to activate your account.') # Success message
        except Exception as e:
            print(f"SignUpView: Failed to send activation email: {e}") # Debug print
            # Optionally add a message to the user
            messages.error(self.request, "There was an error sending the activation email. Please try again later.")
            # Consider logging this error properly in a real application

        # Redirect to the success URL (informing user to check email)
        print(f"SignUpView: Redirecting to {self.get_success_url()}") # Debug print
        # Do NOT call super().form_valid(form) after manually saving and setting self.object.
        # Instead, return a redirect response directly.
        return redirect(self.get_success_url()) # <--- Added this line

    # If you need to perform actions on form invalidation, uncomment this:
    # def form_invalid(self, form):
    #     print("SignUpView: form_invalid method reached.") # Debug print
    #     return super().form_invalid(form)


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
            user = UserProfile.objects.get( # Look up UserProfile first to get user and check activation_key status early
                 # Use get_or_None if needed, but catching DoesNotExist is fine
                Q(user__username__iexact=username) | Q(user__email__iexact=username)
            ).user # Get the user object from the profile

            print(f"UsernameEmailBackend: User profile found for username/email: {username}.") # Debug print


        except UserProfile.DoesNotExist:
             # If no user profile found with that username/email, try finding the user directly
             # This handles cases where a user might exist but have no profile (unlikely with current flow)
             # or if the initial lookup by profile failed.
             print(f"UsernameEmailBackend: User profile not found for username/email: {username}. Trying direct user lookup.") # Debug print
             try:
                  user = get_user_model().objects.get(
                      Q(username__iexact=username) | Q(email__iexact=username)
                  )
                  print(f"UsernameEmailBackend: User '{user.username}' found via direct lookup.") # Debug print
             except get_user_model().DoesNotExist:
                   print(f"UsernameEmailBackend: User '{username}' not found.") # Debug print
                   return None # User not found at all


        # If a user object was found (either via profile or direct lookup)
        if user is not None:
             # Check if the password is correct AND the user is active
             # The inactive check is already here, which prevents login.
             # The form's clean method will now add the specific message for inactive users.
             if user.check_password(password) and user.is_active:
                 print(f"UsernameEmailBackend: Authentication successful for '{user.username}'.") # Debug print
                 return user
             else:
                 # Password incorrect or user is inactive.
                 # The form's clean method will handle the inactive message.
                 # For incorrect password, the form's default error handles it.
                 print(f"UsernameEmailBackend: Authentication failed for '{user.username}' (incorrect password or inactive).") # Debug print
                 return None # Authentication failed
        else:
            # This case should be covered by the DoesNotExist checks above, but for safety:
            print("UsernameEmailBackend: Authentication failed - User object is None after lookup attempts.")
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
            # Use select_related to fetch the related user in the same query
            profile = UserProfile.objects.select_related('user').get(activation_key=activation_key)
            user = profile.user
            print(f"AccountActivateView: UserProfile and User found for key: {activation_key}") # Debug print
        except UserProfile.DoesNotExist:
            profile = None
            user = None
            print(f"AccountActivateView: UserProfile not found for key: {activation_key}") # Debug print
            messages.error(request, 'The activation link is invalid or has expired.')
            print("AccountActivateView: Redirecting to activation invalid page due to invalid key.") # Debug print
            return redirect('accounts:account_activation_invalid') # Redirect to error page

        # If profile was found and the user is not already active
        if user is not None and not user.is_active:
            profile.activate_user() # This activates the user and clears the key
            print(f"AccountActivateView: User '{user.username}' activated.") # Debug print

            messages.success(request, 'Your account has been successfully activated! You can now log in.')
            print("AccountActivateView: Redirecting to activation success page.") # Debug print
            # Redirect to the success page
            return redirect('accounts:account_activation_success')


        else:
            # Profile was found, but user is already active OR user is None (should be caught by except)
            print(f"AccountActivateView: Activation failed for key: {activation_key} (user already active or unexpected error).") # Debug print
            # If user was already active, show a message indicating that.
            if user is not None and user.is_active:
                 messages.info(request, 'Your account is already active. You can log in now.')
                 print("AccountActivateView: Redirecting to login page (user already active).") # Debug print
                 return redirect('accounts:login') # Redirect to login page
            else:
                 # This case should ideally not be reached if the initial try/except handles DoesNotExist
                 messages.error(request, 'The activation link is invalid or has expired.')
                 print("AccountActivateView: Redirecting to activation invalid page (unexpected scenario).") # Debug print
                 return redirect('accounts:account_activation_invalid') # Redirect to error page


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

        # Check if user is already active
        if user.is_active:
             print(f"ResendActivationEmailView: User '{user.username}' is already active. Not sending email.") # Debug print
             messages.info(self.request, 'Your account is already active. You can log in now.')
             return redirect('accounts:login') # Redirect to login page if already active


        # Get the user's profile
        # Since we have a OneToOneField with related_name='profile', we can access it like this
        try:
            profile = user.profile
            print(f"ResendActivationEmailView: UserProfile found for {user.username}.") # Debug print
        except UserProfile.DoesNotExist:
            print(f"ResendActivationEmailView: UserProfile not found for {user.username}. Creating one.") # Debug print
            # It's possible a user exists but profile doesn't, though unlikely with signup flow
            profile = UserProfile.objects.create(user=user)
            messages.warning(self.request, 'A profile was created for your account.')


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
            'domain': current_site.domain, # Still available, but activation_url is used in template
            'activation_url': activation_url,
        })
        message_html = render_to_string('accounts/account_activation_email.html', {
            'user': user,
            'domain': current_site.domain, # Still available, but activation_url is used in template
            'activation_url': activation_url,
        })

        # Send email
        try:
            print("ResendActivationEmailView: Attempting to send resent activation email...") # Debug print
            send_mail(
                mail_subject,
                message_text, # Plain text body
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
                html_message=message_html,
            )
            print(f"ResendActivationEmailView: Resent activation email sent to {user.email}.") # Debug print
            messages.success(self.request, 'A new activation email has been sent. Please check your inbox.') # Success message
        except Exception as e:
            print(f"ResendActivationEmailView: Failed to send resent activation email: {e}") # Debug print
            messages.error(self.request, "There was an error sending the activation email. Please try again later.")
            # Consider logging this error


        # Call the parent class's form_valid to handle the redirect to success_url
        # In FormView, super().form_valid just returns the response from get_success_url()
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


# --- Custom Backend (already included in previous steps, keeping for completeness) ---
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
        print(f"\nUsernameEmailBackend: Attempting to authenticate user: {username}") # Debug print
        try:
            # Use Q objects for case-insensitive lookup across username and email
            user = get_user_model().objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
            print(f"UsernameEmailBackend: User '{user.username}' found.") # Debug print

        except get_user_model().DoesNotExist:
            print(f"UsernameEmailBackend: User with username/email '{username}' not found.") # Debug print
            return None


        # Check if the password is correct AND the user is active
        # The inactive check is also in the form's clean method for a specific message.
        # This backend check ensures only active users can authenticate.
        if user.check_password(password) and user.is_active:
            print(f"UsernameEmailBackend: Authentication successful for '{user.username}'.") # Debug print
            return user
        else:
            # Password incorrect or user is inactive.
            # The form's clean method will handle the inactive message.
            # For incorrect password, the form's default error handles it.
            print(f"UsernameEmailBackend: Authentication failed for '{user.username}' (incorrect password or inactive).") # Debug print
            return None

# --- End Custom Backend ---


# The get_user_model() call should be outside any model definitions
# User = get_user_model() # Removed based on previous troubleshooting
