from django import forms
from .models import JournalEntry, JournalAttachment, Tag
import os
import mimetypes
import re
import logging

logger = logging.getLogger(__name__)

MOOD_CHOICES_FORM_DISPLAY = [
    ('', 'Select Mood'),
    ('happy', '😊 Happy'),
    ('sad', '😢 Sad'),
    ('angry', '😠 Angry'),
    ('calm', '😌 Calm'),
    ('neutral', '😐 Neutral'),
    ('excited', '🎉 Excited'),
]

# --- NEW: Custom Widget and Field for Multiple File Uploads ---
class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget that allows multiple file selections."""
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    """Custom field that uses the MultipleFileInput widget."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class JournalEntryForm(forms.ModelForm):
    mood = forms.ChoiceField(
        choices=MOOD_CHOICES_FORM_DISPLAY, 
        required=False, 
        label="Your Current Mood",
        widget=forms.Select(attrs={'class': 'custom-select-arrow'})
    )

    tags = forms.CharField(
        required=False,
        label="Tags",
        help_text="Select from suggestions.",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Work, Personal, Ideas',
            'class': 'mt-1 block w-full px-3 py-2.5 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:placeholder-gray-500 sm:text-sm focus:ring-primary-light focus:border-primary-light'
        })
    )

    # ADDED: A dedicated field for new uploads. It's not tied to a model field.
    attachments = MultipleFileField(
        required=False,
        label="Add New Attachments",
        # We will style the label as a button, so the input itself is hidden.
        widget=MultipleFileInput(attrs={'multiple': True, 'class': 'hidden'})
    )

    class Meta:
        model = JournalEntry
        # IMPORTANT: The new 'attachments' field is added here to be included in the form.
        fields = ['title', 'content', 'mood', 'tags', 'attachments', 'location', 'privacy_level', 'is_favorite']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter a title for your entry (optional)'}),
            'content': forms.Textarea(attrs={'placeholder': 'Write your thoughts, feelings, and reflections here...', 'rows': 12}),
            'location': forms.TextInput(attrs={'placeholder': 'Where were you? (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'privacy_level' in self.fields and not self.fields['privacy_level'].widget.choices:
            self.fields['privacy_level'].choices = JournalEntry.PRIVACY_CHOICES
        
        if self.instance and self.instance.pk:
            initial_tag_names = [tag.name for tag in self.instance.tags.all().order_by('name')]
            self.initial['tags'] = ', '.join(initial_tag_names)
            if 'tags' in self.fields:
                self.fields['tags'].initial = self.initial['tags']

    def clean_tags(self):
        tags_string = self.cleaned_data.get('tags', '')
        if not tags_string.strip():
            return []

        raw_tag_names = [name.strip() for name in tags_string.split(',') if name.strip()]
        
        cleaned_and_validated_tags = []
        
        for name in raw_tag_names:
            if not name: 
                continue

            if len(name) > 50:
                raise forms.ValidationError(f"Tag \"{name[:50]}...\" is too long (max 50 characters).")
            
            if re.search(r"[<>()\[\]{}]", name): 
                raise forms.ValidationError(f"Tag \"{name}\" contains invalid characters (e.g., <, >, [, ], {{, }}). Please use letters, numbers, spaces, and hyphens.")
            
            if name.startswith('-') or name.endswith('-'):
                raise forms.ValidationError(f"Tag \"{name}\" cannot start or end with a hyphen.")

            if '--' in name:
                raise forms.ValidationError(f"Tag \"{name}\" cannot contain consecutive hyphens.")

            capitalized_name = ' '.join(word.capitalize() for word in name.replace('-', ' - ').split(' ')).replace(' - ', '-')
            
            if not capitalized_name: 
                continue
                
            cleaned_and_validated_tags.append(capitalized_name)
        
        return list(dict.fromkeys(cleaned_and_validated_tags))

# MODIFIED: This form is now only used to handle the deletion of existing files via the formset.
class JournalAttachmentForm(forms.ModelForm):
    class Meta:
        model = JournalAttachment
        fields = ['id'] # We only need the ID to identify instances and the DELETE checkbox.
        # The 'file' field is no longer needed here.
