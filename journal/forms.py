# journal/forms.py

from django import forms
from .models import JournalEntry, JournalAttachment, Tag
import os
import mimetypes
import re
import logging # Import the logging module

logger = logging.getLogger(__name__) # Get an instance of a logger

MOOD_CHOICES_FORM_DISPLAY = [
    ('', 'Select Mood'),
    ('happy', '😊 Happy'),
    ('sad', '😢 Sad'),
    ('angry', '😠 Angry'),
    ('calm', '😌 Calm'),
    ('neutral', '😐 Neutral'),
    ('excited', '🎉 Excited'),
]

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

    class Meta:
        model = JournalEntry
        fields = ['title', 'content', 'mood', 'tags', 'location', 'privacy_level', 'is_favorite']
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
    

class JournalAttachmentForm(forms.ModelForm):
    class Meta:
        model = JournalAttachment
        fields = ['file'] 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'file' in self.fields:
            self.fields['file'].widget.attrs.update({
                'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 transition duration-200 ease-in-out custom-file-input',
            })

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.cleaned_data.get('file') and hasattr(self.cleaned_data['file'], 'name'):
            uploaded_file = self.cleaned_data['file']
            filename = uploaded_file.name
            
            mime_type, _ = mimetypes.guess_type(filename)
            guessed_file_type = 'other'

            if mime_type:
                if mime_type.startswith('image'):
                    guessed_file_type = 'image'
                elif mime_type.startswith('audio'):
                    guessed_file_type = 'audio'
                elif mime_type.startswith('video'):
                    guessed_file_type = 'video'
            else: 
                ext = os.path.splitext(filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.avif']:
                    guessed_file_type = 'image'
                elif ext in ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']:
                    guessed_file_type = 'audio'
                elif ext in ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv']:
                    guessed_file_type = 'video'
            
            instance.file_type = guessed_file_type
            logger.info(f"Auto-detected file_type for '{filename}' as '{guessed_file_type}'. Mime: {mime_type}") # logger is now defined
        elif instance.pk and instance.file and not instance.file_type:
            filename = instance.file.name
            mime_type, _ = mimetypes.guess_type(filename)
            guessed_file_type = 'other'
            if mime_type:
                if mime_type.startswith('image'): guessed_file_type = 'image'
                elif mime_type.startswith('audio'): guessed_file_type = 'audio'
                elif mime_type.startswith('video'): guessed_file_type = 'video'
            else:
                ext = os.path.splitext(filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.avif']: guessed_file_type = 'image'
                elif ext in ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']: guessed_file_type = 'audio'
                elif ext in ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv']: guessed_file_type = 'video'
            instance.file_type = guessed_file_type
            logger.info(f"Updated missing file_type for existing attachment '{filename}' to '{guessed_file_type}'. Mime: {mime_type}")

        if commit:
            instance.save()
        return instance
