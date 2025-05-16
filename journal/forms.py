# journal/forms.py

from django import forms
# Import modelformset_factory for managing multiple attachment forms
from django.forms import modelformset_factory
from .models import JournalEntry, JournalAttachment # Import both models

class JournalEntryForm(forms.ModelForm):
    """
    Form for creating and updating JournalEntry instances.
    Includes fields for title, content, mood, location, is_favorite, and privacy_level.
    File uploads are handled separately by JournalAttachmentFormSet.
    """
    # Define choices for the mood field
    MOOD_CHOICES = [
        ('', 'Select Mood'),
        ('happy', 'Happy'),
        ('sad', 'Sad'),
        ('neutral', 'Neutral'),
        ('excited', 'Excited'),
        ('calm', 'Calm'),
        ('anxious', 'Anxious'),
        ('reflective', 'Reflective'),
        ('grateful', 'Grateful'),
        ('tired', 'Tired'),
        # Add more moods as needed
    ]
    mood = forms.ChoiceField(choices=MOOD_CHOICES, required=False, label="Mood")

    class Meta:
        model = JournalEntry
        # Exclude the 'file' field as attachments are handled by the formset
        fields = ['title', 'content', 'mood', 'location', 'privacy_level', 'is_favorite']

        # Add widgets with Tailwind classes for basic styling
        # We will ensure consistent focus classes directly in the HTML template now.
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-500 focus:outline-none focus:border-primary-light focus:ring-0 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:placeholder-gray-400 dark:focus:border-primary-dark sm:text-sm transition duration-200 ease-in-out',
                'placeholder': 'Enter title',
            }),
            'content': forms.Textarea(attrs={
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-500 focus:outline-none focus:border-primary-light focus:ring-0 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:placeholder-gray-400 sm:text-sm transition duration-200 ease-in-out',
                'placeholder': 'Write your thoughts...',
                'rows': 8, # Adjust number of rows as needed
            }),
            'mood': forms.Select(attrs={
                 # Removed class here to rely solely on HTML for consistency
                 # 'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:border-primary-light focus:ring-0 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:focus:border-primary-dark sm:text-sm appearance-none transition duration-200 ease-in-out',
            }),
             'location': forms.TextInput(attrs={
                 'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:placeholder-gray-400 dark:focus:border-primary-dark sm:text-sm transition duration-200 ease-in-out',
                 'placeholder': 'Where were you?',
            }),
             'is_favorite': forms.CheckboxInput(attrs={
                 'class': 'h-4 w-4 text-primary-light border-gray-300 rounded dark:bg-gray-700 dark:border-gray-600 dark:checked:bg-primary-dark dark:checked:border-primary-dark focus:ring-primary-light dark:focus:ring-primary-dark',
             }),
             'privacy_level': forms.Select(attrs={
                 # Removed class here to rely solely on HTML for consistency
                 # 'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:border-primary-light focus:ring-0 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:focus:border-primary-dark sm:text-sm appearance-none transition duration-200 ease-in-out',
             }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mood'].choices = self.MOOD_CHOICES
        self.fields['privacy_level'].choices = JournalEntry.PRIVACY_CHOICES


class JournalAttachmentForm(forms.ModelForm):
    """
    Form for managing a single JournalAttachment instance.
    Includes the file field and a checkbox for deletion.
    """
    class Meta:
        model = JournalAttachment
        # Include the file field and a field for marking for deletion
        fields = ['file'] # We only need the file field here

    # Add a checkbox for marking the attachment for deletion
    DELETE = forms.BooleanField(required=False, initial=False, label="Delete")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind classes to the file input for styling
        # Using a custom class for styling the file input button in HTML template
        self.fields['file'].widget.attrs.update({
            'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 transition duration-200 ease-in-out custom-file-input', # Added custom-file-input class
        })
        # Add Tailwind classes to the delete checkbox
        self.fields['DELETE'].widget.attrs.update({
             'class': 'h-4 w-4 text-red-600 border-gray-300 rounded focus:ring-red-500 dark:bg-gray-700 dark:border-gray-600 dark:checked:bg-red-600 dark:checked:border-red-600',
        })


# Create a formset for managing multiple JournalAttachment forms
# Note: We use modelformset_factory here in forms.py for general form definition.
# In views.py, we will use inlineformset_factory which is tied to the parent model.
JournalAttachmentFormSet = modelformset_factory(
    JournalAttachment,
    form=JournalAttachmentForm,
    extra=1, # Start with one empty form for adding new attachments
    can_delete=True, # Allow deleting existing attachments
    # max_num=5 # Optional: Limit the maximum number of attachments
)
