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
    
    # URL for polling individual AI task status (quote, mood, tags)
    path('entry/<int:entry_id>/ai-status/', views.AIServiceStatusView.as_view(), name='ai_service_status'),

    # URL for the AI Insights Dashboard page
    path('insights/', views.AIInsightsDashboardView.as_view(), name='ai_insights_dashboard'),

    # URL for fetching sentiment chart data via AJAX
    path('insights/sentiment-chart-data/', views.SentimentChartDataView.as_view(), name='sentiment_chart_data_ajax'),

    # --- NEW URLS FOR COLLECTIVE INSIGHTS ---
    # URL to start the collective insights analysis task (expects POST)
    path('insights/start-analysis/', views.StartInsightsAnalysisView.as_view(), name='start_insights_analysis'),
    
    # URL to poll for and retrieve the results of the insights analysis task (expects GET with task_id)
    path('insights/get-result/', views.GetInsightsResultView.as_view(), name='get_insights_result'),
]
