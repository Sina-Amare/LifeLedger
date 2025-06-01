import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import get_password_validators
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.views import View

from .forms import (CurrentPasswordConfirmForm, EmailChangeRequestForm,
                    NewPasswordSetForm, UserProfileUpdateForm, UserUpdateForm)
from .models import UserProfile
from .tokens import email_change_token_generator

User = get_user_model()
logger = logging.getLogger(__name__) # Setup a logger for this module

class ProfileUpdateView(LoginRequiredMixin, View):
    """
    Allows authenticated users to update their basic user information
    (first name, last name) and their extended profile details.
    """
    template_name = 'user_profile/profile_update_form.html'
    success_url = reverse_lazy('user_profile:profile_update')

    def get(self, request, *args, **kwargs):
        user_form = UserUpdateForm(instance=request.user)
        # Ensure a UserProfile instance exists for the logged-in user.
        profile_instance, profile_was_created = UserProfile.objects.get_or_create(user=request.user)
        profile_form = UserProfileUpdateForm(instance=profile_instance)
        context = {
            'user_form': user_form,
            'profile_form': profile_form,
            'page_title': _('Edit Profile'),
            'active_section': 'profile_update'
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user_form = UserUpdateForm(request.POST, instance=request.user)
        # Ensure a UserProfile instance exists for handling the POST data.
        profile_instance, profile_was_created_on_post = UserProfile.objects.get_or_create(user=request.user)
        profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile_instance)

        if user_form.is_valid() and profile_form.is_valid():
            try:
                user_form.save()
                profile_form.save()
                messages.success(request, _('Your profile has been updated successfully!'))
                return redirect(self.success_url)
            except Exception as e:
                logger.error(
                    f"Error updating profile for {request.user.username}: {e}",
                    exc_info=True # Include traceback information in the log
                )
                messages.error(request, _("An unexpected error occurred while saving your profile. Please try again."))
        else:
            # Consolidate error messages from both forms for clearer user feedback.
            error_messages = []
            for form_instance in [user_form, profile_form]:
                for field, errors in form_instance.errors.items():
                    field_label = form_instance.fields[field].label if field != '__all__' and hasattr(form_instance.fields[field], 'label') else ""
                    label_prefix = f"{field_label}: " if field_label else ""
                    for error in errors:
                        error_messages.append(f"{label_prefix}{error}")
            
            if error_messages:
                messages.error(request, _('Please correct the errors below: ') + " | ".join(error_messages))
            else:
                # Fallback message if forms are invalid but no specific errors are collected (should be rare).
                messages.error(request, _('Please correct the errors below.'))

        context = {
            'user_form': user_form,
            'profile_form': profile_form,
            'page_title': _('Edit Profile'),
            'active_section': 'profile_update'
        }
        return render(request, self.template_name, context)


