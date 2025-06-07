# ai_services/views.py

from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from collections import Counter
import datetime
import json
import logging

from celery.result import AsyncResult
from .tasks import generate_insights_for_period_task, generate_life_suggestions_task

from journal.models import JournalEntry
from journal.constants import MOOD_CHOICES
from journal.utils import MOOD_VISUALS, CHART_JS_COLOR_PALETTE
from journal.forms import MOOD_CHOICES_FORM_DISPLAY

logger = logging.getLogger(__name__)


def _get_sentiment_data_for_period(user, time_period_value):
    """
    Fetches and processes sentiment data for a given user and time period.

    This helper queries the user's journal entries within a specified
    timeframe, counts mood occurrences, and formats the data for Chart.js.
    """
    end_date = timezone.now()
    start_date = None
    
    valid_periods = ['last_7_days', 'last_30_days', 'last_90_days', 'last_365_days', 'all_time']
    if time_period_value not in valid_periods:
        time_period_value = 'last_30_days'

    if time_period_value == 'last_7_days':
        start_date = end_date - datetime.timedelta(days=6)
    elif time_period_value == 'last_30_days':
        start_date = end_date - datetime.timedelta(days=29)
    elif time_period_value == 'last_90_days':
        start_date = end_date - datetime.timedelta(days=89)
    elif time_period_value == 'last_365_days':
        start_date = end_date - datetime.timedelta(days=364)

    entries_query = JournalEntry.objects.filter(user=user)
    if start_date:
        start_of_day = timezone.make_aware(datetime.datetime.combine(start_date.date(), datetime.time.min))
        end_of_day = timezone.make_aware(datetime.datetime.combine(end_date.date(), datetime.time.max))
        entries_for_period = entries_query.filter(created_at__gte=start_of_day, created_at__lte=end_of_day)
    else: 
        entries_for_period = entries_query.all()
    
    mood_counts = Counter(entry.mood for entry in entries_for_period.only('mood') if entry.mood)
    mood_display_names_dict = {key: str(name) for key, name in MOOD_CHOICES}
    
    chart_labels, chart_data_values, chart_background_colors, chart_border_colors = [], [], [], []

    for mood_value, count in mood_counts.items():
        visual_details = MOOD_VISUALS.get(mood_value)
        if not visual_details: continue
        
        emoji = visual_details.get('emoji', '')
        display_name = mood_display_names_dict.get(mood_value, mood_value.capitalize())
        
        chart_labels.append(f"{emoji} {display_name}".strip())
        chart_data_values.append(count)
        
        chart_mood_colors = CHART_JS_COLOR_PALETTE.get(mood_value, CHART_JS_COLOR_PALETTE['default'])
        chart_background_colors.append(chart_mood_colors['bg'])
        chart_border_colors.append(chart_mood_colors['border'])

    return {
        'labels': chart_labels,
        'datasets': [{'label': str(_('Mood Occurrences')), 'data': chart_data_values, 'backgroundColor': chart_background_colors, 'borderColor': chart_border_colors, 'borderWidth': 1, 'borderRadius': 5, 'hoverBorderWidth': 2, 'hoverBorderColor': '#333'}],
        'has_data': bool(chart_data_values)
    }

class AIInsightsDashboardView(LoginRequiredMixin, TemplateView):
    """Renders the main AI Insights dashboard page."""
    template_name = 'ai_services/ai_insights_dashboard.html'

    def get_context_data(self, **kwargs):
        """Prepares the initial context for the dashboard."""
        context = super().get_context_data(**kwargs)
        request = self.request
        
        context['time_period_options'] = [
            {'value': 'last_7_days', 'label': str(_('Last 7 Days'))},
            {'value': 'last_30_days', 'label': str(_('Last 30 Days'))},
            {'value': 'last_90_days', 'label': str(_('Last 90 Days'))},
            {'value': 'last_365_days', 'label': str(_('Last Year'))},
            {'value': 'all_time', 'label': str(_('All Time'))},
        ]
        
        selected_period = request.GET.get('time_period', 'last_30_days')
        context['selected_period'] = selected_period
        
        initial_chart_data = _get_sentiment_data_for_period(request.user, selected_period)
        context['sentiment_chart_data_json'] = json.dumps(initial_chart_data)
        context['has_sentiment_data'] = initial_chart_data.get('has_data', False)
        
        logger.info(f"AIInsightsDashboardView loaded for user {request.user.username}, period: {selected_period}")
        return context

class SentimentChartDataView(LoginRequiredMixin, View):
    """Provides JSON data for the sentiment chart, intended for AJAX updates."""
    def get(self, request, *args, **kwargs):
        chart_data = _get_sentiment_data_for_period(request.user, request.GET.get('time_period', 'last_30_days'))
        return JsonResponse(chart_data)

class StartInsightsAnalysisView(LoginRequiredMixin, View):
    """Starts the Celery task for generating collective insights."""
    def post(self, request, *args, **kwargs):
        time_period = request.POST.get('time_period')
        if not time_period:
            return JsonResponse({'status': 'error', 'message': 'Time period is required.'}, status=400)
        task = generate_insights_for_period_task.delay(request.user.id, time_period)
        return JsonResponse({'status': 'processing', 'task_id': task.id})

class GetInsightsResultView(LoginRequiredMixin, View):
    """Polls for the result of the collective insights Celery task."""
    def get(self, request, *args, **kwargs):
        task_id = request.GET.get('task_id')
        if not task_id:
            return JsonResponse({'status': 'error', 'message': 'Task ID is required.'}, status=400)

        task_result = AsyncResult(task_id)
        if task_result.ready():
            if task_result.successful():
                result = task_result.get()
                result['status'] = 'SUCCESS'
                return JsonResponse(result)
            else:
                logger.error(f"Task {task_id} for insights failed: {task_result.info}")
                return JsonResponse({'status': 'FAILURE', 'message': 'Analysis failed.'})
        else:
            return JsonResponse({'status': task_result.state})

class StartSuggestionsAnalysisView(LoginRequiredMixin, View):
    """Starts the Celery task for generating life suggestions."""
    def post(self, request, *args, **kwargs):
        try:
            insights_data = json.loads(request.body)
            if not isinstance(insights_data, dict):
                raise json.JSONDecodeError
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload.'}, status=400)

        task = generate_life_suggestions_task.delay(request.user.id, insights_data)
        return JsonResponse({'status': 'processing', 'task_id': task.id})

class GetSuggestionsResultView(LoginRequiredMixin, View):
    """Polls for the result of the life suggestions Celery task."""
    def get(self, request, *args, **kwargs):
        task_id = request.GET.get('task_id')
        if not task_id:
            return JsonResponse({'status': 'error', 'message': 'Task ID is required.'}, status=400)

        task_result = AsyncResult(task_id)
        if task_result.ready():
            if task_result.successful():
                result = task_result.get()
                result['status'] = 'SUCCESS'
                return JsonResponse(result) # The result is already a dict {'suggestions': [...]}
            else:
                logger.error(f"Suggestions Task {task_id} failed: {task_result.info}")
                return JsonResponse({'status': 'FAILURE', 'message': 'Suggestion generation failed.'})
        else:
            return JsonResponse({'status': task_result.state})
