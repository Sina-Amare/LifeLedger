# journal/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, Http404
from django.core.exceptions import PermissionDenied
from django.forms import inlineformset_factory 
from django.db import transaction
from .forms import JournalEntryForm, JournalAttachmentForm, MOOD_CHOICES_FORM_DISPLAY 
from .models import JournalEntry, JournalAttachment, Tag
from django.db.models import Q
from django.utils import timezone
import logging

# Import the Celery tasks
from ai_services.tasks import (
    generate_quote_for_entry_task,
    detect_mood_for_entry_task,
    suggest_tags_for_entry_task
)
from LifeLedger.celery import debug_task # Import the debug_task

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
        queryset = JournalEntry.objects.filter(user=self.request.user).prefetch_related('tags')
        mood = self.request.GET.get('mood')
        time_period = self.request.GET.get('time_period')
        is_favorite = self.request.GET.get('is_favorite')
        search_query = self.request.GET.get('q')
        tag_filter_name = self.request.GET.get('tag_filter') 

        if mood and mood != '':
            queryset = queryset.filter(mood=mood)
        if time_period and time_period != 'all':
            now = timezone.now()
            if time_period == 'today': queryset = queryset.filter(created_at__date=now.date())
            elif time_period == 'this_week':
                start_of_week = now.date() - timezone.timedelta(days=now.weekday())
                queryset = queryset.filter(created_at__date__gte=start_of_week)
            elif time_period == 'this_month': queryset = queryset.filter(created_at__year=now.year, created_at__month=now.month)
            elif time_period == 'this_year': queryset = queryset.filter(created_at__year=now.year)
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
        context['mood_options'] = MOOD_CHOICES_FORM_DISPLAY 
        context['mood_visuals'] = MOOD_VISUALS
        
        context['time_period_options'] = [
            ('all', 'All Time'), ('today', 'Today'), ('this_week', 'This Week'),
            ('this_month', 'This Month'), ('this_year', 'This Year'),
        ]
        context['current_mood'] = self.request.GET.get('mood', '')
        context['current_time_period'] = self.request.GET.get('time_period', 'all')
        context['current_is_favorite'] = self.request.GET.get('is_favorite') == 'on'
        context['current_search_query'] = self.request.GET.get('q', '')
        
        user_entry_tags_pks = JournalEntry.objects.filter(user=self.request.user).values_list('tags__pk', flat=True).distinct()
        context['all_tags_for_filter'] = Tag.objects.filter(pk__in=[pk for pk in user_entry_tags_pks if pk is not None]).order_by('name')
        context['current_tag_filter'] = self.request.GET.get('tag_filter', '')
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
        if self.request.method == 'POST':
            data['attachment_formset'] = JournalAttachmentInlineFormSet(
                self.request.POST, self.request.FILES, prefix='attachments'
            )
        else: 
            data['attachment_formset'] = JournalAttachmentInlineFormSet(prefix='attachments')
        
        data['predefined_tags'] = Tag.objects.all().order_by('name')
        data['initial_tags_str'] = '' 
        return data

    def post(self, request, *args, **kwargs):
        self.object = None 
        form = self.get_form()
        attachment_formset = JournalAttachmentInlineFormSet(
            request.POST, request.FILES, prefix='attachments' 
        )
        if form.is_valid() and attachment_formset.is_valid():
            logger.info("Main form and attachment formset are valid for create.")
            return self.form_valid(form, attachment_formset)
        else:
            logger.error(f"Form or Formset invalid on POST. Form errors: {form.errors.as_json()}. Formset errors: {attachment_formset.errors} {attachment_formset.non_form_errors()}")
            return self.form_invalid(form, attachment_formset)

    def form_valid(self, form, attachment_formset):
        with transaction.atomic(): 
            form.instance.user = self.request.user
            self.object = form.save(commit=False) 
            self.object.save() 
            
            tag_names_list = form.cleaned_data.get('tags', []) 
            current_tags_for_entry = []
            if tag_names_list:
                for tag_name in tag_names_list:
                    tag_name_stripped = tag_name.strip()
                    if tag_name_stripped:
                        tag, created = Tag.objects.get_or_create(
                            name__iexact=tag_name_stripped, 
                            defaults={'name': tag_name_stripped.capitalize()} 
                        )
                        current_tags_for_entry.append(tag)
            self.object.tags.set(current_tags_for_entry)
            
            attachment_formset.instance = self.object
            attachment_formset.save()
            logger.info(f"JournalEntry {self.object.pk} created with attachments and tags.")

            entry_id = self.object.id
            # --- Dispatch AI Tasks ---
            logger.info(f"Attempting to dispatch AI tasks for entry ID: {entry_id}")
            try:
                debug_task.delay() # Call the simple debug task
                logger.info(f"Dispatched LifeLedger.celery.debug_task for entry ID: {entry_id}")
            except Exception as e:
                logger.error(f"Failed to dispatch debug_task (entry ID {entry_id}): {e}", exc_info=True)

            try:
                generate_quote_for_entry_task.delay(entry_id)
                logger.info(f"Dispatched generate_quote_for_entry_task for new entry ID: {entry_id}")
            except Exception as e:
                logger.error(f"Failed to dispatch generate_quote_for_entry_task (entry ID {entry_id}): {e}", exc_info=True)
            
            try:
                detect_mood_for_entry_task.delay(entry_id)
                logger.info(f"Dispatched detect_mood_for_entry_task for new entry ID: {entry_id}")
            except Exception as e:
                logger.error(f"Failed to dispatch detect_mood_for_entry_task (entry ID {entry_id}): {e}", exc_info=True)

            try:
                suggest_tags_for_entry_task.delay(entry_id)
                logger.info(f"Dispatched suggest_tags_for_entry_task for new entry ID: {entry_id}")
            except Exception as e:
                logger.error(f"Failed to dispatch suggest_tags_for_entry_task (entry ID {entry_id}): {e}", exc_info=True)
            
        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form, attachment_formset):
        logger.warning(f"CreateView form_invalid. Form errors: {form.errors.as_json()}")
        if attachment_formset and not attachment_formset.is_valid():
            logger.warning(f"  Attachment formset errors: {attachment_formset.errors} {attachment_formset.non_form_errors()}")
        return self.render_to_response(
            self.get_context_data(form=form, attachment_formset=attachment_formset)
        )

class JournalEntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'
    context_object_name = 'entry'

    def get_queryset(self):
        return JournalEntry.objects.filter(user=self.request.user).prefetch_related('tags')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.method == 'POST':
            data['attachment_formset'] = JournalAttachmentInlineFormSet(
                self.request.POST, self.request.FILES, instance=self.object, prefix='attachments'
            )
        else: 
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
        attachment_formset = JournalAttachmentInlineFormSet(
            request.POST, request.FILES, instance=self.object, prefix='attachments'
        )
        if form.is_valid() and attachment_formset.is_valid():
            logger.info(f"Main form and attachment formset are valid for update (entry ID: {self.object.pk}).")
            return self.form_valid(form, attachment_formset)
        else:
            if not form.is_valid(): logger.error(f"UpdateView - Main form invalid: {form.errors.as_json()}")
            if not attachment_formset.is_valid():
                logger.error(f"UpdateView - Attachment formset invalid: {attachment_formset.errors}")
                logger.error(f"UpdateView - Attachment formset non-form errors: {attachment_formset.non_form_errors()}")
            return self.form_invalid(form, attachment_formset)

    def form_valid(self, form, attachment_formset):
        with transaction.atomic():
            content_changed = False
            if form.has_changed() and 'content' in form.changed_data:
                content_changed = True
            
            mood_provided_by_user_in_this_update = 'mood' in form.changed_data and form.cleaned_data.get('mood')
            tags_provided_by_user_in_this_update = 'tags' in form.changed_data and form.cleaned_data.get('tags')

            self.object = form.save(commit=False)
            self.object.save()

            tag_names_list = form.cleaned_data.get('tags', [])
            current_tags_for_entry = []
            if tag_names_list:
                for tag_name in tag_names_list:
                    tag_name_stripped = tag_name.strip()
                    if tag_name_stripped:
                        tag, created = Tag.objects.get_or_create(
                            name__iexact=tag_name_stripped, 
                            defaults={'name': tag_name_stripped.capitalize()}
                        )
                        current_tags_for_entry.append(tag)
            self.object.tags.set(current_tags_for_entry)

            attachment_formset.instance = self.object
            attachment_formset.save()
            logger.info(f"JournalEntry {self.object.pk} and attachments updated.")

            entry_id = self.object.id
            # --- Dispatch AI Tasks for Update ---
            logger.info(f"Attempting to dispatch AI tasks for updated entry ID: {entry_id}")
            try:
                debug_task.delay() # Call the simple debug task
                logger.info(f"Dispatched LifeLedger.celery.debug_task for updated entry ID: {entry_id}")
            except Exception as e:
                logger.error(f"Failed to dispatch debug_task (updated entry ID {entry_id}): {e}", exc_info=True)

            if content_changed or not self.object.ai_quote:
                try:
                    generate_quote_for_entry_task.delay(entry_id)
                    logger.info(f"Dispatched generate_quote_for_entry_task for updated entry ID: {entry_id}")
                except Exception as e:
                    logger.error(f"Failed to dispatch quote task (updated entry ID {entry_id}): {e}", exc_info=True)
            
            if not mood_provided_by_user_in_this_update:
                try:
                    detect_mood_for_entry_task.delay(entry_id)
                    logger.info(f"Dispatched detect_mood_for_entry_task for updated entry ID: {entry_id}")
                except Exception as e:
                    logger.error(f"Failed to dispatch mood task (updated entry ID {entry_id}): {e}", exc_info=True)

            if not tags_provided_by_user_in_this_update:
                try:
                    suggest_tags_for_entry_task.delay(entry_id)
                    logger.info(f"Dispatched suggest_tags_for_entry_task for updated entry ID: {entry_id}")
                except Exception as e:
                    logger.error(f"Failed to dispatch tag task (updated entry ID {entry_id}): {e}", exc_info=True)
            
        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form, attachment_formset):
        logger.error(f"UpdateView.form_invalid. Form errors: {form.errors.as_json()}")
        if attachment_formset and not attachment_formset.is_valid():
            logger.error(f"  UpdateView - Attachment formset errors: {attachment_formset.errors}")
        return self.render_to_response(
            self.get_context_data(form=form, attachment_formset=attachment_formset)
        )

    def test_func(self):
        entry = self.get_object()
        return entry.user == self.request.user

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
        self.object = self.get_object() 
        return self.object.user == self.request.user

    def handle_no_permission(self):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Permission denied (handle_no_permission).'}, status=403)
        return super().handle_no_permission()

    def post(self, request, *args, **kwargs):
        try:
            if not hasattr(self, 'object') or not self.object:
                 self.object = self.get_object() 
            entry_pk = self.object.pk
            self.object.delete()
            return JsonResponse({'status': 'success', 'message': 'Entry deleted successfully.', 'entry_id': entry_pk})
        except Http404: 
            return JsonResponse({'status': 'error', 'message': 'Entry not found in POST.'}, status=404)
        except Exception as e:
            logger.error(f"Unexpected error in JournalEntryAjaxDeleteView POST for pk={kwargs.get('pk')}: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