class CustomPasswordChangeView(LoginRequiredMixin, View):
    """
    Handles the two-stage password change process for authenticated users:
    1. User confirms their current password.
    2. User sets and confirms their new password.
    """
    template_name = 'user_profile/change_password.html'
    current_password_form_class = CurrentPasswordConfirmForm
    new_password_form_class = NewPasswordSetForm
    success_url = reverse_lazy('user_profile:change_password') # Redirect to self shows success message

    SESSION_KEY_PASSWORD_CONFIRMED = 'current_password_confirmed_for_password_change_v2' # More specific key

    def _get_password_validator_help_texts(self):
        """Retrieves and returns help texts from configured AUTH_PASSWORD_VALIDATORS."""
        try:
            validators = get_password_validators(settings.AUTH_PASSWORD_VALIDATORS)
            return [v.get_help_text() for v in validators]
        except Exception as e:
            logger.error(f"Error retrieving password validator help texts: {e}", exc_info=True)
            return []

    def get_context_data(self, **kwargs):
        """Prepares context data for the template, determining the current stage."""
        context = {'active_section': 'change_password'}
        if self.request.session.get(self.SESSION_KEY_PASSWORD_CONFIRMED, False):
            context['stage'] = 2
            context['new_password_form'] = self.new_password_form_class(user=self.request.user)
            context['page_title'] = _('Set New Password')
            context['password_validators_help_texts'] = self._get_password_validator_help_texts()
        else:
            context['stage'] = 1
            context['current_password_form'] = self.current_password_form_class(user=self.request.user)
            context['page_title'] = _('Confirm Current Password')
        context.update(kwargs)
        return context

    def get(self, request, *args, **kwargs):
        """Handles GET requests, displaying the appropriate stage of the password change form."""
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        """Handles POST requests for both password confirmation and new password setting."""
        context_for_rerender = self.get_context_data() # Base context for the current stage

        # Stage 1: Current password confirmation
        if 'current_password' in request.POST:
            form = self.current_password_form_class(request.POST, user=request.user)
            if form.is_valid():
                request.session[self.SESSION_KEY_PASSWORD_CONFIRMED] = True
                messages.success(request, _("Current password confirmed. Please set your new password."))
                return redirect(request.path) # Redirect to GET to show stage 2
            else:
                # Provide helpful messages if password confirmation fails.
                messages.error(request, _("Password confirmation failed. Please check your current password."))
                if not request.user.has_usable_password():
                     messages.info(request, _("If you signed up via a social account and haven't set a password, you might need to use the 'Forgot Password' feature."))
                else:
                    messages.info(request, _("If you've forgotten your current password, you can use the 'Forgot Password' link on the login page after logging out."))
                context_for_rerender['current_password_form'] = form
                context_for_rerender['stage'] = 1 # Ensure re-render shows stage 1
                return render(request, self.template_name, context_for_rerender)

        # Stage 2: New password submission
        elif 'new_password1' in request.POST:
            if not request.session.get(self.SESSION_KEY_PASSWORD_CONFIRMED, False):
                messages.error(request, _("Security check failed. Please confirm your current password first to set a new one."))
                if self.SESSION_KEY_PASSWORD_CONFIRMED in request.session: # Clean up stale session key
                    del request.session[self.SESSION_KEY_PASSWORD_CONFIRMED]
                return redirect(request.path) # Restart the process

            form = self.new_password_form_class(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user) # Keep the user logged in
                if self.SESSION_KEY_PASSWORD_CONFIRMED in request.session:
                    del request.session[self.SESSION_KEY_PASSWORD_CONFIRMED]
                messages.success(request, _('Your password has been changed successfully!'))
                return redirect(self.success_url)
            else:
                messages.error(request, _('Please correct the errors below to set your new password.'))
                context_for_rerender['new_password_form'] = form
                context_for_rerender['stage'] = 2 # Ensure re-render shows stage 2
                context_for_rerender['password_validators_help_texts'] = self._get_password_validator_help_texts()
                return render(request, self.template_name, context_for_rerender)

        # Fallback for unexpected POST data or missing stage identifiers
        messages.error(request, _("Invalid form submission. Please start over."))
        return redirect(request.path)


