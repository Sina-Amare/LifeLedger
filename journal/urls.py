# journal/urls.py

from django.urls import path
from . import views # Import views from the current app

app_name = 'journal' 

urlpatterns = [
    # Existing URL patterns for journal entries
    path('', views.JournalEntryListView.as_view(), name='journal_list'),
    path('new/', views.JournalEntryCreateView.as_view(), name='journal_create'),
    path('<int:pk>/', views.JournalEntryDetailView.as_view(), name='journal_detail'),
    path('<int:pk>/edit/', views.JournalEntryUpdateView.as_view(), name='journal_update'),
    path('<int:pk>/delete/', views.JournalEntryAjaxDeleteView.as_view(), name='journal_delete'),
    
    # URL for polling AI task status (Celery tasks)
    path('entry/<int:entry_id>/ai-status/', views.AIServiceStatusView.as_view(), name='ai_service_status'),

    # URL for the AI Insights Dashboard page.
    path('insights/', views.AIInsightsDashboardView.as_view(), name='ai_insights_dashboard'),

    # --- NEW URL PATTERN ADDED ---
    # This URL will be called by JavaScript to fetch updated sentiment chart data
    # when the user selects a different time period on the AI Insights Dashboard.
    path('insights/sentiment-chart-data/', views.SentimentChartDataView.as_view(), name='sentiment_chart_data_ajax'),
]
