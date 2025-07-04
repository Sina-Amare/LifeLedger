# Generated by Django 5.1.6 on 2025-06-18 11:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0007_alter_journalattachment_file_type_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journalattachment',
            name='file_type',
            field=models.CharField(choices=[('image', 'Image'), ('audio', 'Audio'), ('video', 'Video'), ('other', 'Other')], default='other', max_length=10, verbose_name='File Type'),
        ),
        migrations.AlterField(
            model_name='journalentry',
            name='ai_mood_processed',
            field=models.BooleanField(default=False, help_text='True if AI mood detection has been processed for this version.'),
        ),
        migrations.AlterField(
            model_name='journalentry',
            name='ai_mood_task_id',
            field=models.CharField(blank=True, help_text='Celery task ID for AI mood detection.', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='journalentry',
            name='ai_quote_processed',
            field=models.BooleanField(default=False, help_text='True if AI quote generation has been processed for this version.'),
        ),
        migrations.AlterField(
            model_name='journalentry',
            name='ai_quote_task_id',
            field=models.CharField(blank=True, help_text='Celery task ID for AI quote generation.', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='journalentry',
            name='ai_tags_processed',
            field=models.BooleanField(default=False, help_text='True if AI tag suggestion has been processed for this version.'),
        ),
        migrations.AlterField(
            model_name='journalentry',
            name='ai_tags_task_id',
            field=models.CharField(blank=True, help_text='Celery task ID for AI tag suggestion.', max_length=255, null=True),
        ),
    ]
