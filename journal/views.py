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
from django.forms import inlineformset_factory # Correct import
from django.db import transaction
from .forms import JournalEntryForm, JournalAttachmentForm
from .models import JournalEntry, JournalAttachment
from django.db.models import Q
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

JournalAttachmentInlineFormSet = inlineformset_factory(
    JournalEntry,
    JournalAttachment,
    form=JournalAttachmentForm,
    extra=1, # Number of empty forms to display
    can_delete=True,
    fields=['file']
)


class JournalEntryListView(LoginRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'journal/journal_list.html'
    context_object_name = 'entries'
    paginate_by = 10

    def get_queryset(self):
        queryset = JournalEntry.objects.filter(user=self.request.user)
        mood = self.request.GET.get('mood')
        time_period = self.request.GET.get('time_period')
        is_favorite = self.request.GET.get('is_favorite')
        search_query = self.request.GET.get('q')

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
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(content__icontains=search_query)
            )
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mood_options_from_form = JournalEntryForm.MOOD_CHOICES
        processed_mood_options = []
        has_all_moods_option = False
        for value, label in mood_options_from_form:
            if value == '':
                processed_mood_options.append(('', 'All Moods')) 
                has_all_moods_option = True
            else:
                processed_mood_options.append((value, label))
        if not has_all_moods_option:
            processed_mood_options.insert(0, ('', 'All Moods'))
        
        context['mood_options'] = processed_mood_options
        
        context['time_period_options'] = [
            ('all', 'All Time'), ('today', 'Today'), ('this_week', 'This Week'),
            ('this_month', 'This Month'), ('this_year', 'This Year'),
        ]
        context['current_mood'] = self.request.GET.get('mood', '')
        context['current_time_period'] = self.request.GET.get('time_period', 'all')
        context['current_is_favorite'] = self.request.GET.get('is_favorite') == 'on'
        context['current_search_query'] = self.request.GET.get('q', '')
        return context

class JournalEntryDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = JournalEntry
    template_name = 'journal/journal_detail.html'
    context_object_name = 'entry'

    def test_func(self):
        entry = self.get_object()
        return entry.user == self.request.user
    
    def get_queryset(self):
        return JournalEntry.objects.filter(user=self.request.user)

class JournalEntryCreateView(LoginRequiredMixin, CreateView):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if 'attachment_formset' not in kwargs: # If not passed from post method
            if self.request.POST:
                data['attachment_formset'] = JournalAttachmentInlineFormSet(
                    self.request.POST, self.request.FILES, prefix='attachments'
                )
            else:
                data['attachment_formset'] = JournalAttachmentInlineFormSet(prefix='attachments')
        else: # If passed from post method (e.g. on form_invalid)
            data['attachment_formset'] = kwargs['attachment_formset']
        return data

    def post(self, request, *args, **kwargs):
        self.object = None # Required for CreateView
        form = self.get_form() # Main JournalEntryForm
        attachment_formset = JournalAttachmentInlineFormSet(
            request.POST, request.FILES, prefix='attachments'
        )

        logger.info(f"CreateView POST. CONTENT_TYPE: {request.META.get('CONTENT_TYPE')}")
        logger.info(f"CreateView POST. request.POST keys: {list(request.POST.keys())}")
        logger.info(f"CreateView POST. request.FILES keys: {list(request.FILES.keys())}")
        for key, uploaded_file in request.FILES.items():
            logger.info(f"  File in request.FILES (from post): key='{key}', name='{uploaded_file.name}', size={uploaded_file.size}")

        form_is_valid = form.is_valid()
        formset_is_valid = attachment_formset.is_valid()

        logger.info(f"In POST: Main form is_valid: {form_is_valid}")
        logger.info(f"In POST: Attachment formset is_valid: {formset_is_valid}")
        
        if not form_is_valid:
            logger.error(f"In POST: Main form errors: {form.errors.as_json()}")
        if not formset_is_valid:
            logger.error(f"In POST: Attachment formset errors: {attachment_formset.errors}")
            logger.error(f"In POST: Attachment formset non-form errors: {attachment_formset.non_form_errors()}")
            for i, sub_form in enumerate(attachment_formset.forms):
                if sub_form.errors:
                    logger.error(f"In POST: Errors in formset form #{i} ({sub_form.prefix}): {sub_form.errors.as_json()}")

        if form_is_valid and formset_is_valid:
            return self.form_valid(form, attachment_formset) # Pass both to form_valid
        else:
            return self.form_invalid(form, attachment_formset) # Pass both to form_invalid

    def form_valid(self, form, attachment_formset): # Accepts attachment_formset
        logger.info("CreateView.form_valid entered (with formset).")
        with transaction.atomic():
            form.instance.user = self.request.user
            self.object = form.save() # Save the main object
            logger.info(f"JournalEntry object saved with pk: {self.object.pk}")
            
            # Link formset to the saved object and save the formset
            attachment_formset.instance = self.object
            logger.info(f"Set attachment_formset.instance to JournalEntry pk: {self.object.pk}")
            try:
                saved_attachments = attachment_formset.save()
                logger.info(f"attachment_formset.save() called. Returned: {saved_attachments}")
                db_attachments = JournalAttachment.objects.filter(journal_entry=self.object)
                logger.info(f"Attachments found in DB for entry {self.object.pk}: {db_attachments.count()} - {list(db_attachments)}")
            except Exception as e:
                logger.error(f"Error during attachment_formset.save(): {e}", exc_info=True)
            
            return redirect(self.object.get_absolute_url())

    def form_invalid(self, form, attachment_formset): # Accepts attachment_formset
        logger.error(f"CreateView.form_invalid called. Main form errors: {form.errors.as_json()}")
        # Log formset errors if any (already logged in post, but good for clarity)
        if not attachment_formset.is_valid():
            logger.error(f"Attachment formset (in form_invalid) errors: {attachment_formset.errors}")
        return self.render_to_response(
            self.get_context_data(form=form, attachment_formset=attachment_formset)
        )

