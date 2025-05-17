# journal/apps.py

from django.apps import AppConfig
from django.db.models.signals import post_migrate

# Define your predefined tags here with their names and emojis
# These will be created/updated when the app is ready (after migrations)
PREDEFINED_TAGS_WITH_EMOJI = [
    {'name': 'Work', 'emoji': '💼'},
    {'name': 'Personal', 'emoji': '🏠'},
    {'name': 'Ideas', 'emoji': '💡'},
    {'name': 'Learning', 'emoji': '📚'},
    {'name': 'Travel', 'emoji': '✈️'},
    {'name': 'Health', 'emoji': '💪'},
    {'name': 'Fitness', 'emoji': '🏋️‍♂️'},
    {'name': 'Finance', 'emoji': '💰'},
    {'name': 'Family', 'emoji': '👨‍👩‍👧‍👦'},
    {'name': 'Friends', 'emoji': '😊'},
    {'name': 'Hobbies', 'emoji': '🎨'},
    {'name': 'Goals', 'emoji': '🎯'},
    {'name': 'Reflection', 'emoji': '🤔'},
    {'name': 'Gratitude', 'emoji': '🙏'},
    {'name': 'Project', 'emoji': '🛠️'},
    {'name': 'Book', 'emoji': '📖'},
    {'name': 'Movie', 'emoji': '🎬'},
    {'name': 'Food', 'emoji': '🍲'},
    {'name': 'Dream', 'emoji': '🌙'},
    {'name': 'Important', 'emoji': '⭐'},
    {'name': 'Urgent', 'emoji': '❗'},
    {'name': 'To-Do', 'emoji': '✅'},
    {'name': 'Event', 'emoji': '🎉'},
    {'name': 'Nature', 'emoji': '🌳'},
    {'name': 'Music', 'emoji': '🎵'},
    {'name': 'Technology', 'emoji': '💻'},
]

def populate_initial_tags_handler(sender, **kwargs):
    """
    Signal handler to populate/update predefined tags after migrations.
    """
    # Important: Import the Tag model *inside* the function
    # to avoid AppRegistryNotReady errors during Django's startup process.
    from .models import Tag 
    
    print("\nChecking and populating predefined tags...")
    for tag_data in PREDEFINED_TAGS_WITH_EMOJI:
        tag_name_capitalized = tag_data['name'].capitalize() # Ensure consistent capitalization
        obj, created = Tag.objects.update_or_create(
            name__iexact=tag_name_capitalized, # Case-insensitive check for existing tag
            defaults={
                'name': tag_name_capitalized, 
                'emoji': tag_data.get('emoji') # Use .get() for emoji as it's optional
            }
        )
        if created:
            print(f"  Created tag: '{obj.name}' with emoji '{obj.emoji or ''}'")
        else:
            # If it existed, ensure emoji is updated if provided and different from current
            if tag_data.get('emoji') and obj.emoji != tag_data.get('emoji'):
                obj.emoji = tag_data.get('emoji')
                obj.save(update_fields=['emoji']) # Only update emoji field
                print(f"  Updated emoji for tag: '{obj.name}' to '{obj.emoji}'")
            else:
                print(f"  Tag '{obj.name}' (emoji: '{obj.emoji or ''}') already exists/is up-to-date.")
    print("Finished checking/populating predefined tags.")


class JournalAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'journal'

    def ready(self):
        """
        Called when the application is ready.
        Connects the post_migrate signal to populate initial tags.
        """
        # Connect the signal handler to the post_migrate signal
        # This ensures that populate_initial_tags_handler is called after migrations 
        # for this app (journal) are run.
        post_migrate.connect(populate_initial_tags_handler, sender=self)
        print("JournalAppConfig: Connected populate_initial_tags_handler to post_migrate signal.")

