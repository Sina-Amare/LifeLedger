# journal/forms.py

from django import forms
from .models import JournalEntry
from django.core.exceptions import ValidationError

# Define Tailwind classes here for reference, they will be applied in the template.
TAILWIND_INPUT_CLASSES = "block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:placeholder-gray-400 dark:focus:ring-2 dark:focus:ring-primary-dark dark:focus:border-transparent sm:text-sm transition duration-200 ease-in-out"
TAILWIND_TEXTAREA_CLASSES = "block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:placeholder-gray-400 dark:focus:ring-2 dark:focus:ring-primary-dark dark:focus:border-transparent sm:text-sm transition duration-200 ease-in-out"
TAILWIND_SELECT_CLASSES = "block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:focus:ring-2 dark:focus:ring-primary-dark dark:focus:border-transparent sm:text-sm appearance-none transition duration-200 ease-in-out"
TAILWIND_CHECKBOX_CLASSES = "h-4 w-4 text-primary-light border-gray-300 rounded dark:bg-gray-700 dark:border-gray-600 dark:checked:bg-primary-dark dark:checked:border-primary-dark focus:ring-primary-light dark:focus:ring-primary-dark"


class JournalEntryForm(forms.ModelForm):
    """
    Custom ModelForm for JournalEntry model.
    Adds widget type name to each field for easier template rendering.
    Does NOT apply Tailwind CSS classes here. Classes will be applied in the template.
    """
    class Meta:
        model = JournalEntry
        fields = [
            'title',
            'content',
            'mood',
            'location',
            'privacy_level',
            'shared_details',
            'is_favorite'
        ]
        # No custom widgets defined here, Django will use defaults.
        # widgets = { ... }

    def __init__(self, *args, **kwargs):
        """
        Initializes the form and adds a 'widget_type_name' attribute
        to each field's bound_field for template use.
        """
        super().__init__(*args, **kwargs)
        # Iterate over each field in the form
        for field_name, field in self.fields.items():
            # Get the bound field (which includes the widget)
            bound_field = self[field_name]
            # Add a new attribute 'widget_type_name' to the bound field
            # This attribute stores the name of the widget class as a string
            # This is safe to access in templates as it doesn't use __class__ directly
            setattr(bound_field, 'widget_type_name', field.widget.__class__.__name__)

    # You might want to add custom validation here later if needed
    # def clean_content(self):
    #     content = self.cleaned_data.get('content')
    #     if not content and not self.cleaned_data.get('title'):
    #         raise ValidationError("You must provide content or a title.")
    #     return content

    # Note: For the 'shared_details' JSONField, a simple Textarea for raw JSON
    # might not be user-friendly. In the future, you might need a custom widget
    # or a separate formset/inline form to manage these details more visually.

