from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
import user_profile.signals # noqa: F401 (to prevent unused import linter error if signals are only receivers)
class UserProfileConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_profile'
    verbose_name = _("User Profile")

    def ready(self):
        """
        This method is called when Django fully loads this application.
        It's the recommended place to import and connect signals.
        """
        # Import signals from user_profile.signals module
        
        print("UserProfile signals connected.") # Optional: for confirmation during development
