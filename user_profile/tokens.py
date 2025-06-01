# user_profile/tokens.py

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailChangeTokenGenerator(PasswordResetTokenGenerator):
    """
    Custom token generator for email change verification.

    This generator creates a unique token by hashing user's primary key,
    their current email address, the new pending email address, and a timestamp.
    This ensures the token is specific to a particular email change request and
    cannot be reused for other purposes or other email addresses.
    """
    def _make_hash_value(self, user, timestamp):
        """
        Generate a hash value that includes the user's current email and
        the pending new email from their profile.

        Args:
            user (CustomUser): The user instance for whom the token is generated.
            timestamp (int): The server timestamp.

        Returns:
            str: A hash string to be used in the token.
        """
        # Ensure the user has a profile and a pending_new_email attribute.
        # If not, this token generation should ideally not be reached
        
        pending_email = getattr(user.profile, 'pending_new_email', '')
        current_email = getattr(user, 'email', '')

        return (
            str(user.pk) +
            str(timestamp) +
            str(current_email) +
            str(pending_email)
        )

# Create an instance of the token generator for use in views.
email_change_token_generator = EmailChangeTokenGenerator()