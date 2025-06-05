# journal/views.py 

from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy 
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, View, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, Http404 
from django.core.exceptions import PermissionDenied
from django.forms import inlineformset_factory 
from django.db import transaction 
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from collections import Counter 
import datetime 
import json 

from .forms import JournalEntryForm, JournalAttachmentForm, MOOD_CHOICES_FORM_DISPLAY 
from .models import JournalEntry, JournalAttachment, Tag
from django.db.models import Q

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

# Corrected MOOD_VISUALS with proper emoji for 'excited'
MOOD_VISUALS = {
    'happy': {'emoji': "😊", 'text_color': "text-green-700 dark:text-green-400", 'bg_color': "bg-green-100 dark:bg-green-800", 'border_color': "border-green-500"},
    'sad': {'emoji': "😢", 'text_color': "text-blue-700 dark:text-blue-400", 'bg_color': "bg-blue-100 dark:bg-blue-800", 'border_color': "border-blue-500"},
    'angry': {'emoji': "😠", 'text_color': "text-red-700 dark:text-red-400", 'bg_color': "bg-red-100 dark:bg-red-800", 'border_color': "border-red-500"},
    'calm': {'emoji': "😌", 'text_color': "text-sky-700 dark:text-sky-400", 'bg_color': "bg-sky-100 dark:bg-sky-800", 'border_color': "border-sky-500"},
    'neutral': {'emoji': "😐", 'text_color': "text-gray-700 dark:text-gray-400", 'bg_color': "bg-gray-100 dark:bg-gray-700", 'border_color': "border-gray-500"},
    'excited': {'emoji': "🎉", 'text_color': "text-yellow-700 dark:text-yellow-400", 'bg_color': "bg-yellow-100 dark:bg-yellow-800", 'border_color': "border-yellow-500"}, # Corrected emoji
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
            ('all', _('All Time')) 
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
            task_ids_dict = {} 
            
            user_profile = self.request.user.profile 

            logger.info(f"Attempting to dispatch AI tasks for entry ID: {entry_id} based on user preferences (within transaction).")
            
            if user_profile.ai_enable_quotes:
                try:
                    temp_quote_task_id = generate_quote_for_entry_task.signature(args=[entry_id]).id 
                    transaction.on_commit(lambda: 
                        generate_quote_for_entry_task.apply_async(args=[entry_id], task_id=temp_quote_task_id)
                    )
                    self.object.ai_quote_task_id = temp_quote_task_id
                    task_ids_dict['quote_task_id'] = temp_quote_task_id
                    logger.info(f"Scheduled generate_quote_for_entry_task for new entry ID: {entry_id} (on commit). Task ID: {temp_quote_task_id}")
                except Exception as e:
                    logger.error(f"Failed to schedule generate_quote_for_entry_task (entry ID {entry_id}): {e}", exc_info=True)
                    self.object.ai_quote_processed = True 
            else:
                self.object.ai_quote_processed = True 
                self.object.ai_quote = None 
                logger.info(f"Quote generation skipped for entry {entry_id} as per user preference.")

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
                else: 
                    self.object.ai_mood_processed = True 
                    logger.info(f"Mood detection skipped for entry {entry_id} as mood was set by user.")
            else: 
                self.object.ai_mood_processed = True 
                logger.info(f"Mood detection skipped for entry {entry_id} as per user preference.")

            if user_profile.ai_enable_tag_suggestion:
                if not current_tags_for_entry: 
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
                else: 
                    self.object.ai_tags_processed = True 
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
            
            self.object = form.save(commit=False) 
            
            original_ai_quote_processed = self.object.ai_quote_processed
            original_ai_mood_processed = self.object.ai_mood_processed
            original_ai_tags_processed = self.object.ai_tags_processed

            if content_changed:
                logger.info(f"UpdateView: Content changed for entry {self.object.pk}. Resetting AI processed flags.")
                self.object.ai_quote_processed = False
                self.object.ai_quote_task_id = None
                self.object.ai_mood_processed = False 
                self.object.ai_mood_task_id = None
                self.object.ai_tags_processed = False 
                self.object.ai_tags_task_id = None

            if mood_is_being_set_by_user: 
                logger.info(f"UpdateView: Mood set by user for entry {self.object.pk}.")
                self.object.ai_mood_processed = True 
                self.object.ai_mood_task_id = None
            
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
            logger.info(f"UpdateView: Tags set for entry {self.object.pk}: {[t.name for t in current_tags_for_entry]}")

            attachment_formset.instance = self.object
            attachment_formset.save()
            logger.info(f"JournalEntry {self.object.pk} and attachments updated.")

            entry_id = self.object.id
            task_ids_dict = {}
            
            user_profile = self.request.user.profile

            logger.info(f"UpdateView: Attempting to schedule AI tasks for updated entry ID: {entry_id} (within transaction).")
            logger.info(f"UpdateView: Pre-dispatch state for entry {entry_id} - current_tags_for_entry: {[t.name for t in current_tags_for_entry]}, ai_tags_processed: {self.object.ai_tags_processed}, content_changed: {content_changed}")
            
            should_run_quote_task = user_profile.ai_enable_quotes and (not self.object.ai_quote_processed) 
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

            should_run_mood_task = user_profile.ai_enable_mood_detection and \
                                   not mood_is_being_set_by_user and \
                                   (not self.object.ai_mood_processed) 

            if not user_profile.ai_enable_mood_detection:
                self.object.ai_mood_processed = True
                self.object.ai_mood_task_id = None
                logger.info(f"UpdateView: Mood detection skipped for updated entry {entry_id} (user preference disabled AI).")
            elif mood_is_being_set_by_user:
                self.object.ai_mood_processed = True 
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

            if user_profile.ai_enable_tag_suggestion:
                if current_tags_for_entry: 
                    self.object.ai_tags_processed = True 
                    self.object.ai_tags_task_id = None   
                    logger.info(f"UpdateView: User set/kept tags for updated entry {entry_id}. AI tag suggestion skipped by view; ai_tags_processed=True.")
                else: 
                    if not self.object.ai_tags_processed: 
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
            current_task_api_status = "PENDING" 
            if not ai_enabled_by_user:
                current_task_api_status = "DISABLED_BY_USER"
                if not processed_flag_value: 
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

# --- AI INSIGHTS DASHBOARD VIEW (Corrected and updated) ---
class AIInsightsDashboardView(LoginRequiredMixin, TemplateView):
    """
    View to display the AI Insights Dashboard.
    This view will handle fetching and preparing data for various AI-driven analyses
    of the user's journal entries, starting with sentiment trend analysis.
    """
    template_name = 'journal/ai_insights_dashboard.html'

    def _get_sentiment_data_for_period(self, user, time_period_value):
        """
        Helper method to fetch and process sentiment data for a given user and time period.
        Returns a dictionary suitable for JSON response for the chart.
        """
        end_date = timezone.now()
        start_date = None
        
        # Define valid periods to check against
        valid_periods = ['last_7_days', 'last_30_days', 'last_90_days', 'last_365_days', 'all_time']
        if time_period_value not in valid_periods: # Default to last_30_days if invalid
            time_period_value = 'last_30_days'

        if time_period_value == 'last_7_days':
            start_date = end_date - datetime.timedelta(days=6) # Inclusive of the start day
        elif time_period_value == 'last_30_days':
            start_date = end_date - datetime.timedelta(days=29)
        elif time_period_value == 'last_90_days':
            start_date = end_date - datetime.timedelta(days=89)
        elif time_period_value == 'last_365_days':
            start_date = end_date - datetime.timedelta(days=364)
        # 'all_time' will leave start_date as None

        entries_query = JournalEntry.objects.filter(user=user)
        if start_date:
            # Ensure correct timezone handling for date range queries
            start_of_day_start_date = timezone.make_aware(datetime.datetime.combine(start_date.date(), datetime.time.min), timezone.get_default_timezone())
            end_of_day_end_date = timezone.make_aware(datetime.datetime.combine(end_date.date(), datetime.time.max), timezone.get_default_timezone())
            entries_for_period = entries_query.filter(
                created_at__gte=start_of_day_start_date,
                created_at__lte=end_of_day_end_date
            )
        else: # All time
            entries_for_period = entries_query.all()
        
        mood_counts = Counter(entry.mood for entry in entries_for_period.only('mood') if entry.mood)
        
        # Get display names for moods, ensuring they are strings
        mood_display_names_dict = {key: str(name) for key, name in JournalEntry.MOOD_CHOICES}
        
        chart_labels = []
        chart_data_values = []
        chart_background_colors = []
        chart_border_colors = []

        # Iterate through MOOD_VISUALS to ensure consistent order and access to emojis/colors
        for mood_value, visual_details in MOOD_VISUALS.items():
            if mood_counts[mood_value] > 0: # Only include moods that actually occurred
                emoji = visual_details.get('emoji', '')
                display_name = mood_display_names_dict.get(mood_value, mood_value.capitalize())
                # Prepend emoji to the label for display in the chart
                chart_labels.append(f"{emoji} {display_name}".strip()) 
                chart_data_values.append(mood_counts[mood_value])
                
                # Define a consistent color palette for Chart.js
                color_palette_js = {
                    'happy': {'bg': 'rgba(75, 192, 192, 0.6)', 'border': 'rgb(75, 192, 192)'},
                    'sad': {'bg': 'rgba(54, 162, 235, 0.6)', 'border': 'rgb(54, 162, 235)'},
                    'angry': {'bg': 'rgba(255, 99, 132, 0.6)', 'border': 'rgb(255, 99, 132)'},
                    'calm': {'bg': 'rgba(153, 102, 255, 0.6)', 'border': 'rgb(153, 102, 255)'},
                    'neutral': {'bg': 'rgba(201, 203, 207, 0.6)', 'border': 'rgb(201, 203, 207)'},
                    'excited': {'bg': 'rgba(255, 205, 86, 0.6)', 'border': 'rgb(255, 205, 86)'}
                }
                default_chart_js_color = {'bg': 'rgba(100, 100, 100, 0.6)', 'border': 'rgb(100, 100, 100)'}
                chart_mood_colors = color_palette_js.get(mood_value, default_chart_js_color)
                
                chart_background_colors.append(chart_mood_colors['bg'])
                chart_border_colors.append(chart_mood_colors['border'])

        return {
            'labels': chart_labels,
            'datasets': [{
                'label': str(_('Mood Occurrences')), 
                'data': chart_data_values,
                'backgroundColor': chart_background_colors,
                'borderColor': chart_border_colors,
                'borderWidth': 1,
                'borderRadius': 5, # Added for a slightly more modern look
                'hoverBorderWidth': 2,
                'hoverBorderColor': '#333'
            }],
            'has_data': bool(chart_data_values)
        }

    def get_context_data(self, **kwargs):
        """
        Prepares the context data for the AI Insights Dashboard for initial page load.
        """
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

        initial_chart_data_dict = self._get_sentiment_data_for_period(request.user, selected_period)
        
        context['sentiment_chart_data_json'] = json.dumps(initial_chart_data_dict)
        context['has_sentiment_data'] = initial_chart_data_dict.get('has_data', False)
        
        serializable_mood_visuals = {
            mood: {k: str(v) for k, v in visuals.items()} 
            for mood, visuals in MOOD_VISUALS.items()
        }
        context['mood_visuals_json'] = json.dumps(serializable_mood_visuals)
        
        logger.info(f"AIInsightsDashboardView: Initial load for user {request.user.username}, period: {selected_period}")
        return context

class SentimentChartDataView(LoginRequiredMixin, View):
    """
    Provides JSON data for the sentiment chart, used for AJAX updates.
    Accepts a 'time_period' GET parameter.
    """
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to fetch sentiment chart data for the specified time period.
        """
        user = request.user
        time_period_value = request.GET.get('time_period', 'last_30_days') 

        # Use the helper method from AIInsightsDashboardView (or a refactored shared function)
        # For this example, we assume AIInsightsDashboardView._get_sentiment_data_for_period is accessible
        # or we replicate its logic. To call it directly, we'd need an instance or make it static/module-level.
        # For simplicity, let's assume a module-level helper or re-implement briefly.
        # Re-instantiating the view to call its method is not ideal.
        # Better: Refactor _get_sentiment_data_for_period to be a standalone function.

        # For now, re-instantiating to use the method.
        # In a real scenario, refactor _get_sentiment_data_for_period to a utility function.
        dashboard_view_instance = AIInsightsDashboardView()
        chart_data = dashboard_view_instance._get_sentiment_data_for_period(user, time_period_value)
        
        logger.info(f"SentimentChartDataView: AJAX request for user {user.username}, period: {time_period_value}")
        return JsonResponse(chart_data)


class AIServiceStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    # ... (Your existing AIServiceStatusView code remains unchanged) ...
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
            current_task_api_status = "PENDING" 
            if not ai_enabled_by_user:
                current_task_api_status = "DISABLED_BY_USER"
                if not processed_flag_value: 
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
