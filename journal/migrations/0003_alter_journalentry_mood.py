# Generated by Django 5.1.6 on 2025-06-03 09:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0002_journalentry_ai_mood_processed_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journalentry',
            name='mood',
            field=models.CharField(blank=True, choices=[('happy', 'Happy'), ('sad', 'Sad'), ('angry', 'Angry'), ('calm', 'Calm'), ('neutral', 'Neutral'), ('excited', 'Excited')], help_text='User-selected mood for the entry.', max_length=50, null=True, verbose_name='Mood'),
        ),
    ]
