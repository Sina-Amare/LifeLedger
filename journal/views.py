# journal/views.py

from django.shortcuts import render, get_object_or_404, redirect # Import redirect
from django.urls import reverse_lazy, reverse # Import reverse
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponseForbidden
from django.views import View
from django.db.models import Q # Import Q object for complex lookups
from django.utils import timezone # Import timezone for date filtering
from datetime import timedelta # Import timedelta for date calculations


from .models import JournalEntry, JournalAttachment
from .forms import JournalEntryForm

class JournalEntryListView(LoginRequiredMixin, ListView):
    """
    Displays a list of all journal entries for the currently logged-in user.
    Supports filtering by mood, time period, and favorite status.
    Requires user to be logged in.
    """
    model = JournalEntry
    template_name = 'journal/journal_list.html'
    context_object_name = 'journal_entries'
    paginate_by = 10 # Optional: Add pagination later if needed

    def get_queryset(self):
        """
        Returns the queryset of journal entries filtered by the logged-in user
        and applies additional filters based on GET parameters.
        """
        queryset = JournalEntry.objects.filter(user=self.request.user).order_by('-created_at')

        # Get filter parameters from GET request
        mood = self.request.GET.get('mood')
        time_period = self.request.GET.get('time_period')
        is_favorite = self.request.GET.get('is_favorite') # 'on' or 'true' for checked

        # Apply mood filter
        if mood and mood != 'all': # Assuming 'all' is a value to show all moods
            queryset = queryset.filter(mood__iexact=mood) # Case-insensitive match

        # Apply time period filter
        if time_period:
            now = timezone.now()
            if time_period == 'today':
                queryset = queryset.filter(created_at__date=now.date())
            elif time_period == 'this_week':
                start_of_week = now - timedelta(days=now.weekday()) # Monday as start of week
                queryset = queryset.filter(created_at__date__gte=start_of_week.date())
            elif time_period == 'this_month':
                queryset = queryset.filter(created_at__year=now.year, created_at__month=now.month)
            elif time_period == 'this_year':
                queryset = queryset.filter(created_at__year=now.year)
            # Add more time periods as needed (e.g., 'last_7_days', 'last_30_days')
            elif time_period == 'last_7_days':
                 start_date = now - timedelta(days=7)
                 queryset = queryset.filter(created_at__date__gte=start_date.date())
            elif time_period == 'last_30_days':
                 start_date = now - timedelta(days=30)
                 queryset = queryset.filter(created_at__date__gte=start_date.date())


        # TODO: Add search functionality later (filtering by title or content)
        # search_query = self.request.GET.get('q')
        # if search_query:
        #     queryset = queryset.filter(Q(title__icontains=search_query) | Q(content__icontains=search_query))


        return queryset

    def get_context_data(self, **kwargs):
        """
        Adds filter options and current filter values to the context.
        """
        context = super().get_context_data(**kwargs)

        # Add filter options for the template
        # These could be fetched dynamically from the database for moods used
        # or defined as constants. For now, hardcode some examples.
        context['mood_options'] = [
            ('all', 'All Moods'),
            ('happy', 'Happy'),
            ('sad', 'Sad'),
            ('reflective', 'Reflective'),
            # Add more moods as needed
        ]

        context['time_period_options'] = [
            ('all', 'All Time'),
            ('today', 'Today'),
            ('this_week', 'This Week'),
            ('this_month', 'This Month'),
            ('this_year', 'This Year'),
            ('last_7_days', 'Last 7 Days'),
            ('last_30_days', 'Last 30 Days'),
        ]

        # Pass the current filter values back to the template to maintain state
        context['current_mood'] = self.request.GET.get('mood', 'all') # Default to 'all'
        context['current_time_period'] = self.request.GET.get('time_period', 'all') # Default to 'all'
        context['current_is_favorite'] = self.request.GET.get('is_favorite') # No default, check if present

        return context


class JournalEntryDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Displays the details of a single journal entry.
    Requires user to be logged in and to be the owner of the entry.
    """
    model = JournalEntry
    template_name = 'journal/journal_detail.html'
    context_object_name = 'journal_entry'

    def test_func(self):
        """
        Checks if the logged-in user is the owner of the journal entry.
        Required by UserPassesTestMixin.
        """
        journal_entry = self.get_object()
        return journal_entry.user == self.request.user

    def get_context_data(self, **kwargs):
        """
        Adds the list of attachments for the journal entry to the context.
        """
        context = super().get_context_data(**kwargs)
        context['attachments'] = self.object.attachments.all() # Fetch all attachments related to this entry
        return context


class JournalEntryCreateView(LoginRequiredMixin, CreateView):
    """
    Provides a form to create a new journal entry.
    Requires user to be logged in.
    Uses the custom JournalEntryForm.
    Handles file uploads.
    """
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'

    def form_valid(self, form):
        """
        Sets the user of the journal entry to the currently logged-in user
        before saving the form. Handles file upload.
        """
        # Save the journal entry first
        form.instance.user = self.request.user
        response = super().form_valid(form) # Saves the JournalEntry instance

        # Handle file upload after the journal entry is saved
        uploaded_file = form.cleaned_data.get('file')
        if uploaded_file:
            try:
                # Create a new JournalAttachment instance
                JournalAttachment.objects.create(
                    journal_entry=self.object, # Link to the newly created journal entry
                    file=uploaded_file
                )
                print(f"Successfully uploaded file: {uploaded_file.name} for entry {self.object.pk}")
            except Exception as e:
                # Log the error and potentially add a non-field error to the form
                # or show a message to the user on the next page.
                print(f"Error uploading file {uploaded_file.name}: {e}")
                # For simplicity now, just print the error.
                # In a real application, you might want more robust error handling.


        # TODO: Trigger Celery tasks for AI processing after saving

        return response # Redirects to get_success_url


    def get_success_url(self):
        """
        Redirects to the detail view of the newly created journal entry
        upon successful creation.
        """
        return reverse_lazy('journal:journal_detail', kwargs={'pk': self.object.pk})


class JournalEntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Provides a form to edit an existing journal entry.
    Requires user to be logged in and to be the owner of the entry.
    Uses the custom JournalEntryForm.
    Handles file uploads.
    """
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'

    def test_func(self):
        """
        Checks if the logged-in user is the owner of the journal entry.
        Required by UserPassesTestMixin.
        """
        journal_entry = self.get_object()
        return journal_entry.user == self.request.user

    def form_valid(self, form):
        """
        Handles saving the updated journal entry and file upload.
        """
        response = super().form_valid(form) # Saves the updated JournalEntry instance

        # Handle file upload for update view
        uploaded_file = form.cleaned_data.get('file')
        if uploaded_file:
            try:
                # Create a new JournalAttachment instance for the existing journal entry
                JournalAttachment.objects.create(
                    journal_entry=self.object, # Link to the existing journal entry
                    file=uploaded_file
                )
                print(f"Successfully uploaded file: {uploaded_file.name} for entry {self.object.pk}")
            except Exception as e:
                print(f"Error uploading file {uploaded_file.name}: {e}")
                # Handle error


        # TODO: Re-trigger Celery tasks for AI processing if content changes? (Decision needed)
        # TODO: Handle deletion of existing attachments (requires more form logic or separate view)

        return response # Redirects to get_success_url


    def get_success_url(self):
        """
        Redirects to the detail view of the updated journal entry
        upon successful update.
        """
        return reverse_lazy('journal:journal_detail', kwargs={'pk': self.object.pk})


# Custom View for handling Ajax Delete
class JournalEntryAjaxDeleteView(LoginRequiredMixin, View):
    """
    Handles deletion of a journal entry via Ajax POST request.
    Requires user to be logged in and to be the owner of the entry.
    GET requests to this URL are not allowed and will return 405 Method Not Allowed.
    """
    def post(self, request, pk, *args, **kwargs):
        """
        Handles the POST request for deletion (expected to be Ajax).
        Finds the object, checks permissions, deletes it, and returns JSON response.
        """
        # Ensure the request is Ajax (optional but good practice)
        # if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        #     return HttpResponseNotAllowed(['POST'], "Only Ajax POST requests are allowed.")

        # Get the journal entry object or return 404 if not found
        journal_entry = get_object_or_404(JournalEntry, pk=pk)

        # Check if the logged-in user is the owner of the entry
        if journal_entry.user != request.user:
            # Return 403 Forbidden if the user is not the owner
            return JsonResponse({'success': False, 'message': 'You do not have permission to delete this entry.'}, status=403) # Use JsonResponse for Ajax errors

        # If user is the owner, delete the entry
        try:
            # Deleting the JournalEntry will also delete related JournalAttachment instances
            # due to the ForeignKey's default ON DELETE CASCADE behavior.
            # However, the actual files on the filesystem might remain.
            # TODO: Implement logic to delete associated files from storage.
            journal_entry.delete()
            # Return a JSON response indicating success
            return JsonResponse({'success': True, 'entry_id': pk})
        except Exception as e:
            # Handle potential errors during deletion
            return JsonResponse({'success': False, 'message': f'Error deleting entry: {e}'}, status=500)


    def get(self, request, *args, **kwargs):
        """
        Handles GET requests. Returns 405 Method Not Allowed as GET delete is not supported.
        """
        return HttpResponseNotAllowed(['POST']) # Only POST is allowed for deletion

    # TODO: Handle deletion of associated files when deleting the entry

