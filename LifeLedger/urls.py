# LifeLedger/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import HomeView

urlpatterns = [
    path('admin/', admin.site.urls),

    # App-specific URL includes
    path('accounts/', include('accounts.urls')),
    path('journal/', include('journal.urls')),
    path('profile/', include('user_profile.urls')),

    # New include for our refactored AI services app
    path('ai/', include('ai_services.urls')),
    
    # Root URL for the project homepage
    path('', HomeView.as_view(), name='site_home'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
