# LifeLedger/LifeLedger/urls.py

from django.contrib import admin
from django.urls import path, include 
from django.conf import settings 
from django.conf.urls.static import static 
from accounts.views import HomeView # Import HomeView from your accounts app

urlpatterns = [
    path('admin/', admin.site.urls),

    # Include the accounts app URLs under the 'accounts/' path.
    # The 'accounts' namespace will be taken from accounts.urls' app_name.
    # This is the primary and only include for the 'accounts' app URLs.
    path('accounts/', include('accounts.urls')), 
    
    # Include the journal app URLs under the 'journal/' path.
    # It's good practice to also use a namespace here if journal.urls has an app_name.
    # For example: path('journal/', include('journal.urls', namespace='journal')),
    # Assuming your journal.urls also defines an app_name = 'journal'.
    path('journal/', include('journal.urls')),
    
    # User_profile URL
    path('profile/', include('user_profile.urls')),
    
    # Root URL for the project, directly mapping to HomeView from the accounts app.
    # This avoids including 'accounts.urls' again, which caused the namespace conflict.
    # We give this URL pattern a distinct name, e.g., 'site_home', to avoid clashes
    # if 'home' is also used within the 'accounts' namespace for a different URL (e.g., /accounts/).
    path('', HomeView.as_view(), name='site_home'), 
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
