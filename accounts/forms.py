# accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """
    Custom form for user registration.
    Adds the 'email' field, ensures it is required, and validates uniqueness.
    """
    email = forms.EmailField(required=True, label="Email Address")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def clean_email(self):
        """
        Validates that the email address is unique.
        """
        email = self.cleaned_data.get('email')
        if email:
            # Check if a user with this email already exists (case-insensitive)
            if User.objects.filter(email__iexact=email).exists():
                # Raise a validation error if email is not unique
                raise ValidationError("This email address is already in use.")
        return email


class UsernameEmailAuthenticationForm(AuthenticationForm):
    """
    Custom form for user login that allows authentication using either
    username or email address.
    """
    username = forms.CharField(label="Username or Email")

    def clean(self):
        """
        Cleans the form data. Does not perform authentication itself,
        which is handled by the authentication backend.
        """
        super().clean()
        return self.cleaned_data
