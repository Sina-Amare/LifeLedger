from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, View, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.forms import inlineformset_factory
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import logging

from .forms import JournalEntryForm, JournalAttachmentForm, MOOD_CHOICES_FORM_DISPLAY
from .models import JournalEntry, JournalAttachment, Tag
from .utils import MOOD_VISUALS

from ai_services.tasks import (
    generate_quote_for_entry_task,
    detect_mood_for_entry_task,
    suggest_tags_for_entry_task,
)
from celery.result import AsyncResult
from user_profile.models import UserProfile

logger = logging.getLogger(__name__)

# --- Formset Definition ---
JournalAttachmentInlineFormSet = inlineformset_factory(
    JournalEntry,
    JournalAttachment,
    form=JournalAttachmentForm,
    extra=1,
    can_delete=True,
    fields=['file']
)

# --- Journal CRUD and related Views ---

class JournalEntryListView(LoginRequiredMixin, ListView):
    """
    Handles the display of a paginated and filterable list of a user's journal entries.
    """
    model = JournalEntry
    template_name = 'journal/journal_list.html'
    context_object_name = 'entries'
    paginate_by = 10

    def get_queryset(self):
        """
        Builds the queryset for journal entries based on the current user and
        any active filters from the request's GET parameters.
        """
        queryset = JournalEntry.objects.filter(user=self.request.user).prefetch_related('tags', 'attachments')

        mood = self.request.GET.get('mood')
        time_period = self.request.GET.get('time_period')
        is_favorite = self.request.GET.get('is_favorite')
        search_query = self.request.GET.get('q')
        tag_filter_name = self.request.GET.get('tag_filter')

        if mood:
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
        """
        Adds necessary data for rendering filters and entry visuals to the context.
        """
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
    """
    Displays the details of a single journal entry, ensuring user ownership.
    """
    model = JournalEntry
    template_name = 'journal/journal_detail.html'
    context_object_name = 'entry'

    def test_func(self):
        """Check if the current user is the owner of the journal entry."""
        entry = self.get_object()
        return entry.user == self.request.user
    
    def get_queryset(self):
        """Ensure we only operate on the current user's entries."""
        return JournalEntry.objects.filter(user=self.request.user).prefetch_related('tags', 'attachments')

    def get_context_data(self, **kwargs):
        """Add mood visualization data to the context."""
        context = super().get_context_data(**kwargs)
        context['mood_visuals'] = MOOD_VISUALS
        return context

