from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView, FormView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import get_user_model, login as auth_login, authenticate
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string

from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages

from .forms import CustomUserCreationForm, UsernameEmailAuthenticationForm, ResendActivationEmailForm
from user_profile.models import UserProfile as NewUserProfile 
from journal.models import JournalEntry

User = get_user_model()

class HomeView(TemplateView):
    def get_template_names(self):
        if self.request.user.is_authenticated:
            return ['accounts/dashboard.html']
        else:
            return ['home.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['latest_entry'] = JournalEntry.objects.filter(user=self.request.user).order_by('-created_at').first()
        return context

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:account_activation_sent')

    def form_valid(self, form):
        print("SignUpView: form_valid method reached.")
        user = form.save(commit=False)
        user.is_active = False
        user.save() 
        print(f"SignUpView: User '{user.username}' created (inactive).")
        self.object = user
        try:
            profile = user.profile 
            if not isinstance(profile, NewUserProfile):
                print(f"SignUpView: Warning - user.profile is not an instance of NewUserProfile. Type: {type(profile)}. Attempting to fetch NewUserProfile directly.")
                profile = NewUserProfile.objects.get(user=user)
        except NewUserProfile.DoesNotExist:
            print(f"SignUpView: Error - NewUserProfile not found for '{user.username}' after signal. This is unexpected.")
            messages.error(self.request, "An error occurred during profile creation. Please contact support.")
            return redirect('accounts:signup') 
        except AttributeError: 
             print(f"SignUpView: Error - user.profile attribute not found for '{user.username}'. Attempting direct fetch.")
             try:
                profile = NewUserProfile.objects.get(user=user)
             except NewUserProfile.DoesNotExist:
                print(f"SignUpView: Critical Error - NewUserProfile not found for '{user.username}' even with direct fetch.")
                messages.error(self.request, "A critical error occurred. Please contact support.")
                return redirect('accounts:signup')
        
        if profile is None: # Added safeguard
            print(f"SignUpView: Critical Error - 'profile' is None for user {user.username} before generating key.")
            messages.error(self.request, "A critical profile error occurred. Please contact support.")
            return redirect('accounts:signup')

        print(f"SignUpView: Profile object type before generating key: {type(profile)}") # Debug type
        activation_key_value = profile.generate_activation_key_value()
        profile.activation_key = activation_key_value
        profile.save(update_fields=['activation_key', 'updated_at']) 
        print(f"SignUpView: Activation key generated and saved for '{user.username}' in NewUserProfile.")
        current_site = get_current_site(self.request)
        mail_subject = 'Activate your LifeLedger account.'
        activation_link = reverse('accounts:activate', kwargs={'activation_key': profile.activation_key})
        activation_url = f'http://{current_site.domain}{activation_link}'
        print(f"SignUpView: Activation URL: {activation_url}")
        message_text = render_to_string('accounts/account_activation_email.txt', {'user': user, 'activation_url': activation_url})
        message_html = render_to_string('accounts/account_activation_email.html', {'user': user, 'activation_url': activation_url})
        try:
            print("SignUpView: Attempting to send activation email...")
            send_mail(mail_subject, message_text, settings.EMAIL_HOST_USER, [user.email], fail_silently=False, html_message=message_html)
            print(f"SignUpView: Activation email sent to {user.email}.")
            messages.success(self.request, 'A confirmation email has been sent. Please check your inbox.')
        except Exception as e:
            print(f"SignUpView: Failed to send activation email: {e}")
            messages.error(self.request, "Error sending activation email. Please try again or contact support.")
        print(f"SignUpView: Redirecting to {self.get_success_url()}")
        return redirect(self.get_success_url())

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    form_class = UsernameEmailAuthenticationForm

class LogoutConfirmView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/logout_confirm.html'

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:home')

class AccountActivateView(View):
    def get(self, request, activation_key, *args, **kwargs):
        print(f"AccountActivateView: Activation key received: {activation_key}")
        profile = None # Initialize profile
        user = None # Initialize user
        try:
            profile = NewUserProfile.objects.select_related('user').get(activation_key=activation_key)
            user = profile.user
            print(f"AccountActivateView: NewUserProfile and User found for key: {activation_key}. Profile type: {type(profile)}")
        except NewUserProfile.DoesNotExist:
            print(f"AccountActivateView: NewUserProfile not found for key: {activation_key}")
            messages.error(request, 'The activation link is invalid or has expired.')
            return redirect('accounts:account_activation_invalid')

        if user is not None and not user.is_active:
            print(f"AccountActivateView: Attempting to activate user '{user.username}' via profile object: {profile}") # Debug object
            profile.activate_user_account() 
            print(f"AccountActivateView: User '{user.username}' activated via NewUserProfile.")
            messages.success(request, 'Your account has been successfully activated! You can now log in.')
            return redirect('accounts:account_activation_success')
        elif user is not None and user.is_active:
            print(f"AccountActivateView: User '{user.username}' is already active.")
            messages.info(request, 'Your account is already active. You can log in now.')
            return redirect('accounts:login')
        else:
            print(f"AccountActivateView: Activation failed for key: {activation_key} (user is None or other unexpected error).")
            messages.error(request, 'The activation link is invalid or has encountered an unexpected error.')
            return redirect('accounts:account_activation_invalid')

class AccountActivationSentView(TemplateView):
    template_name = 'accounts/account_activation_sent.html'
class AccountActivationSuccessView(TemplateView):
    template_name = 'accounts/account_activation_success.html'
class AccountActivationInvalidView(TemplateView):
    template_name = 'accounts/account_activation_invalid.html'

class ResendActivationEmailView(FormView):
    template_name = 'accounts/resend_activation_email.html'
    form_class = ResendActivationEmailForm
    success_url = reverse_lazy('accounts:resend_activation_email_sent')

    def form_valid(self, form):
        print("ResendActivationEmailView: form_valid method reached.")
        user = form.user 
        print(f"ResendActivationEmailView: User found in form: {user.username}")
        profile = None # Initialize profile

        if user.is_active:
            print(f"ResendActivationEmailView: User '{user.username}' is already active.")
            messages.info(self.request, 'Your account is already active. You can log in.')
            return redirect('accounts:login')
        try:
            profile = user.profile
            if not isinstance(profile, NewUserProfile):
                 print(f"ResendActivationEmailView: Warning - user.profile is not NewUserProfile. Type: {type(profile)}. Fetching directly.")
                 profile = NewUserProfile.objects.get(user=user)
            # DEBUGGING LINES ADDED HERE
            print(f"ResendActivationEmailView: Profile supposedly found for {user.username}.")
            print(f"ResendActivationEmailView: Type of 'profile' variable is: {type(profile)}")
            print(f"ResendActivationEmailView: Is 'profile' an instance of NewUserProfile? {isinstance(profile, NewUserProfile)}")

        except NewUserProfile.DoesNotExist:
            print(f"ResendActivationEmailView: Error - NewUserProfile.DoesNotExist for {user.username} during fetch.")
            messages.error(self.request, "Could not find a profile for your account. Please contact support.")
            return redirect('accounts:resend_activation_email')
        except AttributeError:
             print(f"ResendActivationEmailView: AttributeError - user.profile likely not found for {user.username}. Attempting direct fetch.")
             try:
                profile = NewUserProfile.objects.get(user=user)
                print(f"ResendActivationEmailView: Profile fetched directly. Type: {type(profile)}")
             except NewUserProfile.DoesNotExist:
                print(f"ResendActivationEmailView: Error - NewUserProfile.DoesNotExist for {user.username} even with direct fetch.")
                messages.error(self.request, "A critical profile error occurred. Please contact support.")
                return redirect('accounts:resend_activation_email')
        
        if profile is None: # Safeguard
            print(f"ResendActivationEmailView: Critical Error - 'profile' is None before calling method for user {user.username}.")
            messages.error(self.request, "A critical error occurred with the user profile. Please contact support.")
            return redirect('accounts:resend_activation_email')

        print(f"ResendActivationEmailView: Attempting to call generate_activation_key_value on profile object: {profile} of type {type(profile)}")
        new_key = profile.generate_activation_key_value() # Error occurs here
        profile.activation_key = new_key
        profile.save(update_fields=['activation_key', 'updated_at'])
        print(f"ResendActivationEmailView: New activation key generated for {user.username} in NewUserProfile.")

        current_site = get_current_site(self.request)
        mail_subject = 'Activate your LifeLedger account (Resent).'
        activation_link = reverse('accounts:activate', kwargs={'activation_key': profile.activation_key})
        activation_url = f'http://{current_site.domain}{activation_link}'
        print(f"ResendActivationEmailView: New activation URL: {activation_url}")
        message_text = render_to_string('accounts/account_activation_email.txt', {'user': user, 'activation_url': activation_url})
        message_html = render_to_string('accounts/account_activation_email.html', {'user': user, 'activation_url': activation_url})
        try:
            print("ResendActivationEmailView: Attempting to send resent activation email...")
            send_mail(mail_subject, message_text, settings.EMAIL_HOST_USER, [user.email], fail_silently=False, html_message=message_html)
            print(f"ResendActivationEmailView: Resent activation email sent to {user.email}.")
            messages.success(self.request, 'A new activation email has been sent. Please check your inbox.')
        except Exception as e:
            print(f"ResendActivationEmailView: Failed to send resent activation email: {e}")
            messages.error(self.request, "Error resending activation email. Please try again or contact support.")
        print(f"ResendActivationEmailView: Redirecting to {self.get_success_url()}")
        return super().form_valid(form)

class UsernameEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        print(f"\nUsernameEmailBackend: Attempting to authenticate user: {username}")
        try:
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
            print(f"UsernameEmailBackend: User '{user.username}' found.")
        except User.DoesNotExist:
            print(f"UsernameEmailBackend: User with username/email '{username}' not found.")
            return None
        if user.check_password(password) and user.is_active:
            print(f"UsernameEmailBackend: Authentication successful for '{user.username}'.")
            return user
        else:
            if not user.is_active:
                print(f"UsernameEmailBackend: Authentication failed for '{user.username}' (user is inactive).")
            else: 
                print(f"UsernameEmailBackend: Authentication failed for '{user.username}' (incorrect password).")
            return None
