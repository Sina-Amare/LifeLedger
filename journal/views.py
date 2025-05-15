# journal/views.py

from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    # DeleteView, # We will replace DeleteView with a custom View for Ajax delete
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponseForbidden # Import HttpResponseForbidden
from django.views import View # Import View

from .models import JournalEntry, JournalAttachment
from .forms import JournalEntryForm

class JournalEntryListView(LoginRequiredMixin, ListView):
    """
    Displays a list of all journal entries for the currently logged-in user.
    Requires user to be logged in.
    """
    model = JournalEntry
    template_name = 'journal/journal_list.html'
    context_object_name = 'journal_entries'

    def get_queryset(self):
        """
        Returns the queryset of journal entries filtered by the logged-in user.
        """
        return JournalEntry.objects.filter(user=self.request.user).order_by('-created_at')

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

class JournalEntryCreateView(LoginRequiredMixin, CreateView):
    """
    Provides a form to create a new journal entry.
    Requires user to be logged in.
    Uses the custom JournalEntryForm.
    """
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_form.html'

    def form_valid(self, form):
        """
        Sets the user of the journal entry to the currently logged-in user
        before saving the form.
        """
        form.instance.user = self.request.user
        # TODO: Handle file uploads here or in a separate form/view logic later
        # TODO: Trigger Celery tasks for AI processing after saving
        return super().form_valid(form)

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

    def get_success_url(self):
        """
        Redirects to the detail view of the updated journal entry
        upon successful update.
        """
        return reverse_lazy('journal:journal_detail', kwargs={'pk': self.object.pk})

    # TODO: Handle file uploads/deletions here or in a separate form/view logic later
    # TODO: Re-trigger Celery tasks for AI processing if content changes? (Decision needed)


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
            return HttpResponseForbidden("You do not have permission to delete this entry.")

        # If user is the owner, delete the entry
        try:
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

