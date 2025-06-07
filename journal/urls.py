# journal/urls.py

from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    # URL patterns for core journal entry operations (CRUD)
    path('', views.JournalEntryListView.as_view(), name='journal_list'),
    path('new/', views.JournalEntryCreateView.as_view(), name='journal_create'),
    path('<int:pk>/', views.JournalEntryDetailView.as_view(), name='journal_detail'),
    path('<int:pk>/edit/', views.JournalEntryUpdateView.as_view(), name='journal_update'),
    path('<int:pk>/delete/', views.JournalEntryAjaxDeleteView.as_view(), name='journal_delete'),
    
    # URL for polling the status of AI tasks for a *single* entry.
    # This remains in 'journal' as it's tightly coupled with the entry creation/update flow.
    path('entry/<int:entry_id>/ai-status/', views.AIServiceStatusView.as_view(), name='ai_service_status'),
]
