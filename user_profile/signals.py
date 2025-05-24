from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.apps import apps # Import the apps module

# settings.AUTH_USER_MODEL refers to your 'accounts.CustomUser'
User = settings.AUTH_USER_MODEL 

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to create or update the user profile automatically
    whenever a User instance is saved.
    """
    # Get the UserProfile model dynamically only when the signal is handled
    UserProfile = apps.get_model('user_profile', 'UserProfile')

    if created:
        UserProfile.objects.create(user=instance)
        print(f"UserProfile created for new user: {instance.username}")
    else:
        # For existing users, ensure their profile exists or update it if necessary
        # Using get_or_create is a robust way to handle this.
        profile, profile_created = UserProfile.objects.get_or_create(user=instance)
        if profile_created:
            print(f"UserProfile created for existing user (was missing): {instance.username}")
        else:
            # If the profile already existed, you might want to save it to update 'updated_at'
            # or perform other logic. For now, just ensuring it exists is often enough.
            # profile.save() # Uncomment if you want to force a save on every user update
            pass # Or print(f"UserProfile for existing user {instance.username} already exists.")
