# LifeLedger/urls.py

from django.contrib import admin
from django.urls import path, include # Import include

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
