import uuid # Not strictly needed in this file anymore after UserProfile removal, but harmless
from django.contrib.auth.models import AbstractUser
from django.db import models
# Removed: from django.conf import settings # No longer needed here
# Removed: UserProfile model definition

class CustomUser(AbstractUser):
    """
    Custom User model inheriting from AbstractUser.
    This model is set as the AUTH_USER_MODEL in settings.
    It includes standard Django user fields and allows for future extensions
    if needed directly on the user model (though extending via a separate
    profile model like user_profile.UserProfile is often preferred for non-auth data).
    """
    # The 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active',
    # 'is_superuser', 'last_login', 'date_joined' fields are inherited from AbstractUser.

    # Custom related_name for groups and user_permissions to avoid clashes
    # when replacing the default user model. This is a best practice.
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text=(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="customuser_set", # Ensures no clash with auth.User's reverse accessor
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="customuser_set", # Ensures no clash with auth.User's reverse accessor
        related_query_name="customuser",
    )

    # You could add additional fields directly here if they are core to authentication
    # or very tightly coupled with the user identity. For example:
    # email_verified = models.BooleanField(default=False)
    # phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        """
        Returns the username as the string representation of the user.
        """
        return self.username
        # Alternatively, you could use email or a combination:
        # return self.email or self.username

# Note: The old UserProfile model that was previously in this file has been removed.
# All profile-related information (including activation_key, bio, profile_picture, etc.)
# is now handled by the 'user_profile.UserProfile' model.
