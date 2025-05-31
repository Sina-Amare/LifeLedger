# journal/urls.py

from django.urls import path
from . import views # Import views from the current app

app_name = 'journal' 

urlpatterns = [
    path('', views.JournalEntryListView.as_view(), name='journal_list'),
    path('new/', views.JournalEntryCreateView.as_view(), name='journal_create'),
    path('<int:pk>/', views.JournalEntryDetailView.as_view(), name='journal_detail'),
    path('<int:pk>/edit/', views.JournalEntryUpdateView.as_view(), name='journal_update'),
    path('<int:pk>/delete/', views.JournalEntryAjaxDeleteView.as_view(), name='journal_delete'),
    
    # New URL for polling AI task status
    path('entry/<int:entry_id>/ai-status/', views.AIServiceStatusView.as_view(), name='ai_service_status'),
]
