# ai_services/views.py

from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.db.models.functions import TruncDay
from django.db.models import Avg, Count
from collections import Counter, defaultdict
import datetime
import json
import logging

from celery.result import AsyncResult
from .tasks import generate_insights_for_period_task, generate_life_suggestions_task

from journal.models import JournalEntry
from journal.constants import MOOD_CHOICES, MOOD_NUMERICAL
# Assuming MOOD_VISUALS is not in utils, or just not needed here anymore for colors.

logger = logging.getLogger(__name__)

def _get_start_end_dates(time_period_value):
    """
    Calculate start and end dates for a given time period identifier.
    """
    end_date = timezone.now()
    start_date = None
    
    valid_periods = ['last_7_days', 'last_30_days', 'last_90_days', 'last_365_days', 'all_time']
    if time_period_value not in valid_periods:
        time_period_value = 'last_30_days'  # Default to 30 days

    if time_period_value == 'last_7_days':
        start_date = end_date - datetime.timedelta(days=6)
    elif time_period_value == 'last_30_days':
        start_date = end_date - datetime.timedelta(days=29)
    elif time_period_value == 'last_90_days':
        start_date = end_date - datetime.timedelta(days=89)
    elif time_period_value == 'last_365_days':
        start_date = end_date - datetime.timedelta(days=364)
    
    return start_date, end_date

def _get_sentiment_data_for_period(user, time_period_value):
    """
    Fetch and process sentiment data for a chart showing mood occurrences.
    This version sends raw mood keys as labels for the frontend to process.
    """
    start_date, end_date = _get_start_end_dates(time_period_value)
    
    entries_query = JournalEntry.objects.filter(user=user)
    if start_date:
        start_of_day = timezone.make_aware(datetime.datetime.combine(start_date.date(), datetime.time.min))
        end_of_day = timezone.make_aware(datetime.datetime.combine(end_date.date(), datetime.time.max))
        entries_for_period = entries_query.filter(created_at__gte=start_of_day, created_at__lte=end_of_day)
    else: 
        entries_for_period = entries_query.all()
    
    mood_counts = Counter(entry.mood for entry in entries_for_period.only('mood') if entry.mood)
    
    # Sort moods based on the order in MOOD_CHOICES for consistency
    mood_order = [mood[0] for mood in MOOD_CHOICES]
    sorted_moods = sorted(mood_counts.items(), key=lambda item: mood_order.index(item[0]) if item[0] in mood_order else -1)
    
    # **CHANGE**: Send the raw mood key (e.g., 'happy') as the label.
    # The frontend (JavaScript) will be responsible for translating this to a display name and color.
    chart_labels = [mood_key for mood_key, count in sorted_moods]
    chart_data_values = [count for mood_key, count in sorted_moods]

    return {
        'labels': chart_labels,
        'datasets': [{
            'data': chart_data_values,
        }],
        'has_data': bool(chart_data_values)
    }

