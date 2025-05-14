# accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError
from django.db.models import Q

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """
    Custom form for user registration.
    Adds the 'email' field, ensures it is required, and validates uniqueness.
    Provides a specific error message if the email is already in use by an inactive user.
    """
    email = forms.EmailField(required=True, label="Email Address")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def clean_email(self):
        """
        Validates that the email address is unique.
        Provides a specific error message if the email is already in use by an inactive user.
        """
        email = self.cleaned_data.get('email')
        if email:
            # Check if a user with this email already exists (case-insensitive)
            try:
                user = User.objects.get(email__iexact=email)
                # If a user is found, check if they are active
                if user.is_active:
                    # If active, show the standard "already in use" message
                    raise ValidationError("This email address is already in use.")
                else:
                    # If inactive, show a specific message guiding them to resend
                    raise ValidationError(
                        "An account with this email already exists but is not active. "
                        "Please use the 'Resend Activation Email' option if you haven't received the activation link."
                    )
            except User.DoesNotExist:
                # If no user with this email exists, it's available
                pass # Email is unique and available

        return email


class UsernameEmailAuthenticationForm(AuthenticationForm):
    """
    Custom form for user login that allows authentication using either
    username or email address.
    Provides a specific error message if the user is inactive.
    """
    username = forms.CharField(label="Username or Email")

    def clean(self):
        """
        Cleans the form data and validates credentials.
        Provides a specific error message if the user is inactive.
        """
        # --- Step 1: Call the parent's clean method first ---
        # This performs the basic validation and attempts authentication
        # using the configured backends. If successful and user is active,
        # it sets self.user. If not, it adds standard non-field errors.
        super().clean()
        # Now self.cleaned_data is populated and self.user might be set


        # --- Step 2: Check if authentication was successful AND the user is inactive ---
        # self.user will be set by the parent's clean method ONLY if authentication
        # was successful AND the user is active (due to the check in UsernameEmailBackend).
        # However, we need to find the user regardless of active status to provide
        # a specific message if they are inactive.

        # Get the username/email entered by the user from cleaned_data
        username_or_email = self.cleaned_data.get('username')

        if username_or_email:
            try:
                # Find the user by username or email (case-insensitive), regardless of active status
                user = User.objects.get(
                    Q(username__iexact=username_or_email) | Q(email__iexact=username_or_email)
                )

                # If the user is found BUT is inactive, add a specific non-field error.
                # This error will override or appear alongside the parent's generic error
                # if the parent's clean method failed because the user was inactive.
                if not user.is_active:
                    # Use add_error to add a non-field error
                    self.add_error(
                        None, # None indicates a non-field error
                        ValidationError(
                            "Your account is not active. Please check your email for the activation link or use the 'Resend Activation Email' option.",
                            code='inactive',
                        )
                    )
                    # IMPORTANT: If we add a specific error for inactive user,
                    # we should clear the generic error added by the parent if it exists,
                    # to avoid showing two conflicting messages.
                    # However, directly manipulating self._errors can be tricky.
                    # A simpler approach is to ensure our specific message is clear
                    # and the user understands it. The parent's error might still show,
                    # but our specific one should be more prominent/helpful.
                    # Let's rely on the specific message being clear enough for now.


            except User.DoesNotExist:
                # User not found. The parent's clean method already handled this
                # by adding a standard invalid login error. No need to do anything here.
                pass


        # --- Step 3: Return the cleaned data ---
        # Any errors (from parent or our inactive check) are now collected in self.errors
        return self.cleaned_data


class ResendActivationEmailForm(forms.Form):
    """
    Form for requesting a new account activation email.
    Accepts either username or email address.
    """
    username_or_email = forms.CharField(
        label="Username or Email Address",
        max_length=254,
        widget=forms.TextInput(attrs={'autofocus': True})
    )

    def clean_username_or_email(self):
        """
        Validates that a user with the provided username or email exists
        and is currently inactive.
        """
        value = self.cleaned_data.get('username_or_email')
        if value:
            try:
                user = User.objects.get(
                    Q(username__iexact=value) | Q(email__iexact=value)
                )
            except User.DoesNotExist:
                raise ValidationError(
                    "No user found with this username or email address."
                )

            if user.is_active:
                raise ValidationError(
                    "This account is already active. Please try logging in."
                )

            self.user = user
            return value

        raise ValidationError("Please enter your username or email address.")

