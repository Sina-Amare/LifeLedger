# ai_services/urls.py

from django.urls import path
from . import views

app_name = 'ai_services'

urlpatterns = [
    # Main dashboard page where users can view their sentiment trends and generate insights.
    path('insights/', views.AIInsightsDashboardView.as_view(), name='ai_insights_dashboard'),

    # API endpoint to fetch updated sentiment data for the chart via AJAX.
    path('insights/sentiment-chart-data/', views.SentimentChartDataView.as_view(), name='sentiment_chart_data_ajax'),

    # API endpoint to begin the analysis for generating collective insights.
    path('insights/start-analysis/', views.StartInsightsAnalysisView.as_view(), name='start_insights_analysis'),
    
    # API endpoint to poll for the results of the insights analysis task.
    path('insights/get-result/', views.GetInsightsResultView.as_view(), name='get_insights_result'),

    # API endpoint to start generating life suggestions based on previously generated insights.
    path('suggestions/start-analysis/', views.StartSuggestionsAnalysisView.as_view(), name='start_suggestions_analysis'),

    # API endpoint to poll for the results of the life suggestions task.
    path('suggestions/get-result/', views.GetSuggestionsResultView.as_view(), name='get_suggestions_result'),
]
