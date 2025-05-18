# journal/admin.py

from django.contrib import admin
from .models import JournalEntry, JournalAttachment, Tag
import os
from django.utils.html import format_html # For linking in admin
from django.urls import reverse # For linking in admin

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for the Tag model.
    """
    list_display = ('name', 'emoji_display') # Use a method for emoji for better empty handling
    search_fields = ('name',)
    fields = ('name', 'emoji') 

    def emoji_display(self, obj):
        return obj.emoji if obj.emoji else "--"
    emoji_display.short_description = 'Emoji'


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for the JournalEntry model.
    """
    list_display = (
        'title_display', 
        'user', 
        'mood', 
        'created_at_display', 
        'is_favorite', 
        'privacy_level', 
        'display_tags',
        'ai_quote_processed', # New field
        'ai_mood_processed',  # New field
        'ai_tags_processed',  # New field
    )
    list_filter = (
        'user', 
        'mood', 
        'is_favorite', 
        'privacy_level', 
        'created_at', 
        'tags',
        'ai_quote_processed', # New filter
        'ai_mood_processed',  # New filter
        'ai_tags_processed',  # New filter
    )
    search_fields = ('title', 'content', 'user__username', 'tags__name', 'ai_quote')
    date_hierarchy = 'created_at'
    filter_horizontal = ('tags',) 
    
    # Add new AI status fields to readonly_fields
    readonly_fields = (
        'created_at', 
        'updated_at',
        'ai_quote_task_id',
        'ai_mood_task_id',
        'ai_tags_task_id',
        # Making status flags readonly as they are set by tasks
        # 'ai_quote_processed', 
        # 'ai_mood_processed',
        # 'ai_tags_processed',
    )
    
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'content')
        }),
        ('Details', {
            'fields': ('mood', 'tags', 'location', 'is_favorite', 'privacy_level')
        }),
        ('AI Generated Content', { # Renamed for clarity
            'fields': ('ai_quote',),
            # 'classes': ('collapse',) # Keep expanded for now to see it easily
        }),
        ('AI Task Status', { # New fieldset for AI task tracking
            'fields': (
                'ai_quote_task_id', 'ai_quote_processed',
                'ai_mood_task_id', 'ai_mood_processed',
                'ai_tags_task_id', 'ai_tags_processed',
            ),
            'classes': ('collapse',), # Collapsible by default
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def display_tags(self, obj):
        """Display up to 5 tags in the list view."""
        return ", ".join([str(tag) for tag in obj.tags.all()[:5]])
    display_tags.short_description = 'Tags'

    def title_display(self, obj):
        """Display title or '(No Title)'."""
        return obj.title if obj.title else "(No Title)"
    title_display.short_description = 'Title'
    title_display.admin_order_field = 'title'
    
    def created_at_display(self, obj):
        """Format created_at timestamp."""
        return obj.created_at.strftime("%Y-%m-%d %H:%M")
    created_at_display.short_description = 'Created At'
    created_at_display.admin_order_field = 'created_at'


@admin.register(JournalAttachment)
class JournalAttachmentAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for the JournalAttachment model.
    """
    list_display = ('id', 'journal_entry_title_link', 'file_name_display', 'file_type', 'uploaded_at_display')
    list_filter = ('file_type', 'uploaded_at')
    search_fields = ('file', 'journal_entry__title')
    readonly_fields = ('uploaded_at',)

    def journal_entry_title_link(self, obj):
        """Make journal entry title a link to the entry in admin."""
        if obj.journal_entry:
            link = reverse("admin:journal_journalentry_change", args=[obj.journal_entry.id])
            return format_html('<a href="{}">{}</a>', link, obj.journal_entry.title if obj.journal_entry.title else "(No Title)")
        return "N/A"
    journal_entry_title_link.short_description = 'Journal Entry'
    journal_entry_title_link.admin_order_field = 'journal_entry__title'

    def file_name_display(self, obj):
        """Display only the basename of the file."""
        if obj.file:
            return os.path.basename(obj.file.name)
        return "N/A"
    file_name_display.short_description = 'File Name'

    def uploaded_at_display(self, obj):
        """Format uploaded_at timestamp."""
        return obj.uploaded_at.strftime("%Y-%m-%d %H:%M")
    uploaded_at_display.short_description = 'Uploaded At'
    uploaded_at_display.admin_order_field = 'uploaded_at'

