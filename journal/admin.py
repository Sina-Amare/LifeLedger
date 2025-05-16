from django.contrib import admin
from .models import JournalEntry, JournalAttachment
# Register your models here.
admin.site.register(JournalEntry)
admin.site.register(JournalAttachment)