def _get_emotional_arc_data(user, time_period_value):
    """
    Fetch and process daily mood averages for the Mood Trends line chart.
    """
    start_date, end_date = _get_start_end_dates(time_period_value)

    if not start_date:
        first_entry = JournalEntry.objects.filter(user=user).order_by('created_at').first()
        if not first_entry:
            return {'has_data': False}
        start_date = first_entry.created_at

    # Ensure date_range starts from the beginning of the day
    start_date_midnight = timezone.make_aware(datetime.datetime.combine(start_date.date(), datetime.time.min))
    date_range = [start_date_midnight.date() + datetime.timedelta(days=x) for x in range((end_date.date() - start_date_midnight.date()).days + 1)]
    
    entries = JournalEntry.objects.filter(
        user=user, 
        created_at__date__gte=start_date_midnight.date(), 
        created_at__date__lte=end_date.date()
    ).exclude(mood__isnull=True).exclude(mood__exact='').order_by('created_at')

    # Map entries to mood scores
    entries_with_mood_value = []
    for entry in entries:
        mood_score = MOOD_NUMERICAL.get(entry.mood)
        if mood_score is not None:
            entries_with_mood_value.append({
                'date': entry.created_at.date(),
                'score': mood_score
            })

    # Aggregate daily mood averages
    daily_moods = defaultdict(lambda: {'sum': 0, 'count': 0})
    for entry in entries_with_mood_value:
        day = entry['date']
        daily_moods[day]['sum'] += entry['score']
        daily_moods[day]['count'] += 1

    # Prepare chart data with interpolation
    chart_labels = [day.strftime('%b %d') for day in date_range]
    chart_data = []
    is_interpolated = []
    last_valid_mood = None

    # Find the first valid mood in the range to start interpolation
    for day in date_range:
         if day in daily_moods:
            last_valid_mood = daily_moods[day]['sum'] / daily_moods[day]['count']
            break

    for day in date_range:
        if day in daily_moods:
            avg_mood = daily_moods[day]['sum'] / daily_moods[day]['count']
            chart_data.append(round(avg_mood, 2))
            is_interpolated.append(False)
            last_valid_mood = avg_mood
        else:
            # Interpolate by carrying forward the last known mood
            chart_data.append(last_valid_mood)
            is_interpolated.append(True if last_valid_mood is not None else False)

    return {
        'labels': chart_labels,
        'datasets': [{'data': chart_data, 'is_interpolated': is_interpolated}],
        'has_data': any(item is not None for item in chart_data)
    }


class AIInsightsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'ai_services/ai_insights_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        
        # Ensure unique time period options
        context['time_period_options'] = [
            {'value': 'last_7_days', 'label': str(_('Last 7 Days'))},
            {'value': 'last_30_days', 'label': str(_('Last 30 Days'))},
            {'value': 'last_90_days', 'label': str(_('Last 90 Days'))},
            {'value': 'last_365_days', 'label': str(_('Last Year'))},
            {'value': 'all_time', 'label': str(_('All Time'))},
        ]
        
        selected_period = request.GET.get('time_period', 'last_30_days')
        context['selected_period'] = selected_period
        
        context['sentiment_chart_data_json'] = json.dumps({'has_data': False})
        context['emotional_arc_data_json'] = json.dumps({'has_data': False})
        
        logger.info(f"AIInsightsDashboardView loaded for user {request.user.username}, period: {selected_period}")
        return context

class SentimentChartDataView(LoginRequiredMixin, View):
    """Provide JSON data for the sentiment chart via AJAX."""
    def get(self, request, *args, **kwargs):
        time_period = request.GET.get('time_period', 'last_30_days')
        chart_data = _get_sentiment_data_for_period(request.user, time_period)
        return JsonResponse(chart_data)

class EmotionalArcDataView(LoginRequiredMixin, View):
    """Provide JSON data for the Mood Trends line chart via AJAX."""
    def get(self, request, *args, **kwargs):
        time_period = request.GET.get('time_period', 'last_30_days')
        chart_data = _get_emotional_arc_data(request.user, time_period)
        return JsonResponse(chart_data)

class StartInsightsAnalysisView(LoginRequiredMixin, View):
    """Start the Celery task for generating collective insights."""
    def post(self, request, *args, **kwargs):
        time_period = request.POST.get('time_period')
        if not time_period:
            return JsonResponse({'status': 'error', 'message': 'Time period is required.'}, status=400)
        task = generate_insights_for_period_task.delay(request.user.id, time_period)
        return JsonResponse({'status': 'processing', 'task_id': task.id})

class GetInsightsResultView(LoginRequiredMixin, View):
    """Poll for the result of the collective insights Celery task."""
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
                return JsonResponse({'status': 'FAILURE', 'message': 'Analysis failed.'}, status=500)
        else:
            return JsonResponse({'status': task_result.state})

class StartSuggestionsAnalysisView(LoginRequiredMixin, View):
    """Start the Celery task for generating life suggestions."""
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
    """Poll for the result of the life suggestions Celery task."""
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
                logger.error(f"Suggestions Task {task_id} failed: {task_result.info}")
                return JsonResponse({'status': 'FAILURE', 'message': 'Suggestion generation failed.'}, status=500)
        else:
            return JsonResponse({'status': task_result.state})
