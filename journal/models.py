# journal/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
import os
import logging
from uuid import uuid4
# from django.utils.text import slugify # Uncomment if you plan to use slugs for Tags

logger = logging.getLogger(__name__)

class Tag(models.Model):
    """
    Represents a predefined tag that can be associated with journal entries.
    Includes an optional emoji for visual representation.
    """
    name = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="The name of the tag (e.g., Work, Personal, Ideas)."
    )
    emoji = models.CharField(
        max_length=20,  # << INCREASED MAX_LENGTH FOR EMOJI (e.g., to 20 for safety)
        blank=True,
        null=True,
        help_text="An optional emoji to represent the tag visually (e.g., 📚, 😊, 👨‍👩‍👧‍👦)."
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return f"{self.emoji} {self.name}" if self.emoji else self.name


def user_directory_path(instance, filename):
    user_id = instance.journal_entry.user.id
    now = timezone.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    
    _name, ext = os.path.splitext(filename) 
    unique_filename = f"{uuid4().hex}{ext}"
    
    return f'user_{user_id}/journal_attachments/{year}/{month}/{day}/{unique_filename}'


class JournalEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='journal_entries',
        verbose_name="User"
    )
    title = models.CharField(max_length=255, blank=True, verbose_name="Title")
    content = models.TextField(verbose_name="Content")

    MOOD_CHOICES = [ 
        ('happy', 'Happy'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
        ('calm', 'Calm'),
        ('neutral', 'Neutral'),
        ('excited', 'Excited'),
    ]
    mood = models.CharField(
        max_length=50,
        choices=MOOD_CHOICES, 
        blank=True,
        null=True,
        verbose_name="Mood"
    )
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="Location")

    PRIVACY_CHOICES = [
        ('private', 'Private (Only You)'),
        ('ai_only', 'AI Analysis Only'),
        ('public', 'Public (Shared)'),
    ]
    privacy_level = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='private',
        verbose_name="Privacy Level"
    )
    shared_details = models.JSONField(default=dict, blank=True, null=True, verbose_name="Shared Details")
    ai_quote = models.TextField(blank=True, null=True, verbose_name="AI Quote")
    is_favorite = models.BooleanField(default=False, verbose_name="Is Favorite")
    
    tags = models.ManyToManyField(
        Tag, 
        blank=True, 
        related_name="journal_entries", 
        verbose_name="Tags"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Journal Entry"
        verbose_name_plural = "Journal Entries"

    def __str__(self):
        if self.title:
            return f"Entry for {self.user.username}: {self.title}"
        return f"Entry for {self.user.username}: {self.content[:50]}..."

    def get_absolute_url(self):
        return reverse('journal:journal_detail', kwargs={'pk': self.pk})

    def delete(self, *args, **kwargs):
        entry_pk = self.pk
        logger.info(f"Attempting to delete JournalEntry with ID: {entry_pk}")
        try:
            for attachment in self.attachments.all():
                logger.info(f"  - Deleting associated attachment ID: {attachment.pk} for JournalEntry ID: {entry_pk}")
                attachment.delete()
        except Exception as e:
            logger.error(f"Error while deleting associated attachments for JournalEntry ID {entry_pk}: {e}", exc_info=True)
        super().delete(*args, **kwargs)
        logger.info(f"JournalEntry (original ID: {entry_pk}) deleted from database.")


class JournalAttachment(models.Model):
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE, 
        related_name='attachments',
        verbose_name="Journal Entry"
    )
    file = models.FileField(
        upload_to=user_directory_path,
        verbose_name="File",
    )
    FILE_TYPE_CHOICES = [
        ('image', 'Image'), ('audio', 'Audio'), ('video', 'Video'), ('other', 'Other'),
    ]
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='other', verbose_name="File Type")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Uploaded At")

    class Meta:
        verbose_name = "Journal Attachment"
        verbose_name_plural = "Journal Attachments"

    def __str__(self):
        file_name_display = os.path.basename(self.file.name) if self.file and self.file.name else 'N/A'
        entry_id_display = self.journal_entry_id if hasattr(self, 'journal_entry_id') else 'Unknown'
        return f"Attachment for Entry {entry_id_display}: {file_name_display}"

    def get_file_name(self):
        if self.file and self.file.name:
            return os.path.basename(self.file.name)
        return ""

    def delete(self, *args, **kwargs):
        attachment_pk = self.pk 
        original_file_name = None
        original_file_path = None

        if self.file and self.file.name:
            original_file_name = self.file.name
            if hasattr(self.file, 'path'):
                original_file_path = self.file.path
        
        logger.info(f"Attempting to delete JournalAttachment instance with ID: {attachment_pk}")
        logger.info(f"  - Associated file (if any): {original_file_name}")

        if original_file_name and original_file_path: 
            try:
                logger.debug(f"  - Calling self.file.delete(save=False) for {original_file_name}")
                self.file.delete(save=False)
                logger.info(f"  - Physical file for '{original_file_name}' (Attachment ID: {attachment_pk}) deletion initiated from storage.")
            except Exception as e:
                logger.error(f"  - Error during self.file.delete() for {original_file_name} (Attachment ID: {attachment_pk}): {e}", exc_info=True)
        elif self.file and not original_file_path: 
             logger.warning(f"  - File object exists for JournalAttachment ID {attachment_pk} but could not determine its physical path.")
        else:
            logger.warning(f"  - No file was associated with JournalAttachment ID: {attachment_pk} at deletion time.")

        super().delete(*args, **kwargs) 
        logger.info(f"JournalAttachment instance (original ID: {attachment_pk}) deleted from database.")
