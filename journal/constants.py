# journal/constants.py

from django.utils.translation import gettext_lazy as _

# Defines the choices for the 'mood' field in the JournalEntry model.
# This tuple is used for database model choices and form fields.
# Placing it in a separate file helps prevent circular import errors.
MOOD_CHOICES = [
    ('happy', _('Happy')),
    ('sad', _('Sad')),
    ('angry', _('Angry')),
    ('calm', _('Calm')),
    ('neutral', _('Neutral')),
    ('excited', _('Excited')),
]
