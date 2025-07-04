# Generated by Django 5.1.6 on 2025-06-18 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0005_remove_journalentry_suggested_mood_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journalentry',
            name='mood',
            field=models.CharField(blank=True, choices=[('happy', 'Happy'), ('excited', 'Excited'), ('calm', 'Calm'), ('neutral', 'Neutral'), ('sad', 'Sad'), ('angry', 'Angry')], max_length=50, null=True, verbose_name='Mood'),
        ),
    ]
