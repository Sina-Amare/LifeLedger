# journal/forms.py

from django import forms
# from django.forms import modelformset_factory # Not actively used for inline formsets
from .models import JournalEntry, JournalAttachment

class JournalEntryForm(forms.ModelForm):
    """
    Form for creating and updating JournalEntry instances.
    """
    MOOD_CHOICES = [
        ('', 'Select Mood'), # Default empty choice
        ('happy', 'Happy'),
        ('sad', 'Sad'),
        ('neutral', 'Neutral'),
        ('excited', 'Excited'),
        ('calm', 'Calm'),
        ('anxious', 'Anxious'),
        ('reflective', 'Reflective'),
        ('grateful', 'Grateful'),
        ('tired', 'Tired'),
    ]
    mood = forms.ChoiceField(choices=MOOD_CHOICES, required=False, label="Mood")

    class Meta:
        model = JournalEntry
        fields = ['title', 'content', 'mood', 'location', 'privacy_level', 'is_favorite']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Enter title for your entry',
            }),
            'content': forms.Textarea(attrs={
                'placeholder': 'Write your thoughts, feelings, and reflections here...',
                'rows': 10, # Default rows
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'Where were you?',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Privacy choices are directly from the model
        if 'privacy_level' in self.fields:
             self.fields['privacy_level'].choices = JournalEntry.PRIVACY_CHOICES


class JournalAttachmentForm(forms.ModelForm):
    """
    Form for managing a single JournalAttachment instance within a formset.
    The 'DELETE' field is automatically handled by inlineformset_factory (if can_delete=True).
    """
    class Meta:
        model = JournalAttachment
        fields = ['file'] # Only the file field is needed here.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'file' in self.fields:
            self.fields['file'].widget.attrs.update({
                'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 transition duration-200 ease-in-out custom-file-input',
            })
