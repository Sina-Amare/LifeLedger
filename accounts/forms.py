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
        # Get the username/email and password from cleaned_data
        username_or_email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        # --- Step 1: Find the user by username or email (case-insensitive) ---
        # Do this BEFORE calling super().clean() to check active status first.
        user = None
        if username_or_email:
            try:
                user = User.objects.get(
                    Q(username__iexact=username_or_email) | Q(email__iexact=username_or_email)
                )
                print(f"UsernameEmailAuthenticationForm: User '{user.username}' found during clean.") # Debug print
            except User.DoesNotExist:
                print(f"UsernameEmailAuthenticationForm: User with username/email '{username_or_email}' not found during clean.") # Debug print
                # User not found. Let the parent's clean handle the generic error.
                pass # Keep user as None

        # --- Step 2: Check if the user is inactive ---
        if user is not None and not user.is_active:
            # If user is found and is inactive, add a specific non-field error.
            # This error will be displayed to the user.
            print(f"UsernameEmailAuthenticationForm: User '{user.username}' is inactive.") # Debug print
            self.add_error(
                None, # None indicates a non-field error
                ValidationError(
                    "Your account is not active. Please check your email for the activation link or use the 'Resend Activation Email' option.",
                    code='inactive',
                )
            )
            # IMPORTANT: If we add a specific error for inactive user,
            # we should NOT proceed with the parent's clean method
            # as it will add a conflicting generic error.
            # We can return the cleaned_data here with the error added.
            # The form will be invalid due to the added error.
            return self.cleaned_data # Return early with error

        # --- Step 3: If user is active or not found, proceed with standard authentication ---
        # Call the parent's clean method to perform the actual authentication
        # using the configured backends (including UsernameEmailBackend).
        # This will check the password and set self.user if authentication is successful
        # for an ACTIVE user. If authentication fails (e.g., wrong password),
        # the parent's clean method will add standard non-field errors.
        print("UsernameEmailAuthenticationForm: Calling super().clean() for authentication.") # Debug print
        return super().clean() # Proceed with standard authentication check


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

            self.user = user # Attach the user object to the form
            return value

        raise ValidationError("Please enter your username or email address.")
