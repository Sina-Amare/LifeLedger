# journal/views.py

from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import JournalEntry, JournalAttachment
from .forms import JournalEntryForm # Import the custom form

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
    form_class = JournalEntryForm # Use the custom form
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
    form_class = JournalEntryForm # Use the custom form
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


class JournalEntryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Provides a confirmation page to delete a journal entry and handles deletion.
    Requires user to be logged in and to be the owner of the entry.
    """
    model = JournalEntry
    template_name = 'journal/journal_confirm_delete.html'
    context_object_name = 'journal_entry'
    success_url = reverse_lazy('journal:journal_list')

    def test_func(self):
        """
        Checks if the logged-in user is the owner of the journal entry.
        Required by UserPassesTestMixin.
        """
        journal_entry = self.get_object()
        return journal_entry.user == self.request.user

    # TODO: Handle deletion of associated files when deleting the entry

