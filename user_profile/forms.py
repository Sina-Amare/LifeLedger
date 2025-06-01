# user_profile/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.utils.translation import gettext_lazy as _
from .models import UserProfile

User = get_user_model()

class UserUpdateForm(forms.ModelForm):
    """
    Form for updating core user information like first name and last name.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs.update({
            'placeholder': _('Enter your first name'),
            'class': 'profile-input'
        })
        self.fields['last_name'].widget.attrs.update({
            'placeholder': _('Enter your last name'),
            'class': 'profile-input'
        })

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
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': _('Tell us a little about yourself...'), 'class': 'profile-textarea'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'text', 'class': 'profile-input flatpickr-input', 'placeholder': _('YYYY-MM-DD')}),
            'location': forms.TextInput(attrs={'placeholder': _('e.g., Tehran, Iran'), 'class': 'profile-input'}),
            'website_url': forms.URLInput(attrs={'placeholder': 'https://your-website.com', 'class': 'profile-input'}),
            'linkedin_url': forms.URLInput(attrs={'placeholder': 'https://linkedin.com/in/yourprofile', 'class': 'profile-input'}),
            'github_url': forms.URLInput(attrs={'placeholder': 'https://github.com/yourusername', 'class': 'profile-input'}),
        }
        help_texts = {
            'profile_picture': _('Upload a new profile picture. Current picture will be replaced. Leave blank to keep the current picture.'),
            'show_email_publicly': _('If checked, your email address will be visible on your public profile page.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Apply base styling class if not already present and not a checkbox/file input
            if not isinstance(field.widget, forms.CheckboxInput) and field_name != 'profile_picture':
                current_class = field.widget.attrs.get('class', '')
                # Determine correct base class
                base_class_to_apply = 'profile-input'
                if isinstance(field.widget, forms.Textarea):
                    base_class_to_apply = 'profile-textarea'

                if base_class_to_apply not in current_class:
                    field.widget.attrs['class'] = f'{current_class} {base_class_to_apply}'.strip()

                # Ensure flatpickr-input is on date_of_birth
                if field_name == 'date_of_birth' and 'flatpickr-input' not in field.widget.attrs.get('class', ''):
                       field.widget.attrs['class'] = f"{field.widget.attrs.get('class', '')} flatpickr-input".strip()

        if self.instance and self.instance.pk and self.instance.profile_picture:
            self.fields['profile_picture'].required = False

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture', False)
        if picture and hasattr(picture, 'content_type'):  # Check if picture is a file object
            # Validate file size (max 2MB)
            max_size = 2 * 1024 * 1024  # 2MB in bytes
            if picture.size > max_size:
                raise forms.ValidationError(
                    _("File size exceeds the maximum limit of 2MB."),
                    code='file_too_large'
                )
            # Validate file type
            allowed_types = ['image/png', 'image/jpeg', 'image/gif']
            if picture.content_type not in allowed_types:
                raise forms.ValidationError(
                    _("Only PNG, JPG, and GIF files are supported."),
                    code='invalid_file_type'
                )
        return picture

class CurrentPasswordConfirmForm(forms.Form):
    """
    Form to confirm the user's current password.
    """
    current_password = forms.CharField(
        label=_("Current Password"),
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'profile-input',
            'placeholder': _('Enter your current password')
        }),
        strip=False,
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        if not self.user:
            raise ValueError("CurrentPasswordConfirmForm requires a 'user' argument to be passed during instantiation.")
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password")
        if self.user and not self.user.check_password(current_password):
            raise forms.ValidationError(
                _("Your current password was entered incorrectly. Please enter it again."),
                code='password_mismatch',
            )
        return current_password

class NewPasswordSetForm(SetPasswordForm):
    """
    A form that lets a user set their new password.
    We customize widget attributes here for consistent styling.
    """
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

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
        # Remove default Django help text for new_password1, as we use an info button in the template.
        self.fields['new_password1'].help_text = None

# --- NEW FORM FOR EMAIL CHANGE ---
class EmailChangeRequestForm(forms.Form):
    """
    Form for requesting an email address change.
    It handles two main steps internally:
    1. Confirming the current password.
    2. Entering the new email address.
    The view and template will manage which part is visible to the user.
    """
    current_password = forms.CharField(
        label=_("Current Password"),
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'profile-input', # Apply consistent styling
            'placeholder': _('Enter your current password to proceed')
        }),
        strip=False,
        required=False # Requirement handled by view logic based on stage
    )
    new_email = forms.EmailField(
        label=_("New Email Address"),
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'class': 'profile-input', # Apply consistent styling
            'placeholder': _('Enter your new email address')
        }),
        required=False # Requirement handled by view logic based on stage
    )

    def __init__(self, *args, **kwargs):
        """
        The form requires the 'request' object to be passed in,
        from which the user can be accessed.
        """
        self.request = kwargs.pop('request', None)
        if not self.request:
            raise ValueError("EmailChangeRequestForm requires a 'request' argument.")
        self.user = self.request.user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        """
        Validates that the provided current password matches the user's actual password.
        This clean method is only triggered if 'current_password' is part of the submitted data.
        """
        current_password = self.cleaned_data.get('current_password')
        # This validation should only run if current_password was submitted.
        # The view will determine if this field was expected at the current stage.
        if current_password: # Only validate if data is provided for this field
            if not self.user.check_password(current_password):
                raise forms.ValidationError(
                    _("Your current password was entered incorrectly. Please try again."),
                    code='incorrect_current_password'
                )
        return current_password

    def clean_new_email(self):
        """
        Validates the new email address.
        Ensures it's different from the current email and not already in use.
        This clean method is only triggered if 'new_email' is part of the submitted data.
        """
        new_email = self.cleaned_data.get('new_email')
        # This validation should only run if new_email was submitted.
        if new_email: # Only validate if data is provided for this field
            if new_email.lower() == self.user.email.lower():
                raise forms.ValidationError(
                    _("The new email address must be different from your current one."),
                    code='email_unchanged'
                )
            # Check if the email is already in use by another active user
            if User.objects.filter(email__iexact=new_email, is_active=True).exclude(pk=self.user.pk).exists():
                raise forms.ValidationError(
                    _("This email address is already in use by another account."),
                    code='email_taken'
                )
        return new_email

    def clean(self):
        """
        Overall form cleaning.
        Can be used if validation depends on multiple fields.
        For now, individual field validations are sufficient.
        """
        cleaned_data = super().clean()
        # If we needed to ensure that EITHER password OR new_email was submitted,
        # or specific combinations, this would be the place.
        # For our staged approach, the view will manage which fields are expected.
        return cleaned_data