# journal/urls.py

from django.urls import path
from . import views # Import views from the current app

app_name = 'journal' # Define app namespace

urlpatterns = [
    # URL for the list of journal entries (e.g., /journal/)
    path('', views.JournalEntryListView.as_view(), name='journal_list'),

    # URL for creating a new journal entry (e.g., /journal/new/)
    path('new/', views.JournalEntryCreateView.as_view(), name='journal_create'),

    # URL for viewing the details of a single journal entry (e.g., /journal/123/)
    # <int:pk> captures the primary key from the URL and passes it to the view
    path('<int:pk>/', views.JournalEntryDetailView.as_view(), name='journal_detail'),

    # URL for editing an existing journal entry (e.g., /journal/123/edit/)
    path('<int:pk>/edit/', views.JournalEntryUpdateView.as_view(), name='journal_update'),

    # URL for deleting an existing journal entry (e.g., /journal/123/delete/)
    path('<int:pk>/delete/', views.JournalEntryDeleteView.as_view(), name='journal_delete'),

    # TODO: Add URLs for file uploads/deletions related to entries later.
    # TODO: Add URLs for AI processing status/results later.
    # TODO: Add URLs for favoriting/unfavoriting later.
]
