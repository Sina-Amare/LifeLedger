# accounts/models.py

from django.db import models
from django.contrib.auth import get_user_model
import uuid # Import uuid for generating unique keys

# Get the currently active user model
User = get_user_model()

class UserProfile(models.Model):
    """
    Extends the default User model to store additional information,
    like the email activation key.
    Uses a One-to-One relationship with the User model.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
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

