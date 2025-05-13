# accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

class CustomUserCreationForm(UserCreationForm):
    """
    Custom form for user registration.
    Inherits from Django's built-in UserCreationForm to handle user creation
    and password hashing securely.
    Adds the 'email' field to the default signup form.
    """
    class Meta(UserCreationForm.Meta):
        model = UserCreationForm.Meta.model
        fields = UserCreationForm.Meta.fields + ('email',)