class JournalEntryCreateView(LoginRequiredMixin, CreateView):
    """
    Handles the creation of a new journal entry and its attachments.
    Schedules AI processing tasks upon successful creation.
    """
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'

    def get_context_data(self, **kwargs):
        """Prepare context data for the form, including the attachment formset."""
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
        """Handle POST request, validating both the entry form and the attachment formset."""
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
        """
        Process a valid form and formset. This includes saving objects and scheduling AI tasks.
        """
        with transaction.atomic():
            form.instance.user = self.request.user
            self.object = form.save(commit=False)
            
            self.object.ai_quote_processed = False
            self.object.ai_mood_processed = False
            self.object.ai_tags_processed = False
            self.object.ai_quote = None
            self.object.ai_quote_task_id = None
            self.object.ai_mood_task_id = None
            self.object.ai_tags_task_id = None
            
            self.object.save()
            
            tag_names_list = form.cleaned_data.get('tags', [])
            current_tags_for_entry = []
            if tag_names_list:
                for tag_name in tag_names_list:
                    tag_name_stripped = tag_name.strip()
                    if tag_name_stripped:
                        tag, was_created = Tag.objects.get_or_create(name__iexact=tag_name_stripped, defaults={'name': tag_name_stripped.capitalize()})
                        current_tags_for_entry.append(tag)
            self.object.tags.set(current_tags_for_entry)
            
            attachment_formset.instance = self.object
            attachment_formset.save()
            logger.info(f"JournalEntry {self.object.pk} created with attachments and tags.")

            entry_id = self.object.id
            task_ids_dict = {}
            user_profile = self.request.user.profile

            logger.info(f"Dispatching AI tasks for new entry {entry_id} based on user preferences.")
            
            if user_profile.ai_enable_quotes:
                quote_task = generate_quote_for_entry_task.apply_async(args=[entry_id])
                self.object.ai_quote_task_id = quote_task.id
                task_ids_dict['quote_task_id'] = quote_task.id
            
            if user_profile.ai_enable_mood_detection and not form.cleaned_data.get('mood'):
                mood_task = detect_mood_for_entry_task.apply_async(args=[entry_id])
                self.object.ai_mood_task_id = mood_task.id
                task_ids_dict['mood_task_id'] = mood_task.id
            else:
                self.object.ai_mood_processed = True
            
            if user_profile.ai_enable_tag_suggestion and not current_tags_for_entry:
                tags_task = suggest_tags_for_entry_task.apply_async(args=[entry_id])
                self.object.ai_tags_task_id = tags_task.id
                task_ids_dict['tags_task_id'] = tags_task.id
            else:
                self.object.ai_tags_processed = True

            self.object.save()

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success', 
                'message': _('Journal entry saved. AI processing scheduled.'),
                'entry_id': self.object.id,
                'task_ids': task_ids_dict, 
                'redirect_url': self.object.get_absolute_url()
            })
        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form, attachment_formset):
        """Handle cases where the form or formset is invalid."""
        logger.warning(f"CreateView form_invalid. Form errors: {form.errors.as_json()}")
        if attachment_formset and not attachment_formset.is_valid():
            logger.warning(f"Attachment formset errors: {attachment_formset.errors} {attachment_formset.non_form_errors()}")
        
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error', 
                'form_errors': form.errors.as_json(), 
                'formset_errors': attachment_formset.errors if attachment_formset else None
            }, status=400)
        return self.render_to_response(self.get_context_data(form=form, attachment_formset=attachment_formset))

class JournalEntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Handles updates to an existing journal entry and its related objects.
    Re-schedules AI tasks if relevant content has changed.
    """
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'
    context_object_name = 'entry'

    def get_queryset(self):
        """Ensures the user can only update their own entries."""
        return JournalEntry.objects.filter(user=self.request.user).prefetch_related('tags')

    def get_context_data(self, **kwargs):
        """Prepare context data for the update form."""
        data = super().get_context_data(**kwargs)
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
        """Handle POST request for updating the entry."""
        self.object = self.get_object()
        form = self.get_form()
        attachment_formset = JournalAttachmentInlineFormSet(request.POST, request.FILES, instance=self.object, prefix='attachments')
        if form.is_valid() and attachment_formset.is_valid():
            return self.form_valid(form, attachment_formset)
        else:
            return self.form_invalid(form, attachment_formset)

    def form_valid(self, form, attachment_formset):
        """
        Process the valid form, re-scheduling AI tasks if content has changed,
        respecting manual edits by the user.
        """
        with transaction.atomic():
            content_changed = 'content' in form.changed_data
            mood_manually_edited = 'mood' in form.changed_data
            tags_manually_edited = 'tags' in form.changed_data

            self.object = form.save(commit=False)
            
            user_profile = self.request.user.profile
            task_ids_dict = {}

            should_run_ai_for_quote = False
            should_run_ai_for_mood = False
            should_run_ai_for_tags = False

            if content_changed:
                if user_profile.ai_enable_quotes:
                    logger.info(f"Content changed for entry {self.object.pk}. Resetting for AI quote.")
                    self.object.ai_quote_processed = False
                    self.object.ai_quote = None
                    self.object.ai_quote_task_id = None
                    should_run_ai_for_quote = True

                if user_profile.ai_enable_mood_detection and not mood_manually_edited:
                    logger.info(f"Content changed, mood not manually set. Resetting for AI mood detection.")
                    self.object.mood = None 
                    self.object.ai_mood_processed = False
                    self.object.ai_mood_task_id = None
                    should_run_ai_for_mood = True
                
                if user_profile.ai_enable_tag_suggestion and not tags_manually_edited:
                    logger.info(f"Content changed, tags not manually set. Resetting for AI tag suggestion.")
                    self.object.ai_tags_processed = False
                    self.object.ai_tags_task_id = None
                    should_run_ai_for_tags = True
            
            # This logic needs to run whether content changed or not.
            if tags_manually_edited:
                logger.info(f"Tags were manually edited for entry {self.object.pk}. Applying them now.")
                tag_names_list = form.cleaned_data.get('tags', [])
                tags_to_set = []
                for tag_name in tag_names_list:
                    tag_name_stripped = tag_name.strip()
                    if tag_name_stripped:
                        # FINAL FIX: Changed '_' to 'was_created'
                        tag, was_created = Tag.objects.get_or_create(name__iexact=tag_name_stripped, defaults={'name': tag_name_stripped.capitalize()})
                        tags_to_set.append(tag)
                self.object.tags.set(tags_to_set)
                self.object.ai_tags_processed = True
            elif should_run_ai_for_tags:
                logger.info(f"Clearing tags for entry {self.object.pk} before AI suggestion.")
                self.object.tags.clear()
            
            self.object.save()
            
            attachment_formset.instance = self.object
            attachment_formset.save()
            logger.info(f"JournalEntry {self.object.pk} and attachments updated.")

            # --- Dispatch AI Tasks ---
            entry_id = self.object.id
            if should_run_ai_for_quote:
                quote_task = generate_quote_for_entry_task.apply_async(args=[entry_id])
                self.object.ai_quote_task_id = quote_task.id
                task_ids_dict['quote_task_id'] = quote_task.id
            
            if should_run_ai_for_mood:
                mood_task = detect_mood_for_entry_task.apply_async(args=[entry_id])
                self.object.ai_mood_task_id = mood_task.id
                task_ids_dict['mood_task_id'] = mood_task.id
            
            if should_run_ai_for_tags:
                tags_task = suggest_tags_for_entry_task.apply_async(args=[entry_id])
                self.object.ai_tags_task_id = tags_task.id
                task_ids_dict['tags_task_id'] = tags_task.id
            
            if task_ids_dict:
                self.object.save(update_fields=['ai_quote_task_id', 'ai_mood_task_id', 'ai_tags_task_id'])

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success', 
                'message': _('Journal entry updated. AI processing scheduled as needed.'),
                'entry_id': self.object.id,
                'task_ids': task_ids_dict,
                'redirect_url': self.object.get_absolute_url()
            })
        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form, attachment_formset):
        """Handle invalid form or formset during an update."""
        logger.error(f"UpdateView form_invalid. Form errors: {form.errors.as_json()}")
        if attachment_formset and not attachment_formset.is_valid():
            logger.error(f"UpdateView - Attachment formset errors: {attachment_formset.errors}")
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'form_errors': form.errors.as_json(), 'formset_errors': attachment_formset.errors}, status=400)
        return self.render_to_response(self.get_context_data(form=form, attachment_formset=attachment_formset))

    def test_func(self):
        """Ensure the user owns the entry they are trying to update."""
        entry = self.get_object()
        return entry.user == self.request.user

class AIServiceStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Checks the status of individual AI processing tasks (quote, mood, tags) for a single journal entry.
    Used for the progress modal after creating or updating an entry.
    """
    def test_func(self):
        """Ensures that the request is made by the owner of the journal entry."""
        try:
            entry_id = self.kwargs.get('entry_id') 
            if not entry_id:
                return False
            entry = JournalEntry.objects.get(pk=entry_id)
            return entry.user == self.request.user
        except JournalEntry.DoesNotExist:
            return False 
        except Exception as e: 
            logger.error(f"AIServiceStatusView.test_func: Unexpected error for entry_id {self.kwargs.get('entry_id')}: {e}", exc_info=True)
            return False

    def get(self, request, entry_id, *args, **kwargs):
        """Handles GET requests to check the status of various AI tasks related to an entry."""
        entry = get_object_or_404(JournalEntry, pk=entry_id, user=request.user)

        statuses = {}
        needs_db_update_flags = [] 
        user_profile = request.user.profile

        task_info_map = {
            'quote': (entry.ai_quote_task_id, entry.ai_quote_processed, 'ai_quote_processed', user_profile.ai_enable_quotes),
            'mood': (entry.ai_mood_task_id, entry.ai_mood_processed, 'ai_mood_processed', user_profile.ai_enable_mood_detection),
            'tags': (entry.ai_tags_task_id, entry.ai_tags_processed, 'ai_tags_processed', user_profile.ai_enable_tag_suggestion),
        }
        
        for task_type, (task_id, is_processed, processed_field, is_enabled) in task_info_map.items():
            current_status = "PENDING"
            if not is_enabled:
                current_status = "DISABLED_BY_USER"
            elif is_processed:
                current_status = "SUCCESS"
            elif task_id:
                task_result = AsyncResult(task_id)
                current_status = task_result.state.upper()
                if task_result.failed():
                    current_status = "FAILURE"
                
                if task_result.ready() and not is_processed:
                    setattr(entry, processed_field, True)
                    needs_db_update_flags.append(processed_field)

            statuses[f'{task_type}_status'] = current_status

        if needs_db_update_flags:
            entry.save(update_fields=list(set(needs_db_update_flags)))
            logger.info(f"Updated AI processed flags for entry {entry.id} via status check: {needs_db_update_flags}")

        all_done = all(
            statuses[f'{task_type}_status'] in ["SUCCESS", "DISABLED_BY_USER", "FAILURE"]
            for task_type in task_info_map
        )

        return JsonResponse({
            'status': 'ok',
            'entry_id': entry.id,
            'task_statuses': statuses,
            'all_done': all_done,
            'ai_quote': entry.ai_quote if user_profile.ai_enable_quotes else "", 
            'mood': entry.mood, 
            'tags': [tag.name for tag in entry.tags.all()]
        })

class JournalEntryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Handles the standard (non-AJAX) deletion of a journal entry."""
    model = JournalEntry
    template_name = 'journal/journal_confirm_delete.html'
    success_url = reverse_lazy('journal:journal_list')
    context_object_name = 'entry'

    def test_func(self):
        """Checks if the request user is the owner of the entry."""
        entry = self.get_object()
        return entry.user == self.request.user

    def get_queryset(self):
        """Ensures that users can only delete their own entries."""
        return JournalEntry.objects.filter(user=self.request.user)

class JournalEntryAjaxDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Handles the deletion of a journal entry using an AJAX POST request. This provides
    a smoother user experience by not requiring a full page reload.
    """
    http_method_names = ['post']

    def test_func(self):
        """
        This check runs before the view's dispatch method.
        It ensures that the user attempting to access this view is the actual
        owner of the journal entry. It fetches the object once and attaches it
        to the view instance (`self.object`) so we don't have to fetch it again.
        """
        entry = get_object_or_404(JournalEntry, pk=self.kwargs.get('pk'))
        if entry.user != self.request.user:
            return False
        self.object = entry
        return True
    
    def handle_no_permission(self):
        """
        If the test_func returns False, this method is called.
        It's customized to return a JSON 403 Forbidden error, which is more
        appropriate for an AJAX call than the default HTML redirect.
        """
        return JsonResponse({'status': 'error', 'message': _('Permission denied.')}, status=403)

    def post(self, request, *args, **kwargs):
        """
        Handles the actual deletion of the journal entry object.
        This method is only called if the test_func check passes.
        """
        try:
            # The object is already available as self.object thanks to test_func
            entry_pk = self.object.pk
            entry_title = self.object.title or _("Untitled Entry")
            
            # The delete() method on the model instance handles the deletion.
            self.object.delete()
            
            logger.info(f"User '{request.user.username}' successfully deleted journal entry PK: {entry_pk}, Title: '{entry_title}' via AJAX.")
            
            # Return a success response to the frontend.
            return JsonResponse({'status': 'success', 'message': _('Entry deleted successfully.'), 'entry_id': entry_pk})
        
        except Exception as e:
            # A general catch-all for any other unexpected errors during deletion.
            logger.error(f"Unexpected error in AJAX delete for PK {kwargs.get('pk')} for user '{request.user.username}': {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': _('An unexpected server error occurred.')}, status=500)
