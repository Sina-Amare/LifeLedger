# LifeLedger/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # This line includes the accounts app's urls at the root level.
    # The empty path '' in accounts/urls.py will match the root URL '/'.
    path('', include('accounts.urls')),
]