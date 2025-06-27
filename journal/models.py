# journal/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
import os
import logging
from uuid import uuid4

# Import choices from the new, separate constants file to prevent circular imports.
from .constants import MOOD_CHOICES

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
        max_length=20, 
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
    """
    Generates a unique file path for journal attachments, structured by user and date.
    Example: 'user_1/journal_attachments/2025/06/07/unique_hex_string.jpg'
    """
    user_id = instance.journal_entry.user.id
    now = timezone.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    
    _name, ext = os.path.splitext(filename) 
    unique_filename = f"{uuid4().hex}{ext}"
    
    return f'user_{user_id}/journal_attachments/{year}/{month}/{day}/{unique_filename}'


class JournalEntry(models.Model):
    """
    Represents a single journal entry made by a user.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='journal_entries',
        verbose_name=_("User")
    )
    title = models.CharField(max_length=255, blank=True, verbose_name=_("Title"))
    content = models.TextField(verbose_name=_("Content"))

    # MOOD_CHOICES is now imported from constants.py
    mood = models.CharField(
        max_length=50,
        choices=MOOD_CHOICES, 
        blank=True,
        null=True,
        verbose_name=_("Mood")
    )
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Location"))

    PRIVACY_CHOICES = [
        ('private', _('Private (Only You)')),
        ('ai_only', _('AI Analysis Only')),
        ('public', _('Public (Shared)')),
    ]
    privacy_level = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='private',
        verbose_name=_("Privacy Level")
    )
    shared_details = models.JSONField(default=dict, blank=True, null=True, verbose_name=_("Shared Details"))
    ai_quote = models.TextField(blank=True, null=True, verbose_name=_("AI Quote"))
    is_favorite = models.BooleanField(default=False, verbose_name=_("Is Favorite"))
    
    tags = models.ManyToManyField(
        Tag, 
        blank=True, 
        related_name="journal_entries", 
        verbose_name=_("Tags")
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    # --- Fields for AI Task Progress Tracking ---
    ai_quote_task_id = models.CharField(max_length=255, blank=True, null=True, help_text="Celery task ID for AI quote generation.")
    ai_mood_task_id = models.CharField(max_length=255, blank=True, null=True, help_text="Celery task ID for AI mood detection.")
    ai_tags_task_id = models.CharField(max_length=255, blank=True, null=True, help_text="Celery task ID for AI tag suggestion.")

    ai_quote_processed = models.BooleanField(default=False, help_text="True if AI quote generation has been processed for this version.")
    ai_mood_processed = models.BooleanField(default=False, help_text="True if AI mood detection has been processed for this version.")
    ai_tags_processed = models.BooleanField(default=False, help_text="True if AI tag suggestion has been processed for this version.")

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Journal Entry")
        verbose_name_plural = _("Journal Entries")

    def __str__(self):
        if self.title:
            return f"Entry for {self.user.username}: {self.title}"
        return f"Entry for {self.user.username}: {self.content[:50]}..."

    def get_absolute_url(self):
        """Returns the URL to access a detail record for this journal entry."""
        return reverse('journal:journal_detail', kwargs={'pk': self.pk})

    def get_image_attachments(self):
        """Returns a queryset of attachments that are images."""
        return self.attachments.filter(file_type='image').order_by('uploaded_at')

    def delete(self, *args, **kwargs):
        """
        Custom delete method to ensure associated files are also removed from storage.
        """
        entry_pk = self.pk
        logger.info(f"Attempting to delete JournalEntry with ID: {entry_pk}")
        try:
            for attachment in self.attachments.all():
                logger.info(f"Deleting associated attachment ID: {attachment.pk} for JournalEntry ID: {entry_pk}")
                attachment.delete()
        except Exception as e:
            logger.error(f"Error while deleting associated attachments for JournalEntry ID {entry_pk}: {e}", exc_info=True)
        super().delete(*args, **kwargs)
        logger.info(f"JournalEntry (original ID: {entry_pk}) deleted from database.")


class JournalAttachment(models.Model):
    """Represents a file attached to a journal entry."""
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE, 
        related_name='attachments',
        verbose_name=_("Journal Entry")
    )
    file = models.FileField(
        upload_to=user_directory_path,
        verbose_name=_("File"),
    )
    FILE_TYPE_CHOICES = [
        ('image', _('Image')), ('audio', _('Audio')), ('video', _('Video')), ('other', _('Other')),
    ]
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='other', verbose_name=_("File Type"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded At"))

    class Meta:
        verbose_name = _("Journal Attachment")
        verbose_name_plural = _("Journal Attachments")

    def __str__(self):
        file_name_display = os.path.basename(self.file.name) if self.file and self.file.name else 'N/A'
        entry_id_display = self.journal_entry_id if hasattr(self, 'journal_entry_id') else 'Unknown'
        return f"Attachment for Entry {entry_id_display}: {file_name_display}"

    def get_file_name(self):
        """Safely returns the basename of the uploaded file."""
        if self.file and self.file.name:
            return os.path.basename(self.file.name)
        return ""

    def delete(self, *args, **kwargs):
        """
        Custom delete method to also remove the physical file from storage.
        """
        attachment_pk = self.pk 
        original_file_name = self.file.name if self.file else None
        
        logger.info(f"Attempting to delete JournalAttachment instance with ID: {attachment_pk}")
        logger.info(f"Associated file (if any): {original_file_name}")

        if self.file: 
            try:
                self.file.delete(save=False)
                logger.info(f"Physical file for '{original_file_name}' (Attachment ID: {attachment_pk}) deletion initiated from storage.")
            except Exception as e:
                logger.error(f"Error during file deletion for Attachment ID {attachment_pk}: {e}", exc_info=True)

        super().delete(*args, **kwargs) 
        logger.info(f"JournalAttachment instance (original ID: {attachment_pk}) deleted from database.")