class EmailChangeRequestView(LoginRequiredMixin, View):
    """
    Manages the multi-stage process for a user to change their email address.
    This involves confirming the current password, then entering and verifying
    the new email address via a confirmation link sent to it.
    """
    template_name = 'user_profile/change_email_form.html'
    form_class = EmailChangeRequestForm
    success_redirect_url_name = 'user_profile:change_email_sent' # Named URL for redirection

    # Use a specific session key to avoid clashes with other multi-stage forms.
    SESSION_KEY_EMAIL_PASSWORD_CONFIRMED = 'email_change_password_confirmed_v3'

    def _send_email_change_verification(self, user_instance, new_email_address):
        """
        Constructs and sends the email change verification email.

        Args:
            user_instance (User): The user requesting the email change.
            new_email_address (str): The new email address to be verified.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        current_site = get_current_site(self.request)
        mail_subject = _('Confirm Your New Email Address for LifeLedger')
        
        # The token's hash incorporates user.profile.pending_new_email.
        # This field must be set on the profile before make_token is called.
        if not hasattr(user_instance, 'profile') or not user_instance.profile.pending_new_email:
            logger.error(
                f"Attempted to generate email change token for {user_instance.username} "
                f"without user.profile.pending_new_email being set."
            )
            return False

        token = email_change_token_generator.make_token(user_instance)
        uid = urlsafe_base64_encode(force_bytes(user_instance.pk))
        
        try:
            verification_path = reverse('user_profile:change_email_confirm', kwargs={'uidb64': uid, 'token': token})
        except Exception as e: # Catch potential NoReverseMatch or other errors
            logger.error(f"Could not reverse URL for email change confirmation: {e}", exc_info=True)
            messages.error(self.request, _("A system error occurred. Could not generate verification link."))
            return False

        protocol = 'https' if self.request.is_secure() else 'http'
        verification_link = f"{protocol}://{current_site.domain}{verification_path}"
        
        email_context = {
            'user': user_instance,
            'new_email': new_email_address,
            'verification_link': verification_link,
            'site_name': current_site.name,
        }
        
        text_content = render_to_string('user_profile/email/email_change_verification_email.txt', email_context)
        html_content = render_to_string('user_profile/email/email_change_verification_email.html', email_context)
        
        try:
            email_message = EmailMultiAlternatives(
                subject=mail_subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL, # Use system's default sender
                to=[new_email_address]
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()
        except Exception as e:
            logger.error(
                f"Error sending email change verification to {new_email_address} for user {user_instance.username}: {e}",
                exc_info=True
            )
            messages.error(self.request, _("Could not send the verification email. Please try again later or contact support if the problem persists."))
            return False
        return True

    def get_context_data(self, **kwargs):
        """Prepares context for the template, determining the current display stage."""
        context = {
            'active_section': 'change_email', # For sidebar navigation highlighting
            'current_email': self.request.user.email,
            'form': self.form_class(request=self.request) # Initialize with request for user access
        }
        
        if self.request.session.get(self.SESSION_KEY_EMAIL_PASSWORD_CONFIRMED, False):
            context['stage'] = 2  # Stage 2: User enters new email
            context['page_title'] = _('Enter New Email Address')
        else:
            context['stage'] = 1  # Stage 1: User confirms current password
            context['page_title'] = _('Confirm Password to Change Email')
        
        context.update(kwargs) # Allow additional context to be passed
        return context

    def get(self, request, *args, **kwargs):
        """Displays the form appropriate for the current stage of the email change process."""
        profile = request.user.profile
        # If the user navigates back to stage 1 (e.g., via URL or browser back button)
        # and their password isn't confirmed in the session, clear any stale pending email change data.
        if not request.session.get(self.SESSION_KEY_EMAIL_PASSWORD_CONFIRMED) and \
           (profile.pending_new_email or profile.email_change_token_key):
            profile.clear_email_change_data()

        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        """Handles form submissions for both password confirmation (stage 1) and new email entry (stage 2)."""
        profile = request.user.profile
        form = self.form_class(request.POST, request=request)

        # Stage 1: Current password confirmation
        if 'submit_current_password' in request.POST:
            # The form's clean_current_password handles the actual password check.
            if form.is_valid() and form.cleaned_data.get('current_password'):
                request.session[self.SESSION_KEY_EMAIL_PASSWORD_CONFIRMED] = True
                messages.success(request, _("Password confirmed. Please enter your new email address."))
                return redirect(request.path) # Redirect to GET to display stage 2
            else:
                # If 'current_password' was submitted but is invalid, form.errors will contain details.
                # If it wasn't submitted at all, add a generic error.
                if 'current_password' in request.POST and not request.POST.get('current_password'):
                     form.add_error('current_password', _("This field is required."))
                # Use a generic message if specific errors aren't already on the field.
                if not form.errors.get('current_password'):
                     form.add_error('current_password', _("Password confirmation failed. Please check your password and try again."))
                return render(request, self.template_name, self.get_context_data(form=form, stage=1))

        # Stage 2: New email submission
        elif 'submit_new_email' in request.POST:
            if not request.session.get(self.SESSION_KEY_EMAIL_PASSWORD_CONFIRMED, False):
                messages.error(request, _("Security check failed. Please confirm your current password first."))
                return redirect(request.path) # Restart the process

            # Form validation for new_email (uniqueness, different from old) occurs in form.is_valid()
            if form.is_valid() and form.cleaned_data.get('new_email'):
                new_email = form.cleaned_data['new_email']
                
                # Store pending data on the profile.
                profile.pending_new_email = new_email
                profile.email_change_token_key_created_at = timezone.now()
                profile.save(update_fields=['pending_new_email', 'email_change_token_key_created_at'])
                
                # Generate and store the token (depends on pending_new_email being set).
                profile.email_change_token_key = email_change_token_generator.make_token(request.user)
                profile.save(update_fields=['email_change_token_key'])

                if self._send_email_change_verification(request.user, new_email):
                    messages.success(request, _("A verification email has been sent to {email}. Please check your inbox to complete the change.").format(email=new_email))
                    if self.SESSION_KEY_EMAIL_PASSWORD_CONFIRMED in request.session:
                        del request.session[self.SESSION_KEY_EMAIL_PASSWORD_CONFIRMED] # Clear session key
                    return redirect(reverse(self.success_redirect_url_name))
                else:
                    # Error message is typically handled by _send_email_change_verification.
                    # Clear pending data as sending failed to allow user to retry.
                    profile.clear_email_change_data()
                    # Re-render stage 2 with form; _send_email_change_verification already added a message.
                    return render(request, self.template_name, self.get_context_data(form=form, stage=2))
            else:
                # If 'new_email' was expected but not provided or invalid.
                if 'new_email' in request.POST and not request.POST.get('new_email'):
                     form.add_error('new_email', _("This field is required."))
                if not form.errors: # General error if form is invalid without specific field errors
                    messages.error(request, _("Please correct the information provided for your new email address."))
                return render(request, self.template_name, self.get_context_data(form=form, stage=2))

        # Fallback for submissions that don't match expected stages.
        messages.error(request, _("An unexpected error occurred. Please try the process again."))
        return redirect(request.path)


class EmailChangeSentView(LoginRequiredMixin, View):
    """
    Displays a simple confirmation message after the email change verification
    link has been successfully dispatched to the user's new email address.
    """
    template_name = 'user_profile/change_email_sent.html'

    def get(self, request, *args, **kwargs):
        context = {
            'page_title': _('Verification Email Sent'),
            'active_section': 'change_email', # For sidebar consistency
        }
        return render(request, self.template_name, context)


class EmailChangeConfirmView(LoginRequiredMixin, View):
    """
    Handles the verification link clicked by the user from their email
    to confirm and finalize the email address change.
    """
    template_name_success = 'user_profile/change_email_complete.html'
    template_name_invalid = 'user_profile/change_email_invalid.html'
    TOKEN_TIMEOUT_DAYS = getattr(settings, 'EMAIL_CHANGE_TOKEN_TIMEOUT_DAYS', 1) # Configurable timeout

    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, AttributeError):
            user = None # Handle cases where uid is invalid or user does not exist

        profile = getattr(user, 'profile', None)

        # Basic validation: user, profile, token match, and a pending email exists
        if not (user and profile and profile.email_change_token_key == token and profile.pending_new_email):
            messages.error(request, _("This email change link is invalid or has already been used."))
            if profile: profile.clear_email_change_data() # Clean up potentially stale data
            return render(request, self.template_name_invalid, {'page_title': _('Invalid Link')})

        # Check token creation timestamp for expiry
        if not profile.email_change_token_key_created_at:
            messages.error(request, _("The email change link is incomplete (missing creation date). Please try again."))
            profile.clear_email_change_data()
            return render(request, self.template_name_invalid, {'page_title': _('Invalid Link')})

        expiry_date = profile.email_change_token_key_created_at + timedelta(days=self.TOKEN_TIMEOUT_DAYS)
        if timezone.now() > expiry_date:
            messages.error(request, _("This email change link has expired. Please request a new one."))
            profile.clear_email_change_data() # Clear expired data
            return render(request, self.template_name_invalid, {'page_title': _('Link Expired')})

        # Final, more robust token check using the generator
        if email_change_token_generator.check_token(user, token):
            # Successfully verified, proceed with email change
            # old_email = user.email # Could be used for logging or notifying the old address
            user.email = profile.pending_new_email
            user.save(update_fields=['email'])
            
            # logger.info(f"User {user.username} successfully changed email from {old_email} to {user.email}.")
            
            profile.clear_email_change_data() # Important: clear sensitive pending data
            
            messages.success(request, _("Your email address has been successfully updated to {new_email}.").format(new_email=user.email))
            # update_session_auth_hash(request, user) # Consider if necessary for your auth setup
            
            context_success = {
                'page_title': _('Email Changed Successfully'),
                'new_email': user.email, # Pass the new email to the template
                'active_section': 'change_email',
            }
            return render(request, self.template_name_success, context_success)
        else:
            # Token check failed (e.g., already used, or internal state of user changed)
            messages.error(request, _("This email change link is invalid or could not be verified. Please try again."))
            profile.clear_email_change_data()
            return render(request, self.template_name_invalid, {'page_title': _('Invalid Link')})


class EmailChangeCompleteView(LoginRequiredMixin, View):
    """
    Displays a page confirming that the email address has been successfully changed.
    Note: EmailChangeConfirmView can also render this success state directly.
    """
    template_name = 'user_profile/change_email_complete.html'

    def get(self, request, *args, **kwargs):
        context = {
            'page_title': _('Email Address Changed'),
            'active_section': 'change_email', # For sidebar consistency
            'new_email': request.user.email # Display the user's (now current) email
        }
        return render(request, self.template_name, context)


class EmailChangeInvalidView(LoginRequiredMixin, View):
    """
    Displays a page indicating that the email change verification link was invalid or expired.
    Note: EmailChangeConfirmView can also render this invalid state directly.
    """
    template_name = 'user_profile/change_email_invalid.html'

    def get(self, request, *args, **kwargs):
        context = {
            'page_title': _('Invalid Email Change Link'),
            'active_section': 'change_email',
        }
        return render(request, self.template_name, context)