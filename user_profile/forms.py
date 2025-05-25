from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm # For setting the new password
from django.utils.translation import gettext_lazy as _
from .models import UserProfile

User = get_user_model() # This gets your accounts.CustomUser model

class UserUpdateForm(forms.ModelForm):
    """
    Form for updating core user information like first name and last name.
    Email and username changes are typically handled separately due to their sensitivity
    and potential need for verification or uniqueness checks beyond simple updates.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name'] # Add 'email' here if you want to allow direct editing without re-verification for now

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add placeholders or classes if needed for styling
        self.fields['first_name'].widget.attrs.update({'placeholder': 'Enter your first name'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Enter your last name'})
        # if 'email' in self.fields:
        #     self.fields['email'].widget.attrs.update({'placeholder': 'Enter your email address'})


class UserProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile specific information.
    """
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture', 'bio', 'location', 'date_of_birth', 
            'website_url', 'linkedin_url', 'github_url',
            'show_email_publicly', 'show_location_publicly', 
            'show_socials_publicly', 'show_dob_publicly',
            'ai_enable_quotes', 'ai_enable_mood_detection', 'ai_enable_tag_suggestion'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell us a little about yourself...'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'profile-input flatpickr-input'}), # Added profile-input for consistent styling
            'location': forms.TextInput(attrs={'placeholder': 'e.g., Tehran, Iran'}),
            'website_url': forms.URLInput(attrs={'placeholder': 'https://your-website.com'}),
            'linkedin_url': forms.URLInput(attrs={'placeholder': 'https://linkedin.com/in/yourprofile'}),
            'github_url': forms.URLInput(attrs={'placeholder': 'https://github.com/yourusername'}),
        }
        help_texts = { # Example of custom help texts if model help_texts are not enough
            'profile_picture': ('Upload a new profile picture. Current picture will be replaced. '
                                'Leave blank to keep the current picture or remove it below.'),
            'show_email_publicly': ('If checked, your email address will be visible on your public profile page.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply 'profile-input' class to all fields for consistent styling,
        # except for checkboxes and the profile picture (which gets special handling in template).
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput) and field_name != 'profile_picture':
                current_class = field.widget.attrs.get('class', '')
                # Ensure 'profile-input' is added without duplicating it
                if 'profile-input' not in current_class:
                    field.widget.attrs['class'] = f'{current_class} profile-input'.strip()
            if field_name == 'date_of_birth': # Ensure flatpickr-input is also there
                if 'flatpickr-input' not in field.widget.attrs.get('class', ''):
                     field.widget.attrs['class'] = f"{field.widget.attrs.get('class', '')} flatpickr-input".strip()


        if self.instance and self.instance.pk and self.instance.profile_picture:
            self.fields['profile_picture'].required = False

    def clean_profile_picture(self):
        """
        Custom validation for the profile picture if needed.
        For example, checking file size or type (though Django's ImageField handles basic type checks).
        """
        picture = self.cleaned_data.get('profile_picture', False)
        if picture:
            # Example: Check file size (e.g., max 2MB)
            # if picture.size > 2 * 1024 * 1024:
            #     raise forms.ValidationError("Image file too large ( > 2MB )")
            pass # Add more validation if needed
        return picture

# --- Added Password Change Forms ---

class CurrentPasswordConfirmForm(forms.Form):
    """
    Form to confirm the user's current password.
    """
    current_password = forms.CharField(
        label=_("Current Password"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'class': 'profile-input'}), # Using your .profile-input class
        strip=False, # Do not strip whitespace, as passwords can have it
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None) # Expect a 'user' instance to be passed
        super().__init__(*args, **kwargs)
        if not self.user:
            # This form should only be instantiated with a user.
            # Raising an error here helps catch incorrect usage during development.
            raise ValueError("CurrentPasswordConfirmForm requires a 'user' argument to be passed during instantiation.")

    def clean_current_password(self):
        """
        Validates that the entered password matches the user's current password.
        """
        current_password = self.cleaned_data.get("current_password")
        # self.user should be set in __init__
        if not self.user.check_password(current_password):
            raise forms.ValidationError(
                _("Your current password was entered incorrectly. Please enter it again."),
                code='password_mismatch', # Standard error code
            )
        return current_password

class NewPasswordSetForm(SetPasswordForm):
    """
    A form that lets a user set their new password.
    Inherits from Django's SetPasswordForm, which handles validation
    for new_password1 and new_password2 (e.g., matching, complexity).
    We customize widget attributes here for consistent styling.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply consistent styling to password fields
        self.fields['new_password1'].widget.attrs.update({
            'class': 'profile-input', 
            'autocomplete': 'new-password',
            'placeholder': _('Enter new password')
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'profile-input', 
            'autocomplete': 'new-password',
            'placeholder': _('Confirm new password')
        })
        # Remove default Django help text for new_password1, as we might use an info button.
        self.fields['new_password1'].help_text = None
