# journal/forms.py

from django import forms
from .models import JournalEntry, JournalAttachment

class JournalEntryForm(forms.ModelForm):
    """
    Form for creating and updating JournalEntry instances.
    Includes fields for title, content, mood, location, and is_favorite.
    Adds a file upload field for attachments.
    """
    # Add a FileField to the form for uploading attachments
    # This will handle a single file upload for simplicity initially.
    # For multiple files, a Formset would be more appropriate later.
    file = forms.FileField(
        label="Attach a file (Optional)",
        required=False, # Make the file upload optional
        widget=forms.ClearableFileInput(attrs={'multiple': False}) # Allow only single file for now
    )

    # Define choices for the mood field
    # These should ideally come from a more central place or a Mood model later
    MOOD_CHOICES = [
        ('', 'Select Mood'), # Optional: Add a default empty choice
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
    # Use ChoiceField for dropdown, required=False because it's optional in the model
    mood = forms.ChoiceField(choices=MOOD_CHOICES, required=False, label="Mood")

    class Meta:
        model = JournalEntry
        # Include 'mood' and 'privacy_level' here, their widgets are defined below
        fields = ['title', 'content', 'mood', 'location', 'privacy_level', 'is_favorite'] # Keep the desired order

        # Add widgets with Tailwind classes for basic styling
        # We will ensure consistent focus classes directly in the HTML template now.
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-500 focus:outline-none focus:border-primary-light focus:ring-0 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:placeholder-gray-400 dark:focus:border-primary-dark sm:text-sm transition duration-200 ease-in-out',
                'placeholder': 'Enter title',
            }),
            'content': forms.Textarea(attrs={
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-500 focus:outline-none focus:border-primary-light focus:ring-0 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:placeholder-gray-400 dark:focus:border-primary-dark sm:text-sm transition duration-200 ease-in-out',
                'placeholder': 'Write your thoughts...',
                'rows': 8, # Adjust number of rows as needed
            }),
            # Added class attribute here for completeness, though HTML will override
            'mood': forms.Select(attrs={
                 # Removed class here to rely solely on HTML for consistency
                 # 'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:border-primary-light focus:ring-0 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:focus:border-primary-dark sm:text-sm appearance-none transition duration-200 ease-in-out',
            }),
             'location': forms.TextInput(attrs={
                 'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-500 focus:outline-none focus:border-primary-light focus:ring-0 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:placeholder-gray-400 dark:focus:border-primary-dark sm:text-sm transition duration-200 ease-in-out',
                 'placeholder': 'Where were you?',
            }),
             'is_favorite': forms.CheckboxInput(attrs={
                 'class': 'h-4 w-4 text-primary-light border-gray-300 rounded dark:bg-gray-700 dark:border-gray-600 dark:checked:bg-primary-dark dark:checked:border-primary-dark focus:ring-primary-light dark:focus:ring-primary-dark',
             }),
             # Added class attribute here for completeness, though HTML will override
             'privacy_level': forms.Select(attrs={
                 # Removed class here to rely solely on HTML for consistency
                 # 'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:border-primary-light focus:ring-0 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:focus:border-primary-dark sm:text-sm appearance-none transition duration-200 ease-in-out',
             }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # We don't need custom attributes like is_select/is_textarea for this HTML approach

        # Assign choices to the mood field in the form instance
        self.fields['mood'].choices = self.MOOD_CHOICES

        # Assign choices to the privacy_level field from the model
        self.fields['privacy_level'].choices = JournalEntry.PRIVACY_CHOICES

    # get_context method is not needed for this approach

