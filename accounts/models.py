# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid # Import uuid for generating unique keys
# Removed: from django.contrib.auth import get_user_model # This should not be called here
# Removed: User = get_user_model() # Do not call get_user_model() here
# Removed: from django.conf import settings # Not needed if using direct string reference 'accounts.CustomUser'

class CustomUser(AbstractUser):
    # Add any additional fields you want for your user model here.
    # For example, a profile picture, bio, etc.
    # profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    # bio = models.TextField(max_length=500, blank=True)

    # Add custom related_name to avoid clashes with auth.User
    # These are standard practice when replacing the default user model
    # to prevent potential clashes with reverse relationships from auth models.
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="customuser_set", # Custom related_name
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="customuser_set", # Custom related_name
        related_query_name="customuser",
    )


    def __str__(self):
        # Use email as string representation if username is not preferred
        # return self.email or self.username
        return self.username # Or self.email, depending on which field you use for login/display


class UserProfile(models.Model):
    """
    Extends the custom User model to store additional information,
    like the email activation key.
    Uses a One-to-One relationship with the custom User model.
    """
    # Use the direct string reference to the custom user model
    # This is the correct way to reference the AUTH_USER_MODEL
    # in model definitions, especially within the same app.
    user = models.OneToOneField(
        'accounts.CustomUser', # Use direct string reference here
        on_delete=models.CASCADE,
        related_name='profile'
    )
    # activation_key can be null and blank after activation
    activation_key = models.CharField(max_length=64, blank=True, null=True, unique=True)
    # You can add other profile-related fields here in the future

    def __str__(self):
        """String representation of the UserProfile."""
        return f'Profile for {self.user.username}'

    def generate_activation_key(self):
        """
        Generates a unique activation key using UUID.
        """
        self.activation_key = str(uuid.uuid4())
        self.save() # Save the key to the database

    def activate_user(self):
        """
        Activates the user account and clears the activation key.
        """
        user = self.user
        user.is_active = True
        user.save()
        self.activation_key = None # Clear the key after activation
        self.save()

# Note: Do NOT call get_user_model() in this file.
# AUTH_USER_MODEL setting in settings.py tells Django to use CustomUser.
# Other models should refer to the user model using the string reference 'app_label.ModelName'.
