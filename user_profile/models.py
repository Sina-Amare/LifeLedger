import uuid
from django.db import models
from django.conf import settings # To get AUTH_USER_MODEL
from django.utils.translation import gettext_lazy as _ # For verbose names
from django.utils import timezone # Needed for default timestamp, or set in view

def user_profile_picture_path(instance, filename):
    """
    Generates a unique path for user profile pictures.
    Example: user_{id}/profile_pictures/{filename_with_uuid_extension}
    """
    ext = filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    return f'user_{instance.user.id}/profile_pictures/{unique_filename}'

class UserProfile(models.Model):
    """
    Stores extended information for a user, including profile details,
    activation key, AI preferences, and fields for email change process.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_("User")
    )
    activation_key = models.CharField(
        _("Activation Key"),
        max_length=64,
        blank=True,
        null=True,
        unique=True, # Ensure this is okay if old keys might be None before being set
        help_text=_("Key used for account activation. Cleared after activation.")
    )
    profile_picture = models.ImageField(
        _("Profile Picture"),
        upload_to=user_profile_picture_path,
        blank=True,
        null=True,
        help_text=_("User's profile picture.")
    )
    bio = models.TextField(
        _("Biography"),
        max_length=1000,
        blank=True,
        null=True,
        help_text=_("A short biography or about me section for the user.")
    )
    location = models.CharField(
        _("Location"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("User's general location (e.g., City, Country).")
    )
    date_of_birth = models.DateField(
        _("Date of Birth"),
        blank=True,
        null=True,
        help_text=_("User's date of birth. Handle with privacy in mind.")
    )
    website_url = models.URLField(
        _("Website URL"),
        blank=True,
        null=True,
        help_text=_("User's personal or professional website.")
    )
    linkedin_url = models.URLField(
        _("LinkedIn Profile URL"),
        blank=True,
        null=True,
        help_text=_("Link to the user's LinkedIn profile.")
    )
    github_url = models.URLField(
        _("GitHub Profile URL"),
        blank=True,
        null=True,
        help_text=_("Link to the user's GitHub profile.")
    )

    # --- Privacy Settings ---
    show_email_publicly = models.BooleanField(
        _("Show Email Publicly"),
        default=False,
        help_text=_("If checked, the user's email (from CustomUser) will be visible on their public profile.")
    )
    show_location_publicly = models.BooleanField(
        _("Show Location Publicly"),
        default=False,
        help_text=_("If checked, the user's location will be visible on their public profile.")
    )
    show_socials_publicly = models.BooleanField(
        _("Show Social Links Publicly"),
        default=False,
        help_text=_("If checked, website, LinkedIn, and GitHub links will be visible on their public profile.")
    )
    show_dob_publicly = models.BooleanField(
        _("Show Date of Birth Publicly"),
        default=False,
        help_text=_("If checked, the user's date of birth will be visible on their public profile.")
    )

    # --- AI Preferences ---
    ai_enable_quotes = models.BooleanField(
        _("Enable AI Quote Generation"),
        default=True,
        help_text=_("Allow AI to generate quotes for journal entries.")
    )
    ai_enable_mood_detection = models.BooleanField(
        _("Enable AI Mood Detection"),
        default=True,
        help_text=_("Allow AI to detect mood from journal entries.")
    )
    ai_enable_tag_suggestion = models.BooleanField(
        _("Enable AI Tag Suggestion"),
        default=True,
        help_text=_("Allow AI to suggest tags for journal entries.")
    )

    # --- Fields for Email Change Process ---
    # NEW FIELD
    pending_new_email = models.EmailField(
        _("Pending New Email"),
        max_length=254, # Standard max length for emails
        blank=True,
        null=True,
        help_text=_("Stores a new email address awaiting verification after a change request.")
    )
    # NEW FIELD
    email_change_token_key = models.CharField(
        _("Email Change Token Key"),
        max_length=64, # Similar to activation_key
        blank=True,
        null=True,
        help_text=_("Token key sent to the pending new email for verification.")
    )
    # NEW FIELD
    email_change_token_key_created_at = models.DateTimeField(
        _("Email Change Token Key Created At"),
        blank=True,
        null=True,
        help_text=_("Timestamp for when the email change token key was generated.")
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(_("Profile Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Profile Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        ordering = ['user__username']

    def __str__(self):
        return f"Profile for {self.user.username}"

    def generate_activation_key_value(self):
        """
        Generates a unique activation key value using UUID.
        This method *returns* the key value. It does NOT save the instance.
        The calling code (e.g., a view) is responsible for setting this key
        on the 'activation_key' field and then saving the profile instance.
        """
        return str(uuid.uuid4())

    def activate_user_account(self):
        """
        Activates the associated user account (sets user.is_active=True)
        and clears the activation_key on this profile instance.
        This method saves both the user and this profile instance.
        """
        if self.user:
            self.user.is_active = True
            self.user.save(update_fields=['is_active']) # Be specific about what's saved
        self.activation_key = None
        self.save(update_fields=['activation_key', 'updated_at'])

    # NEW METHOD (Optional, but good practice)
    def clear_email_change_data(self):
        """
        Clears the pending email and token data after a successful change
        or if the process is cancelled/expires.
        Saves the profile instance.
        """
        self.pending_new_email = None
        self.email_change_token_key = None
        self.email_change_token_key_created_at = None
        self.save(update_fields=[
            'pending_new_email',
            'email_change_token_key',
            'email_change_token_key_created_at',
            'updated_at'
        ])