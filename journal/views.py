# journal/views.py 

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, View, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, Http404
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.forms import inlineformset_factory 
from django.db import transaction # Import transaction
from django.utils.translation import gettext_lazy as _

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
            ('today', _('Today')), ('this_week', _('This Week')), 
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
        # context['new_entries'] = [entry for entry in context['entries'] if (timezone.now() - entry.created_at).total_seconds() <= 24 * 3600] # Corrected this line if it was causing issues, though not directly related to tags.
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
        # All database operations and Celery task dispatches will be part of this atomic transaction.
        # Tasks will be sent to broker only if the transaction successfully commits.
        with transaction.atomic(): 
            form.instance.user = self.request.user
            self.object = form.save(commit=False) 
            
            # Initialize AI fields
            self.object.ai_quote_task_id = None
            self.object.ai_mood_task_id = None
            self.object.ai_tags_task_id = None
            self.object.ai_quote_processed = False
            self.object.ai_mood_processed = False
            self.object.ai_tags_processed = False
            
            self.object.save() # Save the main object first
            
            # Process and save tags
            tag_names_list = form.cleaned_data.get('tags', []) 
            current_tags_for_entry = []
            if tag_names_list:
                for tag_name in tag_names_list:
                    tag_name_stripped = tag_name.strip()
                    if tag_name_stripped:
                        tag, created = Tag.objects.get_or_create(name__iexact=tag_name_stripped, defaults={'name': tag_name_stripped.capitalize()})
                        current_tags_for_entry.append(tag)
            self.object.tags.set(current_tags_for_entry) # Set tags for the entry
            
            # Process attachments
            attachment_formset.instance = self.object
            attachment_formset.save()
            logger.info(f"JournalEntry {self.object.pk} created with attachments and tags.")

            entry_id = self.object.id
            task_ids_dict = {} # Using a different name to avoid conflict if self.object has task_ids
            
            user_profile = self.request.user.profile 

            logger.info(f"Attempting to dispatch AI tasks for entry ID: {entry_id} based on user preferences (within transaction).")
            
            # --- Quote Task ---
            if user_profile.ai_enable_quotes:
                try:
                    # Using a lambda for transaction.on_commit
                    transaction.on_commit(lambda: 
                        generate_quote_for_entry_task.apply_async(args=[entry_id], task_id=self.object.ai_quote_task_id or None)
                    )
                    # Note: We can't get task_result.id here directly as it's deferred.
                    # We'll need to generate a task_id if we want to store it predictively, or rely on Celery signals.
                    # For simplicity, we'll assume task_id is set if dispatched.
                    # A more robust way would be to generate UUID for task_id beforehand.
                    # For now, let's clear it and let Celery assign one.
                    temp_quote_task_id = generate_quote_for_entry_task.signature(args=[entry_id]).id # Get a potential ID
                    self.object.ai_quote_task_id = temp_quote_task_id
                    task_ids_dict['quote_task_id'] = temp_quote_task_id
                    logger.info(f"Scheduled generate_quote_for_entry_task for new entry ID: {entry_id} (on commit). Task ID: {temp_quote_task_id}")
                except Exception as e:
                    logger.error(f"Failed to schedule generate_quote_for_entry_task (entry ID {entry_id}): {e}", exc_info=True)
                    self.object.ai_quote_processed = True # Mark as processed on error to avoid re-queue
            else:
                self.object.ai_quote_processed = True 
                self.object.ai_quote = None 
                logger.info(f"Quote generation skipped for entry {entry_id} as per user preference.")

            # --- Mood Task ---
            if user_profile.ai_enable_mood_detection:
                if not form.cleaned_data.get('mood'): 
                    try:
                        temp_mood_task_id = detect_mood_for_entry_task.signature(args=[entry_id]).id
                        transaction.on_commit(lambda: 
                            detect_mood_for_entry_task.apply_async(args=[entry_id], task_id=temp_mood_task_id)
                        )
                        self.object.ai_mood_task_id = temp_mood_task_id
                        task_ids_dict['mood_task_id'] = temp_mood_task_id
                        logger.info(f"Scheduled detect_mood_for_entry_task for new entry ID: {entry_id} (on commit). Task ID: {temp_mood_task_id}")
                    except Exception as e:
                        logger.error(f"Failed to schedule detect_mood_for_entry_task (entry ID {entry_id}): {e}", exc_info=True)
                        self.object.ai_mood_processed = True
                else: # User set mood
                    self.object.ai_mood_processed = True 
                    logger.info(f"Mood detection skipped for entry {entry_id} as mood was set by user.")
            else: # AI mood detection disabled
                self.object.ai_mood_processed = True 
                logger.info(f"Mood detection skipped for entry {entry_id} as per user preference.")

            # --- Tags Task ---
            if user_profile.ai_enable_tag_suggestion:
                if not current_tags_for_entry: # Only if user did not provide tags
                    try:
                        temp_tags_task_id = suggest_tags_for_entry_task.signature(args=[entry_id]).id
                        transaction.on_commit(lambda: 
                            suggest_tags_for_entry_task.apply_async(args=[entry_id], task_id=temp_tags_task_id)
                        )
                        self.object.ai_tags_task_id = temp_tags_task_id
                        task_ids_dict['tags_task_id'] = temp_tags_task_id
                        logger.info(f"Scheduled suggest_tags_for_entry_task for new entry ID: {entry_id} (on commit). Task ID: {temp_tags_task_id}")
                    except Exception as e:
                        logger.error(f"Failed to schedule suggest_tags_for_entry_task (entry ID {entry_id}): {e}", exc_info=True)
                        self.object.ai_tags_processed = True
                else: # User set tags
                    self.object.ai_tags_processed = True 
                    logger.info(f"Tag suggestion skipped for entry {entry_id} as tags were set by user.")
            else: # AI tag suggestion disabled
                self.object.ai_tags_processed = True 
                logger.info(f"Tag suggestion skipped for entry {entry_id} as per user preference.")
            
            # Save AI task IDs and processed flags again, as they might have been updated
            self.object.save(update_fields=['ai_quote_task_id', 'ai_mood_task_id', 'ai_tags_task_id', 
                                            'ai_quote_processed', 'ai_mood_processed', 'ai_tags_processed',
                                            'ai_quote', 'mood']) 
        
        # This response is sent after the transaction.on_commit block,
        # but the tasks are only truly sent to the broker when the transaction commits.
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success', 
                'message': _('Journal entry saved. AI processing scheduled based on your preferences.'),
                'entry_id': self.object.id,
                'task_ids': task_ids_dict, 
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
        if not hasattr(self, 'object') and self.kwargs.get(self.pk_url_kwarg): # Ensure self.object is available
            self.object = self.get_object()
        if self.request.method == 'POST':
            if 'attachment_formset' not in data: # Check if already added
                data['attachment_formset'] = JournalAttachmentInlineFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='attachments')
        elif 'attachment_formset' not in data: # For GET requests or if not in POST context
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
            
            self.object = form.save(commit=False) # Get the object but don't save to DB yet
            
            # Store original AI processed flags before potential reset
            original_ai_quote_processed = self.object.ai_quote_processed
            original_ai_mood_processed = self.object.ai_mood_processed
            original_ai_tags_processed = self.object.ai_tags_processed

            # Reset AI processed flags if relevant content changed
            if content_changed:
                logger.info(f"UpdateView: Content changed for entry {self.object.pk}. Resetting AI processed flags.")
                self.object.ai_quote_processed = False
                self.object.ai_quote_task_id = None
                self.object.ai_mood_processed = False 
                self.object.ai_mood_task_id = None
                self.object.ai_tags_processed = False 
                self.object.ai_tags_task_id = None

            # If mood is explicitly changed by user, AI for mood is considered "processed"
            if mood_is_being_set_by_user: 
                logger.info(f"UpdateView: Mood set by user for entry {self.object.pk}.")
                self.object.ai_mood_processed = True 
                self.object.ai_mood_task_id = None
            
            self.object.save() # Save main fields, including potentially reset AI flags

            # Process and save tags submitted by the user
            tag_names_list = form.cleaned_data.get('tags', [])
            current_tags_for_entry = [] 
            if tag_names_list:
                for tag_name in tag_names_list:
                    tag_name_stripped = tag_name.strip()
                    if tag_name_stripped:
                        tag, created = Tag.objects.get_or_create(name__iexact=tag_name_stripped, defaults={'name': tag_name_stripped.capitalize()})
                        current_tags_for_entry.append(tag)
            self.object.tags.set(current_tags_for_entry) 
            logger.info(f"UpdateView: Tags set for entry {self.object.pk}: {[t.name for t in current_tags_for_entry]}")


            attachment_formset.instance = self.object
            attachment_formset.save()
            logger.info(f"JournalEntry {self.object.pk} and attachments updated.")

            entry_id = self.object.id
            task_ids_dict = {}
            
            user_profile = self.request.user.profile

            logger.info(f"UpdateView: Attempting to schedule AI tasks for updated entry ID: {entry_id} (within transaction).")
            logger.info(f"UpdateView: Pre-dispatch state for entry {entry_id} - current_tags_for_entry: {[t.name for t in current_tags_for_entry]}, ai_tags_processed: {self.object.ai_tags_processed}, content_changed: {content_changed}")
            
            # --- Conditional Quote Generation ---
            should_run_quote_task = user_profile.ai_enable_quotes and (not self.object.ai_quote_processed) # Simplified: run if not processed
            if not user_profile.ai_enable_quotes:
                self.object.ai_quote_processed = True
                self.object.ai_quote_task_id = None
                self.object.ai_quote = None
                logger.info(f"UpdateView: Quote generation skipped for updated entry {entry_id} (user preference disabled AI).")
            elif should_run_quote_task:
                try:
                    temp_quote_task_id = generate_quote_for_entry_task.signature(args=[entry_id]).id
                    transaction.on_commit(lambda: 
                        generate_quote_for_entry_task.apply_async(args=[entry_id], task_id=temp_quote_task_id)
                    )
                    self.object.ai_quote_task_id = temp_quote_task_id
                    task_ids_dict['quote_task_id'] = temp_quote_task_id
                    logger.info(f"UpdateView: Scheduled generate_quote_for_entry_task for updated entry ID: {entry_id} (on commit). Task ID: {temp_quote_task_id}")
                except Exception as e:
                    logger.error(f"UpdateView: Failed to schedule quote task (updated entry ID {entry_id}): {e}", exc_info=True)
                    self.object.ai_quote_processed = True 
            else:
                logger.info(f"UpdateView: Quote generation not needed or already processed for updated entry {entry_id}. ai_quote_processed: {self.object.ai_quote_processed}")


            # --- Conditional Mood Detection ---
            should_run_mood_task = user_profile.ai_enable_mood_detection and \
                                   not mood_is_being_set_by_user and \
                                   (not self.object.ai_mood_processed) # Simplified: run if not set by user and not processed

            if not user_profile.ai_enable_mood_detection:
                self.object.ai_mood_processed = True
                self.object.ai_mood_task_id = None
                logger.info(f"UpdateView: Mood detection skipped for updated entry {entry_id} (user preference disabled AI).")
            elif mood_is_being_set_by_user:
                self.object.ai_mood_processed = True # Already set, confirming
                self.object.ai_mood_task_id = None
                logger.info(f"UpdateView: Mood detection skipped for updated entry {entry_id} (user set mood).")
            elif should_run_mood_task:
                try:
                    temp_mood_task_id = detect_mood_for_entry_task.signature(args=[entry_id]).id
                    transaction.on_commit(lambda: 
                        detect_mood_for_entry_task.apply_async(args=[entry_id], task_id=temp_mood_task_id)
                    )
                    self.object.ai_mood_task_id = temp_mood_task_id
                    task_ids_dict['mood_task_id'] = temp_mood_task_id
                    logger.info(f"UpdateView: Scheduled detect_mood_for_entry_task for updated entry ID: {entry_id} (on commit). Task ID: {temp_mood_task_id}")
                except Exception as e:
                    logger.error(f"UpdateView: Failed to schedule mood task (updated entry ID {entry_id}): {e}", exc_info=True)
                    self.object.ai_mood_processed = True
            else:
                logger.info(f"UpdateView: Mood detection not needed or already processed for updated entry {entry_id}. mood_is_being_set_by_user: {mood_is_being_set_by_user}, ai_mood_processed: {self.object.ai_mood_processed}")


            # --- Conditional Tag Suggestion (REVISED LOGIC) ---
            if user_profile.ai_enable_tag_suggestion:
                if current_tags_for_entry: # User submitted/kept some tags in this update.
                    self.object.ai_tags_processed = True 
                    self.object.ai_tags_task_id = None   
                    logger.info(f"UpdateView: User set/kept tags for updated entry {entry_id}. AI tag suggestion skipped by view; ai_tags_processed=True.")
                else: # User submitted an empty list for tags (cleared them) OR didn't touch the field and it was already empty.
                    # self.object.ai_tags_processed could be False if content_changed.
                    if not self.object.ai_tags_processed: # If flag indicates reprocessing is needed
                        self.object.ai_tags_task_id = None 
                        try:
                            temp_tags_task_id = suggest_tags_for_entry_task.signature(args=[entry_id]).id
                            transaction.on_commit(lambda: 
                                suggest_tags_for_entry_task.apply_async(args=[entry_id], task_id=temp_tags_task_id)
                            )
                            self.object.ai_tags_task_id = temp_tags_task_id
                            task_ids_dict['tags_task_id'] = temp_tags_task_id
                            logger.info(f"UpdateView: Scheduled suggest_tags_for_entry_task for updated entry {entry_id} (tags empty & ai_tags_processed=False, on commit). Task ID: {temp_tags_task_id}")
                        except Exception as e:
                            logger.error(f"UpdateView: Failed to schedule tag task (updated entry ID {entry_id}): {e}", exc_info=True)
                            self.object.ai_tags_processed = True 
                    else:
                        logger.info(f"UpdateView: Tags are empty for updated entry {entry_id}, but ai_tags_processed is True ({self.object.ai_tags_processed}). AI tag suggestion not scheduled.")
            
            elif not user_profile.ai_enable_tag_suggestion: 
                self.object.ai_tags_processed = True
                self.object.ai_tags_task_id = None
                logger.info(f"UpdateView: Tag suggestion skipped for updated entry {entry_id} (user preference disabled AI).")
            
            self.object.save(update_fields=['ai_quote_task_id', 'ai_mood_task_id', 'ai_tags_task_id', 
                                            'ai_quote_processed', 'ai_mood_processed', 'ai_tags_processed',
                                            'ai_quote', 'mood']) 
            
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success', 
                'message': _('Journal entry updated. AI processing scheduled based on your preferences.'),
                'entry_id': self.object.id,
                'task_ids': task_ids_dict,
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
        user_profile = request.user.profile 

        task_info_map = {
            'quote': (entry.ai_quote_task_id, entry.ai_quote_processed, 'ai_quote_processed', user_profile.ai_enable_quotes),
            'mood': (entry.ai_mood_task_id, entry.ai_mood_processed, 'ai_mood_processed', user_profile.ai_enable_mood_detection),
            'tags': (entry.ai_tags_task_id, entry.ai_tags_processed, 'ai_tags_processed', user_profile.ai_enable_tag_suggestion),
        }
        
        for task_type_key, (task_id, processed_flag_value, processed_flag_name, ai_enabled_by_user) in task_info_map.items():
            current_task_api_status = "PENDING" # Default if no other condition met
            if not ai_enabled_by_user:
                current_task_api_status = "DISABLED_BY_USER"
                if not processed_flag_value: 
                    setattr(entry, processed_flag_name, True)
                    needs_db_update_flags.append(processed_flag_name)
            elif processed_flag_value: 
                # If already marked as processed by the view (e.g., user set it, or AI previously completed)
                current_task_api_status = "SUCCESS" 
            elif task_id: # AI is enabled, not yet marked processed, and there's a task ID
                task_result = AsyncResult(task_id)
                current_task_api_status = task_result.state.upper() 
                if task_result.successful(): 
                    current_task_api_status = "SUCCESS"
                    if not getattr(entry, processed_flag_name): # Sync DB flag if task succeeded but flag wasn't set
                        setattr(entry, processed_flag_name, True)
                        needs_db_update_flags.append(processed_flag_name)
                elif task_result.failed():
                    current_task_api_status = "FAILURE"
                    if not getattr(entry, processed_flag_name): # Sync DB flag if task failed but flag wasn't set
                        setattr(entry, processed_flag_name, True) 
                        needs_db_update_flags.append(processed_flag_name)
                    logger.warning(f"Celery task {task_id} ({task_type_key}) for entry {entry.id} reported FAILURE. Traceback: {task_result.traceback}")
                # If state is PENDING, STARTED, RETRY, current_task_api_status will reflect that
            # If no task_id and not processed_flag_value and ai_enabled_by_user, it remains PENDING (task might have failed to dispatch)
            
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
            'mood': entry.mood, 
            'tags': [tag.name for tag in entry.tags.all()] 
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
