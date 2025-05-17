# journal/admin.py

from django.contrib import admin
from .models import JournalEntry, JournalAttachment, Tag
import os

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'emoji')
    search_fields = ('name',)
    fields = ('name', 'emoji') 

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('title_display', 'user', 'mood', 'created_at_display', 'is_favorite', 'privacy_level', 'display_tags')
    list_filter = ('user', 'mood', 'is_favorite', 'privacy_level', 'created_at', 'tags')
    search_fields = ('title', 'content', 'user__username', 'tags__name')
    date_hierarchy = 'created_at'
    filter_horizontal = ('tags',) 
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'content')
        }),
        ('Details', {
            'fields': ('mood', 'tags', 'location', 'is_favorite', 'privacy_level')
        }),
        ('AI Generated', {
            'fields': ('ai_quote',),
            'classes': ('collapse',) 
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def display_tags(self, obj):
        return ", ".join([str(tag) for tag in obj.tags.all()[:5]])
    display_tags.short_description = 'Tags'

    def title_display(self, obj):
        return obj.title if obj.title else "(No Title)"
    title_display.short_description = 'Title'
    title_display.admin_order_field = 'title'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M")
    created_at_display.short_description = 'Created At'
    created_at_display.admin_order_field = 'created_at'


@admin.register(JournalAttachment)
class JournalAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'journal_entry_title_link', 'file_name_display', 'file_type', 'uploaded_at')
    list_filter = ('file_type', 'uploaded_at')
    search_fields = ('file', 'journal_entry__title')
    readonly_fields = ('uploaded_at',)

    def journal_entry_title_link(self, obj):
        from django.utils.html import format_html
        from django.urls import reverse
        link = reverse("admin:journal_journalentry_change", args=[obj.journal_entry.id])
        return format_html('<a href="{}">{}</a>', link, obj.journal_entry.title if obj.journal_entry.title else "(No Title)")
    journal_entry_title_link.short_description = 'Journal Entry'
    journal_entry_title_link.admin_order_field = 'journal_entry__title'

    def file_name_display(self, obj):
        if obj.file:
            return os.path.basename(obj.file.name)
        return "N/A"
    file_name_display.short_description = 'File Name'
