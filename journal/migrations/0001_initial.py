# Generated by Django 5.1.6 on 2025-05-17 17:52

import django.db.models.deletion
import journal.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='The name of the tag (e.g., Work, Personal, Ideas).', max_length=50, unique=True)),
                ('emoji', models.CharField(blank=True, help_text='An optional emoji to represent the tag visually (e.g., 📚, 😊, 👨\u200d👩\u200d👧\u200d👦).', max_length=20, null=True)),
            ],
            options={
                'verbose_name': 'Tag',
                'verbose_name_plural': 'Tags',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='JournalEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=255, verbose_name='Title')),
                ('content', models.TextField(verbose_name='Content')),
                ('mood', models.CharField(blank=True, choices=[('happy', 'Happy'), ('sad', 'Sad'), ('angry', 'Angry'), ('calm', 'Calm'), ('neutral', 'Neutral'), ('excited', 'Excited')], max_length=50, null=True, verbose_name='Mood')),
                ('location', models.CharField(blank=True, max_length=255, null=True, verbose_name='Location')),
                ('privacy_level', models.CharField(choices=[('private', 'Private (Only You)'), ('ai_only', 'AI Analysis Only'), ('public', 'Public (Shared)')], default='private', max_length=10, verbose_name='Privacy Level')),
                ('shared_details', models.JSONField(blank=True, default=dict, null=True, verbose_name='Shared Details')),
                ('ai_quote', models.TextField(blank=True, null=True, verbose_name='AI Quote')),
                ('is_favorite', models.BooleanField(default=False, verbose_name='Is Favorite')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='journal_entries', to=settings.AUTH_USER_MODEL, verbose_name='User')),
                ('tags', models.ManyToManyField(blank=True, related_name='journal_entries', to='journal.tag', verbose_name='Tags')),
            ],
            options={
                'verbose_name': 'Journal Entry',
                'verbose_name_plural': 'Journal Entries',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='JournalAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=journal.models.user_directory_path, verbose_name='File')),
                ('file_type', models.CharField(choices=[('image', 'Image'), ('audio', 'Audio'), ('video', 'Video'), ('other', 'Other')], default='other', max_length=10, verbose_name='File Type')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='Uploaded At')),
                ('journal_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='journal.journalentry', verbose_name='Journal Entry')),
            ],
            options={
                'verbose_name': 'Journal Attachment',
                'verbose_name_plural': 'Journal Attachments',
            },
        ),
    ]
