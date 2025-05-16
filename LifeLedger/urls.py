# LifeLedger/urls.py

from django.contrib import admin
from django.urls import path, include # Import include
from django.conf import settings # Import settings
from django.conf.urls.static import static # Import static helper function


urlpatterns = [
    path('admin/', admin.site.urls),
    # Include the accounts app URLs under the 'accounts/' path
    path('accounts/', include('accounts.urls')),
    # Include the journal app URLs under the 'journal/' path (assuming you have one)
    # path('journal/', include('journal.urls')), # Uncomment if you have a journal app
    # Root URL for the project (handled by accounts.urls.home)
    path('', include('accounts.urls')), # Include accounts urls at the root for the homepage
    path('journal/', include('journal.urls'))
]

# Serve media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

