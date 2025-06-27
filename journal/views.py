from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, View, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.forms import inlineformset_factory
from django.db import transaction
from django.db.models import Q, Prefetch
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import logging

from .forms import JournalEntryForm, JournalAttachmentForm, MOOD_CHOICES_FORM_DISPLAY
from .models import JournalEntry, JournalAttachment, Tag
from .utils import MOOD_VISUALS, get_file_type # Import the new helper

from ai_services.tasks import (
    generate_quote_for_entry_task,
    detect_mood_for_entry_task,
    suggest_tags_for_entry_task,
)
from celery.result import AsyncResult
from user_profile.models import UserProfile

logger = logging.getLogger(__name__)

# MODIFIED: Formset now only handles deletion and has no extra forms.
JournalAttachmentInlineFormSet = inlineformset_factory(
    JournalEntry,
    JournalAttachment,
    form=JournalAttachmentForm,
    extra=0,  # No extra forms needed for new uploads.
    can_delete=True,
    fields=['id']
)

# --- Journal CRUD and related Views ---

class JournalEntryListView(LoginRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'journal/journal_list.html'
    context_object_name = 'entries'
    paginate_by = 10

    def get_queryset(self):
        # Prefetch image attachments specifically using the model method
        image_attachments_prefetch = Prefetch(
            'attachments',
            queryset=JournalAttachment.objects.filter(file_type='image').order_by('uploaded_at'),
            to_attr='image_attachments'
        )

        queryset = JournalEntry.objects.filter(user=self.request.user).prefetch_related(
            'tags', 
            image_attachments_prefetch  # Use the specific prefetch for images
        )
        
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

# A new base class to handle form processing logic for both Create and Update views
class JournalEntryFormMixin(object):
    def process_new_attachments(self, request, entry_instance):
        """Creates new attachment objects from the 'attachments' form field."""
        files = request.FILES.getlist('attachments')
        for uploaded_file in files:
            JournalAttachment.objects.create(
                journal_entry=entry_instance,
                file=uploaded_file,
                file_type=get_file_type(uploaded_file.name)
            )
        if files:
            logger.info(f"Created {len(files)} new attachments for entry {entry_instance.pk}.")

    def process_tags(self, form, entry_instance):
        """Converts tag strings from the form into Tag objects and sets them."""
        tag_names = form.cleaned_data.get('tags', [])
        tags_to_set = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name__iexact=name, defaults={'name': name})
            tags_to_set.append(tag)
        entry_instance.tags.set(tags_to_set)

class JournalEntryCreateView(LoginRequiredMixin, CreateView, JournalEntryFormMixin):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['predefined_tags'] = Tag.objects.all().order_by('name')
        data['initial_tags_str'] = ''
        return data

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()
        
        self.process_new_attachments(self.request, self.object)
        self.process_tags(form, self.object)
        
        self.schedule_ai_tasks(form)
        
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'entry_id': self.object.id,
                'task_ids': getattr(self, 'task_ids_dict', {}),
                'redirect_url': self.object.get_absolute_url()
            })
        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form):
        logger.error(f"Form invalid on create: {form.errors.as_json()}")
        return self.render_to_response(self.get_context_data(form=form))
        
    def schedule_ai_tasks(self, form):
        self.task_ids_dict = {}
        user_profile = self.request.user.profile
        
        if user_profile.ai_enable_quotes:
            quote_task = generate_quote_for_entry_task.apply_async(args=[self.object.id])
            self.object.ai_quote_task_id = quote_task.id
            self.task_ids_dict['quote_task_id'] = quote_task.id
        
        if user_profile.ai_enable_mood_detection and not form.cleaned_data.get('mood'):
            mood_task = detect_mood_for_entry_task.apply_async(args=[self.object.id])
            self.object.ai_mood_task_id = mood_task.id
            self.task_ids_dict['mood_task_id'] = mood_task.id
        else:
            self.object.ai_mood_processed = True
        
        if user_profile.ai_enable_tag_suggestion and not form.cleaned_data.get('tags'):
            tags_task = suggest_tags_for_entry_task.apply_async(args=[self.object.id])
            self.object.ai_tags_task_id = tags_task.id
            self.task_ids_dict['tags_task_id'] = tags_task.id
        else:
            self.object.ai_tags_processed = True
            
        self.object.save(update_fields=['ai_quote_task_id', 'ai_mood_task_id', 'ai_tags_task_id', 'ai_mood_processed', 'ai_tags_processed'])

class JournalEntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView, JournalEntryFormMixin):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'
    context_object_name = 'entry'

    def get_queryset(self):
        return JournalEntry.objects.filter(user=self.request.user).prefetch_related('tags', 'attachments')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if 'attachment_formset' not in data:
            data['attachment_formset'] = JournalAttachmentInlineFormSet(instance=self.object, prefix='attachments')
        data['predefined_tags'] = Tag.objects.all().order_by('name')
        if self.object and hasattr(self.object, 'tags'):
            data['initial_tags_str'] = ', '.join([tag.name for tag in self.object.tags.all().order_by('name')])
        return data
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        attachment_formset = JournalAttachmentInlineFormSet(request.POST, request.FILES, instance=self.object, prefix='attachments')

        if form.is_valid() and attachment_formset.is_valid():
            return self.form_valid(form, attachment_formset)
        return self.form_invalid(form, attachment_formset)

    @transaction.atomic
    def form_valid(self, form, attachment_formset):
        self.object = form.save(commit=False)
        
        # Process deletions first
        attachment_formset.save()
        
        self.process_new_attachments(self.request, self.object)
        
        self.schedule_ai_tasks_for_update(form)
        
        self.object.save()
        self.process_tags(form, self.object) # Process tags after potential clearing by AI logic
        
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'entry_id': self.object.id,
                'task_ids': getattr(self, 'task_ids_dict', {}),
                'redirect_url': self.object.get_absolute_url()
            })
        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form, attachment_formset):
        logger.error(f"Update form invalid: {form.errors.as_json()} | Formset: {attachment_formset.errors}")
        context = self.get_context_data(form=form, attachment_formset=attachment_formset)
        return self.render_to_response(context)

    def schedule_ai_tasks_for_update(self, form):
        self.task_ids_dict = {}
        user_profile = self.request.user.profile
        content_changed = 'content' in form.changed_data

        if content_changed:
            if user_profile.ai_enable_quotes:
                self.object.ai_quote_processed, self.object.ai_quote, self.object.ai_quote_task_id = False, None, None
                quote_task = generate_quote_for_entry_task.apply_async(args=[self.object.id])
                self.object.ai_quote_task_id, self.task_ids_dict['quote_task_id'] = quote_task.id, quote_task.id

            if user_profile.ai_enable_mood_detection and 'mood' not in form.changed_data:
                self.object.mood, self.object.ai_mood_processed, self.object.ai_mood_task_id = None, False, None
                mood_task = detect_mood_for_entry_task.apply_async(args=[self.object.id])
                self.object.ai_mood_task_id, self.task_ids_dict['mood_task_id'] = mood_task.id, mood_task.id

            if user_profile.ai_enable_tag_suggestion and 'tags' not in form.changed_data:
                self.object.tags.clear()
                self.object.ai_tags_processed, self.object.ai_tags_task_id = False, None
                tags_task = suggest_tags_for_entry_task.apply_async(args=[self.object.id])
                self.object.ai_tags_task_id, self.task_ids_dict['tags_task_id'] = tags_task.id, tags_task.id
        
        if 'tags' in form.changed_data:
            self.object.ai_tags_processed = True
            
    def test_func(self):
        return self.get_object().user == self.request.user


# The rest of the views (AIServiceStatusView, Delete views) remain unchanged.
# ... (omitted for brevity, but they should be kept in your file) ...
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
    http_method_names = ['post']

    def test_func(self):
        """
        This check runs before the view's dispatch method.
        """
        entry = get_object_or_404(JournalEntry, pk=self.kwargs.get('pk'))
        if entry.user != self.request.user:
            return False
        self.object = entry
        return True
    
    def handle_no_permission(self):
        """
        Customized to return a JSON 403 Forbidden error.
        """
        return JsonResponse({'status': 'error', 'message': _('Permission denied.')}, status=403)

    def post(self, request, *args, **kwargs):
        """
        Handles the actual deletion of the journal entry object.
        """
        try:
            entry_pk = self.object.pk
            entry_title = self.object.title or _("Untitled Entry")
            self.object.delete()
            logger.info(f"User '{request.user.username}' successfully deleted journal entry PK: {entry_pk}, Title: '{entry_title}' via AJAX.")
            return JsonResponse({'status': 'success', 'message': _('Entry deleted successfully.'), 'entry_id': entry_pk})
        except Exception as e:
            logger.error(f"Unexpected error in AJAX delete for PK {kwargs.get('pk')} for user '{request.user.username}': {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': _('An unexpected server error occurred.')}, status=500)
