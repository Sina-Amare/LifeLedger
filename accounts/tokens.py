# accounts/tokens.py

from django.contrib.auth.tokens import PasswordResetTokenGenerator
# Removed import six - not needed in Python 3
from django.contrib.auth import get_user_model

# Get the user model
User = get_user_model()

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Custom token generator for account activation.
    Inherits from PasswordResetTokenGenerator but uses different data
    to generate the hash, ensuring tokens for activation and password reset
    are distinct and cannot be used interchangeably.
    """
    def _make_hash_value(self, user, timestamp):
        """
        Generates a hash value based on user's primary key, activation status,
        and timestamp. This hash is part of the token.
        """
        # Use str() directly instead of six.text_type() in Python 3
        return (
            str(user.pk) + str(timestamp) +
            str(user.is_active) # Include is_active status
        )

# Instantiate the token generator
account_activation_token = AccountActivationTokenGenerator()