# ... (The rest of your views.py: JournalEntryUpdateView, JournalEntryDeleteView, JournalEntryAjaxDeleteView) ...
class JournalEntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'
    context_object_name = 'entry'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if 'attachment_formset' not in kwargs: # If not passed from post method
            if self.request.POST:
                data['attachment_formset'] = JournalAttachmentInlineFormSet(
                    self.request.POST, self.request.FILES, instance=self.object, prefix='attachments'
                )
            else:
                data['attachment_formset'] = JournalAttachmentInlineFormSet(instance=self.object, prefix='attachments')
        else:
            data['attachment_formset'] = kwargs['attachment_formset']
        return data

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() # Get object for UpdateView
        form = self.get_form()
        attachment_formset = JournalAttachmentInlineFormSet(
            request.POST, request.FILES, instance=self.object, prefix='attachments'
        )

        logger.info(f"UpdateView POST. request.FILES keys: {list(request.FILES.keys())}")

        if form.is_valid() and attachment_formset.is_valid():
            return self.form_valid(form, attachment_formset)
        else:
            return self.form_invalid(form, attachment_formset)

    def form_valid(self, form, attachment_formset):
        logger.info("UpdateView.form_valid entered.")
        with transaction.atomic():
            self.object = form.save()
            attachment_formset.instance = self.object # Ensure instance is set before saving formset
            attachment_formset.save()
            logger.info(f"JournalEntry {self.object.pk} and attachments updated.")
        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form, attachment_formset):
        logger.error(f"UpdateView.form_invalid. Form errors: {form.errors.as_json()}")
        if not attachment_formset.is_valid():
            logger.error(f"UpdateView.form_invalid. Formset errors: {attachment_formset.errors}")
        return self.render_to_response(
            self.get_context_data(form=form, attachment_formset=attachment_formset)
        )

    def test_func(self): # For UserPassesTestMixin
        entry = self.get_object()
        return entry.user == self.request.user

    def get_queryset(self): # For UserPassesTestMixin and get_object
        return JournalEntry.objects.filter(user=self.request.user)


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
                logger.info(f"AJAX Http404 caught in dispatch for pk={kwargs.get('pk')}")
                return JsonResponse({'status': 'error', 'message': 'Entry not found (dispatch).'}, status=404)
            raise
        except PermissionDenied: 
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                logger.info(f"AJAX PermissionDenied caught in dispatch for pk={kwargs.get('pk')}")
                return JsonResponse({'status': 'error', 'message': 'Permission denied (dispatch).'}, status=403)
            raise

    def test_func(self):
        self.object = self.get_object() 
        return self.object.user == self.request.user

    def handle_no_permission(self):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            logger.info(f"AJAX handle_no_permission called for pk={self.kwargs.get('pk')}")
            return JsonResponse({'status': 'error', 'message': 'Permission denied (handle_no_permission).'}, status=403)
        return super().handle_no_permission()

    def post(self, request, *args, **kwargs):
        try:
            if not hasattr(self, 'object') or not self.object: # Should be set by dispatch
                 self.object = self.get_object() 

            entry_pk = self.object.pk
            self.object.delete() # Triggers overridden JournalEntry.delete()
            return JsonResponse({'status': 'success', 'message': 'Entry deleted successfully.', 'entry_id': entry_pk})
        except Http404: 
            logger.warning(f"Http404 in POST for Ajax delete for pk={kwargs.get('pk')}", exc_info=False)
            return JsonResponse({'status': 'error', 'message': 'Entry not found in POST.'}, status=404)
        except Exception as e:
            logger.error(f"Unexpected error in JournalEntryAjaxDeleteView POST for pk={kwargs.get('pk')}: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
