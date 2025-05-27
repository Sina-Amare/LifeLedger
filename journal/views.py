from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, View, DeleteView # CORRECTED: Added DeleteView back
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, Http404
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.forms import inlineformset_factory 
from django.db import transaction
from django.utils.translation import gettext_lazy as _ # For messages

from .forms import JournalEntryForm, JournalAttachmentForm, MOOD_CHOICES_FORM_DISPLAY 
from .models import JournalEntry, JournalAttachment, Tag
from django.db.models import Q
from django.utils import timezone
import logging

from ai_services.tasks import (
    generate_quote_for_entry_task,
    detect_mood_for_entry_task,
    suggest_tags_for_entry_task
)
from celery.result import AsyncResult 

# Import UserProfile from the user_profile app
from user_profile.models import UserProfile as NewUserProfile 

logger = logging.getLogger(__name__)

JournalAttachmentInlineFormSet = inlineformset_factory(
    JournalEntry,
    JournalAttachment,
    form=JournalAttachmentForm,
    extra=1, 
    can_delete=True,
    fields=['file']
)

MOOD_VISUALS = {
    'happy': {'emoji': "😊", 'text_color': "text-green-700 dark:text-green-400", 'bg_color': "bg-green-100 dark:bg-green-800", 'border_color': "border-green-500"},
    'sad': {'emoji': "😢", 'text_color': "text-blue-700 dark:text-blue-400", 'bg_color': "bg-blue-100 dark:bg-blue-800", 'border_color': "border-blue-500"},
    'angry': {'emoji': "😠", 'text_color': "text-red-700 dark:text-red-400", 'bg_color': "bg-red-100 dark:bg-red-800", 'border_color': "border-red-500"},
    'calm': {'emoji': "😌", 'text_color': "text-sky-700 dark:text-sky-400", 'bg_color': "bg-sky-100 dark:bg-sky-800", 'border_color': "border-sky-500"},
    'neutral': {'emoji': "😐", 'text_color': "text-gray-700 dark:text-gray-400", 'bg_color': "bg-gray-100 dark:bg-gray-700", 'border_color': "border-gray-500"},
    'excited': {'emoji': "🎉", 'text_color': "text-yellow-700 dark:text-yellow-400", 'bg_color': "bg-yellow-100 dark:bg-yellow-800", 'border_color': "border-yellow-500"},
}

class JournalEntryListView(LoginRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'journal/journal_list.html'
    context_object_name = 'entries'
    paginate_by = 10

    def get_queryset(self):
        queryset = JournalEntry.objects.filter(user=self.request.user).prefetch_related('tags', 'attachments')
        mood = self.request.GET.get('mood')
        time_period = self.request.GET.get('time_period')
        is_favorite = self.request.GET.get('is_favorite')
        search_query = self.request.GET.get('q')
        tag_filter_name = self.request.GET.get('tag_filter')

        if mood and mood != '':
            queryset = queryset.filter(mood=mood)
        if time_period and time_period != 'all':
            now = timezone.now()
            if time_period == 'today':
                queryset = queryset.filter(created_at__date=now.date())
            elif time_period == 'this_week':
                start_of_week = now.date() - timezone.timedelta(days=now.weekday())
                queryset = queryset.filter(created_at__date__gte=start_of_week)
            elif time_period == 'this_month':
                queryset = queryset.filter(created_at__year=now.year, created_at__month=now.month)
            elif time_period == 'this_year':
                queryset = queryset.filter(created_at__year=now.year)
        if is_favorite == 'on':
            queryset = queryset.filter(is_favorite=True)
        if tag_filter_name:
            queryset = queryset.filter(tags__name__iexact=tag_filter_name)
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(tags__name__icontains=search_query)
            ).distinct()
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mood_options'] = [option for option in MOOD_CHOICES_FORM_DISPLAY if option[0] != ""]
        context['mood_visuals'] = MOOD_VISUALS
        context['time_period_options'] = [
            ('today', _('Today')), ('this_week', _('This Week')), # Translated options
            ('this_month', _('This Month')), ('this_year', _('This Year')),
        ]
        context['current_mood'] = self.request.GET.get('mood', '')
        context['current_time_period'] = self.request.GET.get('time_period', 'all')
        context['current_is_favorite'] = self.request.GET.get('is_favorite') == 'on'
        context['current_search_query'] = self.request.GET.get('q', '')
        user_entry_tags_pks = JournalEntry.objects.filter(user=self.request.user).values_list('tags__pk', flat=True).distinct()
        context['all_tags_for_filter'] = Tag.objects.filter(pk__in=[pk for pk in user_entry_tags_pks if pk is not None]).order_by('name')
        context['current_tag_filter'] = self.request.GET.get('tag_filter', '')
        context['is_filtered'] = any([
            context['current_mood'], context['current_time_period'] != 'all',
            context['current_is_favorite'], context['current_search_query'], context['current_tag_filter']
        ])
        context['new_entries'] = [entry for entry in context['entries'] if (timezone.now() - entry.created_at).total_seconds() <= 24 * 3600]
        return context

class JournalEntryDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = JournalEntry
    template_name = 'journal/journal_detail.html'
    context_object_name = 'entry'

    def test_func(self):
        entry = self.get_object()
        return entry.user == self.request.user
    
    def get_queryset(self):
        return JournalEntry.objects.filter(user=self.request.user).prefetch_related('tags', 'attachments')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mood_visuals'] = MOOD_VISUALS
        return context

class JournalEntryCreateView(LoginRequiredMixin, CreateView):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if 'attachment_formset' not in kwargs:
            if self.request.method == 'POST':
                data['attachment_formset'] = JournalAttachmentInlineFormSet(self.request.POST, self.request.FILES, prefix='attachments')
            else:
                data['attachment_formset'] = JournalAttachmentInlineFormSet(prefix='attachments')
        data['predefined_tags'] = Tag.objects.all().order_by('name')
        data['initial_tags_str'] = '' 
        return data

    def post(self, request, *args, **kwargs):
        self.object = None 
        form = self.get_form()
        attachment_formset = JournalAttachmentInlineFormSet(request.POST, request.FILES, prefix='attachments')
        if form.is_valid() and attachment_formset.is_valid():
            logger.info("Main form and attachment formset are valid for create.")
            return self.form_valid(form, attachment_formset)
        else:
            logger.error(f"Form or Formset invalid on POST. Form errors: {form.errors.as_json()}. Formset errors: {attachment_formset.errors} {attachment_formset.non_form_errors()}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'form_errors': form.errors.as_json(), 'formset_errors': attachment_formset.errors}, status=400)
            return self.form_invalid(form, attachment_formset)

    def form_valid(self, form, attachment_formset):
        with transaction.atomic(): 
            form.instance.user = self.request.user
            self.object = form.save(commit=False) 
            
            self.object.ai_quote_task_id = None
            self.object.ai_mood_task_id = None
            self.object.ai_tags_task_id = None
            self.object.ai_quote_processed = False
            self.object.ai_mood_processed = False
            self.object.ai_tags_processed = False
            
            self.object.save() 
            
            tag_names_list = form.cleaned_data.get('tags', []) 
            current_tags_for_entry = []
            if tag_names_list:
                for tag_name in tag_names_list:
                    tag_name_stripped = tag_name.strip()
                    if tag_name_stripped:
                        tag, created = Tag.objects.get_or_create(name__iexact=tag_name_stripped, defaults={'name': tag_name_stripped.capitalize()})
                        current_tags_for_entry.append(tag)
            self.object.tags.set(current_tags_for_entry)
            
            attachment_formset.instance = self.object
            attachment_formset.save()
            logger.info(f"JournalEntry {self.object.pk} created with attachments and tags.")

            entry_id = self.object.id
            task_ids = {}
            
            user_profile = self.request.user.profile 

            logger.info(f"Attempting to dispatch AI tasks for entry ID: {entry_id} based on user preferences.")
            
            if user_profile.ai_enable_quotes:
                try:
                    task_result = generate_quote_for_entry_task.delay(entry_id)
                    self.object.ai_quote_task_id = task_result.id
                    task_ids['quote_task_id'] = task_result.id
                    logger.info(f"Dispatched generate_quote_for_entry_task for new entry ID: {entry_id}, Task ID: {task_result.id}")
                except Exception as e:
                    logger.error(f"Failed to dispatch generate_quote_for_entry_task (entry ID {entry_id}): {e}", exc_info=True)
            else:
                self.object.ai_quote_processed = True 
                self.object.ai_quote = None 
                logger.info(f"Quote generation skipped for entry {entry_id} as per user preference.")

            if user_profile.ai_enable_mood_detection:
                # Only run mood detection if mood was not set by user in the form
                if not form.cleaned_data.get('mood'): 
                    try:
                        task_result = detect_mood_for_entry_task.delay(entry_id)
                        self.object.ai_mood_task_id = task_result.id
                        task_ids['mood_task_id'] = task_result.id
                        logger.info(f"Dispatched detect_mood_for_entry_task for new entry ID: {entry_id}, Task ID: {task_result.id}")
                    except Exception as e:
                        logger.error(f"Failed to dispatch detect_mood_for_entry_task (entry ID {entry_id}): {e}", exc_info=True)
                else:
                    self.object.ai_mood_processed = True # User set mood, so AI processing for mood is "done"
                    logger.info(f"Mood detection skipped for entry {entry_id} as mood was set by user.")
            else:
                self.object.ai_mood_processed = True 
                logger.info(f"Mood detection skipped for entry {entry_id} as per user preference.")

            if user_profile.ai_enable_tag_suggestion:
                # Only run tag suggestion if no tags were provided by user
                if not current_tags_for_entry: 
                    try:
                        task_result = suggest_tags_for_entry_task.delay(entry_id)
                        self.object.ai_tags_task_id = task_result.id
                        task_ids['tags_task_id'] = task_result.id
                        logger.info(f"Dispatched suggest_tags_for_entry_task for new entry ID: {entry_id}, Task ID: {task_result.id}")
                    except Exception as e:
                        logger.error(f"Failed to dispatch suggest_tags_for_entry_task (entry ID {entry_id}): {e}", exc_info=True)
                else:
                    self.object.ai_tags_processed = True # User set tags
                    logger.info(f"Tag suggestion skipped for entry {entry_id} as tags were set by user.")
            else:
                self.object.ai_tags_processed = True 
                logger.info(f"Tag suggestion skipped for entry {entry_id} as per user preference.")
            
            self.object.save(update_fields=['ai_quote_task_id', 'ai_mood_task_id', 'ai_tags_task_id', 
                                           'ai_quote_processed', 'ai_mood_processed', 'ai_tags_processed',
                                           'ai_quote', 'mood']) 
        
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success', 
                'message': _('Journal entry saved. AI processing initiated based on your preferences.'),
                'entry_id': self.object.id,
                'task_ids': task_ids, 
                'redirect_url': self.object.get_absolute_url() 
            })
        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form, attachment_formset):
        logger.warning(f"CreateView form_invalid. Form errors: {form.errors.as_json()}")
        if attachment_formset and not attachment_formset.is_valid():
            logger.warning(f"  Attachment formset errors: {attachment_formset.errors} {attachment_formset.non_form_errors()}")
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'form_errors': form.errors.as_json(), 'formset_errors': attachment_formset.errors}, status=400)
        return self.render_to_response(self.get_context_data(form=form, attachment_formset=attachment_formset))

class JournalEntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'
    context_object_name = 'entry'

    def get_queryset(self):
        return JournalEntry.objects.filter(user=self.request.user).prefetch_related('tags')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if not hasattr(self, 'object') and self.kwargs.get(self.pk_url_kwarg):
            self.object = self.get_object()
        if self.request.method == 'POST':
            if 'attachment_formset' not in data:
                data['attachment_formset'] = JournalAttachmentInlineFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='attachments')
        elif 'attachment_formset' not in data: 
            data['attachment_formset'] = JournalAttachmentInlineFormSet(instance=self.object, prefix='attachments')
        data['predefined_tags'] = Tag.objects.all().order_by('name')
        if self.object and hasattr(self.object, 'tags'):
            initial_tag_names = [tag.name for tag in self.object.tags.all().order_by('name')]
            data['initial_tags_str'] = ', '.join(initial_tag_names)
        else:
            data['initial_tags_str'] = ''
        return data
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        attachment_formset = JournalAttachmentInlineFormSet(request.POST, request.FILES, instance=self.object, prefix='attachments')
        if form.is_valid() and attachment_formset.is_valid():
            logger.info(f"Main form and attachment formset are valid for update (entry ID: {self.object.pk}).")
            return self.form_valid(form, attachment_formset)
        else:
            if not form.is_valid(): logger.error(f"UpdateView - Main form invalid: {form.errors.as_json()}")
            if not attachment_formset.is_valid():
                logger.error(f"UpdateView - Attachment formset invalid: {attachment_formset.errors}")
                logger.error(f"UpdateView - Attachment formset non-form errors: {attachment_formset.non_form_errors()}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'form_errors': form.errors.as_json(), 'formset_errors': attachment_formset.errors}, status=400)
            return self.form_invalid(form, attachment_formset)

    def form_valid(self, form, attachment_formset):
        with transaction.atomic():
            content_changed = 'content' in form.changed_data
            mood_is_being_set_by_user = 'mood' in form.changed_data and form.cleaned_data.get('mood')
            tags_are_being_set_by_user = 'tags' in form.changed_data and form.cleaned_data.get('tags')
            
            self.object = form.save(commit=False)
            
            # Always reset AI processed flags if relevant content changed,
            # so AI can re-evaluate if enabled by user.
            if content_changed:
                self.object.ai_quote_processed = False
                self.object.ai_quote_task_id = None
                self.object.ai_mood_processed = False # Mood might change with content
                self.object.ai_mood_task_id = None
                self.object.ai_tags_processed = False # Tags might change with content
                self.object.ai_tags_task_id = None

            # If mood is explicitly changed by user, AI for mood is considered "processed" by user action
            if 'mood' in form.changed_data: 
                self.object.ai_mood_processed = True # User has taken control of mood
                self.object.ai_mood_task_id = None
            
            # If tags are explicitly changed by user, AI for tags is considered "processed" by user action
            if 'tags' in form.changed_data:
                self.object.ai_tags_processed = True # User has taken control of tags
                self.object.ai_tags_task_id = None

            self.object.save()

            tag_names_list = form.cleaned_data.get('tags', [])
            current_tags_for_entry = []
            if tag_names_list:
                for tag_name in tag_names_list:
                    tag_name_stripped = tag_name.strip()
                    if tag_name_stripped:
                        tag, created = Tag.objects.get_or_create(name__iexact=tag_name_stripped, defaults={'name': tag_name_stripped.capitalize()})
                        current_tags_for_entry.append(tag)
            self.object.tags.set(current_tags_for_entry)

            attachment_formset.instance = self.object
            attachment_formset.save()
            logger.info(f"JournalEntry {self.object.pk} and attachments updated.")

            entry_id = self.object.id
            task_ids = {}
            
            user_profile = self.request.user.profile

            logger.info(f"Attempting to dispatch AI tasks for updated entry ID: {entry_id} based on user preferences.")
            
            # Conditional Quote Generation: Run if enabled and content changed OR if no quote exists yet
            if user_profile.ai_enable_quotes and (content_changed or not self.object.ai_quote):
                self.object.ai_quote_processed = False # Reset for new processing
                try:
                    task_result = generate_quote_for_entry_task.delay(entry_id)
                    self.object.ai_quote_task_id = task_result.id
                    task_ids['quote_task_id'] = task_result.id
                    logger.info(f"Dispatched generate_quote_for_entry_task for updated entry ID: {entry_id}, Task ID: {task_result.id}")
                except Exception as e:
                    logger.error(f"Failed to dispatch quote task (updated entry ID {entry_id}): {e}", exc_info=True)
                    self.object.ai_quote_processed = True # Mark processed on error to avoid re-queue
            elif not user_profile.ai_enable_quotes:
                self.object.ai_quote_processed = True
                self.object.ai_quote_task_id = None
                self.object.ai_quote = None 
                logger.info(f"Quote generation skipped for updated entry {entry_id} (user preference).")

            # Conditional Mood Detection: Run if enabled AND mood was NOT set by user in this update AND (content changed OR no mood exists)
            if user_profile.ai_enable_mood_detection and not mood_is_being_set_by_user and (content_changed or not self.object.mood):
                self.object.ai_mood_processed = False # Reset for new processing
                try:
                    task_result = detect_mood_for_entry_task.delay(entry_id)
                    self.object.ai_mood_task_id = task_result.id
                    task_ids['mood_task_id'] = task_result.id
                    logger.info(f"Dispatched detect_mood_for_entry_task for updated entry ID: {entry_id}, Task ID: {task_result.id}")
                except Exception as e:
                    logger.error(f"Failed to dispatch mood task (updated entry ID {entry_id}): {e}", exc_info=True)
                    self.object.ai_mood_processed = True # Mark processed on error
            elif not user_profile.ai_enable_mood_detection or mood_is_being_set_by_user:
                self.object.ai_mood_processed = True # User preference or user set it
                self.object.ai_mood_task_id = None
                logger.info(f"Mood detection skipped for updated entry {entry_id} (user preference or user set mood).")

            # Conditional Tag Suggestion: Run if enabled AND tags were NOT set by user in this update AND (content changed OR no tags exist)
            if user_profile.ai_enable_tag_suggestion and not tags_are_being_set_by_user and (content_changed or not self.object.tags.exists()):
                self.object.ai_tags_processed = False # Reset for new processing
                try:
                    task_result = suggest_tags_for_entry_task.delay(entry_id)
                    self.object.ai_tags_task_id = task_result.id
                    task_ids['tags_task_id'] = task_result.id
                    logger.info(f"Dispatched suggest_tags_for_entry_task for updated entry ID: {entry_id}, Task ID: {task_result.id}")
                except Exception as e:
                    logger.error(f"Failed to dispatch tag task (updated entry ID {entry_id}): {e}", exc_info=True)
                    self.object.ai_tags_processed = True # Mark processed on error
            elif not user_profile.ai_enable_tag_suggestion or tags_are_being_set_by_user:
                self.object.ai_tags_processed = True # User preference or user set tags
                self.object.ai_tags_task_id = None
                logger.info(f"Tag suggestion skipped for updated entry {entry_id} (user preference or user set tags).")
            
            self.object.save(update_fields=['ai_quote_task_id', 'ai_mood_task_id', 'ai_tags_task_id', 
                                           'ai_quote_processed', 'ai_mood_processed', 'ai_tags_processed',
                                           'ai_quote', 'mood']) 
            
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success', 
                'message': _('Journal entry updated. AI processing initiated based on your preferences.'),
                'entry_id': self.object.id,
                'task_ids': task_ids,
                'redirect_url': self.object.get_absolute_url()
            })
        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form, attachment_formset):
        logger.error(f"UpdateView.form_invalid. Form errors: {form.errors.as_json()}")
        if attachment_formset and not attachment_formset.is_valid():
            logger.error(f"  UpdateView - Attachment formset errors: {attachment_formset.errors}")
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'form_errors': form.errors.as_json(), 'formset_errors': attachment_formset.errors}, status=400)
        return self.render_to_response(self.get_context_data(form=form, attachment_formset=attachment_formset))

    def test_func(self):
        entry = self.get_object()
        return entry.user == self.request.user

class AIServiceStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        try:
            entry_id = self.kwargs.get('entry_id') 
            if not entry_id:
                logger.warning("AIServiceStatusView.test_func: entry_id not found in URL kwargs.")
                return False
            entry = JournalEntry.objects.get(pk=entry_id)
            is_owner = entry.user == self.request.user
            if not is_owner:
                logger.warning(f"AIServiceStatusView.test_func: User {self.request.user.username} attempted to access entry {entry_id} owned by {entry.user.username}.")
            return is_owner
        except JournalEntry.DoesNotExist:
            logger.warning(f"AIServiceStatusView.test_func: JournalEntry with pk={entry_id} does not exist.")
            return False 
        except Exception as e: 
            logger.error(f"AIServiceStatusView.test_func: Unexpected error for entry_id {entry_id}: {e}", exc_info=True)
            return False

    def get(self, request, entry_id, *args, **kwargs):
        try:
            entry = JournalEntry.objects.get(pk=entry_id) 
        except JournalEntry.DoesNotExist:
            logger.error(f"AIServiceStatusView.get: Entry ID {entry_id} not found.")
            return JsonResponse({'status': 'error', 'message': 'Entry not found.'}, status=404)

        statuses = {}
        needs_db_update_flags = [] 
        user_profile = request.user.profile # Get user profile for AI preferences

        task_info_map = {
            'quote': (entry.ai_quote_task_id, entry.ai_quote_processed, 'ai_quote_processed', user_profile.ai_enable_quotes),
            'mood': (entry.ai_mood_task_id, entry.ai_mood_processed, 'ai_mood_processed', user_profile.ai_enable_mood_detection),
            'tags': (entry.ai_tags_task_id, entry.ai_tags_processed, 'ai_tags_processed', user_profile.ai_enable_tag_suggestion),
        }
        
        for task_type_key, (task_id, processed_flag_value, processed_flag_name, ai_enabled_by_user) in task_info_map.items():
            current_task_api_status = "PENDING" 
            if not ai_enabled_by_user:
                current_task_api_status = "DISABLED_BY_USER"
                if not processed_flag_value: # If not already marked as processed (e.g. disabled)
                    setattr(entry, processed_flag_name, True)
                    needs_db_update_flags.append(processed_flag_name)
            elif processed_flag_value: 
                current_task_api_status = "SUCCESS" 
            elif task_id:
                task_result = AsyncResult(task_id)
                current_task_api_status = task_result.state.upper() 
                if task_result.successful(): 
                    current_task_api_status = "SUCCESS"
                    if not getattr(entry, processed_flag_name):
                        setattr(entry, processed_flag_name, True)
                        needs_db_update_flags.append(processed_flag_name)
                elif task_result.failed():
                    current_task_api_status = "FAILURE"
                    if not getattr(entry, processed_flag_name): 
                        setattr(entry, processed_flag_name, True) 
                        needs_db_update_flags.append(processed_flag_name)
                    logger.warning(f"Celery task {task_id} ({task_type_key}) for entry {entry.id} reported FAILURE. Traceback: {task_result.traceback}")
            statuses[f'{task_type_key}_status'] = current_task_api_status
        
        if needs_db_update_flags:
            unique_flags_to_update = list(set(needs_db_update_flags))
            if unique_flags_to_update:
                entry.save(update_fields=unique_flags_to_update)
                logger.info(f"Updated AI processed flags for entry {entry.id} from AIServiceStatusView: {unique_flags_to_update}")

        all_done_now = (not user_profile.ai_enable_quotes or entry.ai_quote_processed) and \
                       (not user_profile.ai_enable_mood_detection or entry.ai_mood_processed) and \
                       (not user_profile.ai_enable_tag_suggestion or entry.ai_tags_processed)


        return JsonResponse({
            'status': 'ok', 'entry_id': entry.id, 'task_statuses': statuses, 'all_done': all_done_now,
            'ai_quote': entry.ai_quote if user_profile.ai_enable_quotes else "", 
            'mood': entry.mood, # Mood can be user-set or AI-set, display regardless of AI pref for mood detection
            'tags': [tag.name for tag in entry.tags.all()] # Tags are user-set or AI-suggested, display regardless
        })

class JournalEntryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = JournalEntry
    template_name = 'journal/journal_confirm_delete.html'
    success_url = reverse_lazy('journal:journal_list')
    context_object_name = 'entry'

    def test_func(self):
        entry = self.get_object()
        return entry.user == self.request.user

    def get_queryset(self):
        return JournalEntry.objects.filter(user=self.request.user)

class JournalEntryAjaxDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = JournalEntry
    http_method_names = ['post'] 

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Entry not found (dispatch).'}, status=404)
            raise
        except PermissionDenied: 
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Permission denied (dispatch).'}, status=403)
            raise

    def test_func(self):
        try:
            self.object = self.get_object() 
            return self.object.user == self.request.user
        except Http404: 
            return False

    def handle_no_permission(self):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Permission denied (handle_no_permission).'}, status=403)
        return super().handle_no_permission()

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object() 
            entry_pk = self.object.pk
            entry_title = self.object.title or "Untitled Entry" 
            self.object.delete()
            logger.info(f"User {request.user.username} successfully deleted journal entry PK: {entry_pk}, Title: '{entry_title}' via AJAX.")
            return JsonResponse({'status': 'success', 'message': _('Entry deleted successfully.'), 'entry_id': entry_pk})
        except Http404: 
            logger.warning(f"JournalEntryAjaxDeleteView: Entry not found in POST for pk={kwargs.get('pk')} by user {request.user.username}.")
            return JsonResponse({'status': 'error', 'message': _('Entry not found.')}, status=404)
        except Exception as e:
            logger.error(f"Unexpected error in JournalEntryAjaxDeleteView POST for pk={kwargs.get('pk')} by user {request.user.username}: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': _('An unexpected server error occurred.')}, status=500)

