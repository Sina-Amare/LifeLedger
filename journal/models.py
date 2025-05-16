# journal/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.urls import reverse # Import reverse for get_absolute_url
import json
import os # Import os module

class JournalEntry(models.Model):
    """
    Represents a single journal entry for a user.
    Includes fields for content, metadata, privacy, and AI-generated info.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='journal_entries',
        verbose_name="User"
    )

    title = models.CharField(max_length=255, blank=True, verbose_name="Title")

    content = models.TextField(verbose_name="Content")

    # Optional field for the user to manually select their mood.
    # AI can fill this if left blank.
    mood = models.CharField(max_length=50, blank=True, null=True, verbose_name="Mood")

    # Optional field for the user to add a location.
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="Location")

    # Privacy settings for the journal entry.
    PRIVACY_CHOICES = [
        ('private', 'Private (Only You)'),
        ('ai_only', 'AI Analysis Only'), # AI can access for analysis, but not public
        ('public', 'Public (Shared)'), # Can be shared publicly (details controlled by shared_details)
    ]
    privacy_level = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='private',
        verbose_name="Privacy Level"
    )

    # Details to be shared if privacy_level is 'public'. Stored as JSON.
    # Example: {'include_date': True, 'include_location': False}
    shared_details = models.JSONField(
        default=dict, # Use dict as the callable default
        blank=True,
        null=True, # Allow null for simplicity if no specific details are set
        verbose_name="Shared Details"
    )

    # AI-generated quote based on the journal content/mood.
    ai_quote = models.TextField(blank=True, null=True, verbose_name="AI Quote")

    # Flag to mark the entry as a favorite.
    is_favorite = models.BooleanField(default=False, verbose_name="Is Favorite")

    # Automatically set the date and time when the entry is first created.
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    # Automatically update the date and time whenever the entry is saved.
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        # Order journal entries by creation date in descending order by default.
        ordering = ['-created_at']
        verbose_name = "Journal Entry"
        verbose_name_plural = "Journal Entries"

    def __str__(self):
        """
        String representation of the journal entry.
        Shows the title or the beginning of the content if no title.
        """
        if self.title:
            return f"Entry for {self.user.username}: {self.title}"
        elif self.content:
            # Return first 50 characters of content if no title
            return f"Entry for {self.user.username}: {self.content[:50]}..."
        else:
            return f"Entry for {self.user.username}: (No content)"

    def get_absolute_url(self):
        """
        Returns the URL to display the details of the journal entry.
        Used for redirects after creation/update.
        """
        # Assumes you have a URL pattern named 'journal:journal_detail'
        # that takes a primary key (pk) as an argument.
        return reverse('journal:journal_detail', kwargs={'pk': self.pk})


    def is_ai_accessible(self):
        """Checks if the entry is accessible by AI for analysis."""
        return self.privacy_level in ['ai_only', 'public']

    def is_public(self):
        """Checks if the entry is publicly shareable."""
        return self.privacy_level == 'public'


class JournalAttachment(models.Model):
    """
    Represents a file attachment for a journal entry (e.g., image, audio).
    """
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name="Journal Entry"
    )

    # The file itself. Uploaded files will be stored here.
    # upload_to specifies the subdirectory within MEDIA_ROOT.
    file = models.FileField(
        upload_to='journal_attachments/%Y/%m/%d/',
        verbose_name="File",
        # Optional: Add validators for allowed file types
        # validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp3', 'wav', 'mp4'])]
    )

    # Type of the file (e.g., 'image', 'audio', 'video', 'other').
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('other', 'Other'),
    ]
    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES,
        default='other',
        verbose_name="File Type"
    )

    # Automatically set the date and time when the file was uploaded.
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Uploaded At")

    class Meta:
        verbose_name = "Journal Attachment"
        verbose_name_plural = "Journal Attachments"

    def __str__(self):
        """
        String representation of the attachment.
        Shows the file name and the related journal entry ID.
        """
        # Use os.path.basename to get just the file name
        return f"Attachment for Entry {self.journal_entry.id}: {os.path.basename(self.file.name)}"

    def delete(self, *args, **kwargs):
        """
        Override the delete method to delete the file from storage
        when the JournalAttachment object is deleted.
        """
        # Delete the file from storage
        if self.file:
            self.file.delete(save=False) # Use save=False to avoid saving the model again

        # Call the parent class's delete method to delete the model instance
        super().delete(*args, **kwargs)

    # Optional: Add methods here, e.g., to get file URL, thumbnail URL, etc.
    # def get_file_url(self):
    #     """Returns the URL for the uploaded file."""
    #     if self.file:
    #         return self.file.url
    #     return None
