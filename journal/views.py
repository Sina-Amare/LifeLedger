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
from .forms import JournalEntryForm, JournalAttachmentForm
from .models import JournalEntry, JournalAttachment
from django.db.models import Q
from django.utils import timezone
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Use inlineformset_factory to create a formset linked to JournalEntry
# This is used in the Create/Update views to manage attachments related to an entry.
JournalAttachmentInlineFormSet = inlineformset_factory(
    JournalEntry,  # Parent model: JournalEntry
    JournalAttachment,  # Child model: JournalAttachment
    form=JournalAttachmentForm,  # Use the form defined in forms.py for individual attachments
    extra=1,  # Start with one empty form for adding new attachments
    can_delete=True,  # Allow deleting existing attachments
    fields=['file'],  # Specify the fields to include from JournalAttachment model
    # max_num=5  # Optional: Limit the maximum number of attachments
)


class JournalEntryListView(LoginRequiredMixin, ListView):
    """
    Displays a list of journal entries for the logged-in user.
    Supports pagination, filtering, and searching.
    """
    model = JournalEntry
    template_name = 'journal/journal_list.html'
    context_object_name = 'entries'  # Name of the variable in the template
    paginate_by = 10  # Number of entries per page

    def get_queryset(self):
        """
        Return only the journal entries for the current logged-in user.
        Applies filtering and searching based on GET parameters.
        """
        queryset = JournalEntry.objects.filter(user=self.request.user)

        # Get filter parameters from the request
        mood = self.request.GET.get('mood')
        time_period = self.request.GET.get('time_period')
        is_favorite = self.request.GET.get('is_favorite')
        search_query = self.request.GET.get('q')

        # Apply mood filter
        if mood and mood != 'all': # 'all' or empty string means no mood filter
            queryset = queryset.filter(mood=mood)

        # Apply time period filter
        if time_period and time_period != 'all':
            now = timezone.now()
            if time_period == 'today':
                queryset = queryset.filter(created_at__date=now.date())
            elif time_period == 'this_week':
                # Start of the week (Monday)
                start_of_week = now.date() - timezone.timedelta(days=now.weekday())
                queryset = queryset.filter(created_at__date__gte=start_of_week)
            elif time_period == 'this_month':
                queryset = queryset.filter(created_at__year=now.year, created_at__month=now.month)
            elif time_period == 'this_year':
                queryset = queryset.filter(created_at__year=now.year)
            # Add more time periods as needed

        # Apply favorite filter
        if is_favorite == 'on':  # Checkbox value is 'on' when checked
            queryset = queryset.filter(is_favorite=True)

        # Apply search query
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(content__icontains=search_query)
            )
        
        return queryset.order_by('-created_at') # Ensure consistent ordering

    def get_context_data(self, **kwargs):
        """
        Add filter options and current filter values to the context
        for use in the template.
        """
        context = super().get_context_data(**kwargs)
        from .forms import JournalEntryForm # Import to get mood choices
        
        # Prepare mood options for the filter dropdown
        mood_options = [('', 'All Moods')] # Default "All Moods" option
        for value, label in JournalEntryForm.MOOD_CHOICES:
            if value != '': # Avoid adding the form's default 'Select Mood' if its value is empty
                mood_options.append((value,label))
        context['mood_options'] = mood_options
        
        # Time period options for the filter dropdown
        context['time_period_options'] = [
            ('all', 'All Time'),
            ('today', 'Today'),
            ('this_week', 'This Week'),
            ('this_month', 'This Month'),
            ('this_year', 'This Year'),
        ]

        # Pass current filter values to the template to pre-select options
        context['current_mood'] = self.request.GET.get('mood', '') # Default to empty to match 'All Moods'
        context['current_time_period'] = self.request.GET.get('time_period', 'all')
        context['current_is_favorite'] = self.request.GET.get('is_favorite') == 'on'
        context['current_search_query'] = self.request.GET.get('q', '')
        return context


class JournalEntryDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Displays the details of a single journal entry.
    Ensures only the owner can view the entry using UserPassesTestMixin.
    """
    model = JournalEntry
    template_name = 'journal/journal_detail.html'
    context_object_name = 'entry'

    def test_func(self):
        """
        Check if the logged-in user is the owner of the journal entry.
        Called by UserPassesTestMixin.
        """
        entry = self.get_object()
        return entry.user == self.request.user

    def get_queryset(self):
        """
        Override get_queryset to ensure that the DetailView only operates
        on entries belonging to the current user. This is an additional
        layer of security, complementing test_func.
        """
        return JournalEntry.objects.filter(user=self.request.user)


class JournalEntryCreateView(LoginRequiredMixin, CreateView):
    """
    Handles the creation of a new journal entry and its attachments.
    """
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'
    # success_url is set dynamically in form_valid via get_absolute_url

    def get_context_data(self, **kwargs):
        """
        Add the attachment formset to the context.
        """
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            # If it's a POST request, bind the formset with the POST data and files
            data['attachment_formset'] = JournalAttachmentInlineFormSet(self.request.POST, self.request.FILES, prefix='attachments')
        else:
            # If it's a GET request, create an empty formset
            data['attachment_formset'] = JournalAttachmentInlineFormSet(prefix='attachments')
        return data

    def form_valid(self, form):
        """
        Save the journal entry and its associated attachments.
        Uses a transaction to ensure atomicity (all or nothing).
        """
        context = self.get_context_data()
        attachment_formset = context['attachment_formset']

        if form.is_valid() and attachment_formset.is_valid():
            with transaction.atomic():
                # Assign the current user to the journal entry before saving
                form.instance.user = self.request.user
                # Save the main journal entry first
                self.object = form.save()

                # Associate the formset with the saved journal entry instance
                attachment_formset.instance = self.object
                attachment_formset.save()
                
                return redirect(self.object.get_absolute_url())
        else:
            # If either the main form or the formset is invalid, re-render the form with errors
            return self.render_to_response(self.get_context_data(form=form, attachment_formset=attachment_formset))

    def form_invalid(self, form):
        """
        Handle invalid form submission, ensuring formset is also passed back with errors.
        """
        # Re-initialize formset with POST data if available, and current instance if it's an update (though this is CreateView)
        attachment_formset = JournalAttachmentInlineFormSet(
            self.request.POST or None, 
            self.request.FILES or None, 
            prefix='attachments',
            instance=self.object if hasattr(self, 'object') and self.object else None # Should be None for CreateView
        )
        return self.render_to_response(self.get_context_data(form=form, attachment_formset=attachment_formset))


class JournalEntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Handles the updating of an existing journal entry and its attachments.
    Ensures only the owner can update the entry.
    """
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'
    context_object_name = 'entry'
    # success_url is set dynamically in form_valid via get_absolute_url

    def test_func(self):
        """
        Check if the logged-in user is the owner of the journal entry being updated.
        """
        entry = self.get_object()
        return entry.user == self.request.user

    def get_queryset(self):
        """
        Ensure only the user's entries can be fetched for update.
        """
        return JournalEntry.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        """
        Add the attachment formset to the context, populated with existing attachments.
        """
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['attachment_formset'] = JournalAttachmentInlineFormSet(
                self.request.POST,
                self.request.FILES,
                instance=self.object, # Pass the current journal entry instance
                prefix='attachments'
            )
        else:
            data['attachment_formset'] = JournalAttachmentInlineFormSet(instance=self.object, prefix='attachments')
        return data

    def form_valid(self, form):
        """
        Save the updated journal entry and its associated attachments.
        Handles adding new attachments and deleting marked attachments.
        Uses a transaction to ensure atomicity.
        """
        context = self.get_context_data()
        attachment_formset = context['attachment_formset']

        if form.is_valid() and attachment_formset.is_valid():
            with transaction.atomic():
                self.object = form.save() # User is already set, no need to set it again for update
                attachment_formset.instance = self.object
                attachment_formset.save()
                return redirect(self.object.get_absolute_url())
        else:
            return self.render_to_response(self.get_context_data(form=form, attachment_formset=attachment_formset))

    def form_invalid(self, form):
        """
        Handle invalid form submission for the update view, ensuring formset is also passed back with errors.
        """
        attachment_formset = JournalAttachmentInlineFormSet(
            self.request.POST or None, 
            self.request.FILES or None, 
            instance=self.object, # Crucial for update view
            prefix='attachments'
        )
        return self.render_to_response(self.get_context_data(form=form, attachment_formset=attachment_formset))


class JournalEntryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Handles the standard (non-Ajax) deletion of a journal entry.
    Ensures only the owner can delete the entry.
    """
    model = JournalEntry
    template_name = 'journal/journal_confirm_delete.html'
    success_url = reverse_lazy('journal:journal_list') # Redirect to the list view after deletion
    context_object_name = 'entry'

    def test_func(self):
        """
        Check if the logged-in user is the owner of the journal entry being deleted.
        """
        entry = self.get_object()
        return entry.user == self.request.user

    def get_queryset(self):
        """
        Ensure only the user's entries can be targeted for deletion.
        """
        return JournalEntry.objects.filter(user=self.request.user)


class JournalEntryAjaxDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Handles the deletion of a journal entry via Ajax POST requests.
    Returns a JSON response indicating success or failure.
    Ensures only the owner can delete the entry.
    The actual deletion logic is handled by overriding the post() method.
    """
    model = JournalEntry
    http_method_names = ['post'] # This view should only accept POST requests

    def test_func(self):
        """
        Check if the logged-in user is the owner of the journal entry.
        This is called by UserPassesTestMixin during the dispatch cycle.
        self.object is set by get_object() before this method is called.
        """
        entry = self.get_object() # self.get_object() fetches based on pk from URL and get_queryset()
        return entry.user == self.request.user

    def get_queryset(self):
        """
        Ensure get_object() only operates on entries belonging to the current user.
        """
        return JournalEntry.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        """
        Override post method to handle deletion and return JsonResponse directly.
        The UserPassesTestMixin and object retrieval (get_object)
        are handled by the parent classes' dispatch methods before this point.
        """
        try:
            # self.object should have been set by the time test_func was called,
            # or by DeleteView's dispatch mechanism.
            # If for some reason it's not (e.g., custom dispatch), ensure it's fetched.
            if not hasattr(self, 'object') or not self.object:
                 self.object = self.get_object() # This will raise Http404 if not found by pk in user's entries

            entry_pk = self.object.pk  # Store pk before deleting the object
            
            # Perform the deletion of the model instance
            self.object.delete()
            
            # Return a JSON response indicating success
            return JsonResponse({'status': 'success', 'message': 'Entry deleted successfully.', 'entry_id': entry_pk})
        
        except Http404:
            logger.warning(
                f"Ajax delete attempt for non-existent entry (pk={self.kwargs.get('pk')}) by user {request.user.id}.",
                exc_info=True # Include traceback in log
            )
            return JsonResponse({'status': 'error', 'message': 'Entry not found.'}, status=404)
        except PermissionDenied: # Should be caught by UserPassesTestMixin's dispatch
            logger.warning(
                f"Permission denied for Ajax delete by user {request.user.id} for entry pk={self.kwargs.get('pk')}.",
                exc_info=True
            )
            return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        except Exception as e:
            logger.error(
                f"Unexpected error in JournalEntryAjaxDeleteView for user {request.user.id}, entry pk={self.kwargs.get('pk')}: {e}",
                exc_info=True
            )
            return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)

    # Since we override post() to return JsonResponse,
    # success_url and get_success_url are not used by this view's Ajax response path.
