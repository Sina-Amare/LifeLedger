# ai_services/models.py

from django.db import models
from django.conf import settings
# It's good practice to import the JournalEntry model using settings.AUTH_USER_MODEL's app
# or directly if it's a well-defined app like 'journal'.
# from journal.models import JournalEntry # Assuming your journal app is named 'journal'

class JournalEntryAnalysis(models.Model):
    """
    Stores AI-driven analysis results for a specific journal entry.
    """
    # Link to the specific journal entry
    # Using a OneToOneField ensures each entry has at most one AI analysis record.
    # If an entry is deleted, its analysis should also be deleted.
    journal_entry = models.OneToOneField(
        'journal.JournalEntry', # Use 'app_label.ModelName' string to avoid circular imports
        on_delete=models.CASCADE,
        related_name='ai_analysis', # How to access this from a JournalEntry instance (entry.ai_analysis)
        primary_key=True, # Makes journal_entry the primary key for this model
        help_text="The journal entry this analysis pertains to."
    )

    # Example fields for AI-generated data
    # We might already have 'mood' and 'ai_quote' on JournalEntry.
    # If AI provides a more nuanced sentiment score, we can store it here.
    sentiment_score = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Overall sentiment score from -1.0 (negative) to 1.0 (positive)."
    )
    
    # Could store a list of keywords/topics extracted by AI
    extracted_keywords = models.JSONField(
        null=True, 
        blank=True, 
        default=list, 
        help_text="List of keywords or topics extracted from the entry."
    )
    
    # A more detailed summary if different from a simple quote
    generated_summary = models.TextField(
        blank=True, 
        null=True, 
        help_text="AI-generated summary of the journal entry."
    )
    
    # Timestamp for when the analysis was last performed/updated
    analysis_timestamp = models.DateTimeField(
        auto_now=True,
        help_text="When this analysis was last generated or updated."
    )

    # You could add more fields later, e.g.:
    # detected_emotions = models.JSONField(null=True, blank=True, default=list, help_text="List of detected emotions and their scores.")
    # suggested_tags = models.JSONField(null=True, blank=True, default=list, help_text="Tags suggested by AI.")
    # pattern_references = models.TextField(blank=True, null=True, help_text="Notes on detected patterns or links to other relevant entries.")

    class Meta:
        verbose_name = "Journal Entry AI Analysis"
        verbose_name_plural = "Journal Entry AI Analyses"
        # Ensures that the analysis is tied to the user of the journal entry for any permission checks later
        # This is not a direct DB constraint but a good reminder for querysets.
        # constraints = [
        #     models.UniqueConstraint(fields=['journal_entry'], name='unique_ai_analysis_per_entry')
        # ] # primary_key=True on OneToOneField already enforces uniqueness.

    def __str__(self):
        return f"AI Analysis for Entry ID: {self.journal_entry_id}"