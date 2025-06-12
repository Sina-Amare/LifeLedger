from django.utils.translation import gettext_lazy as _

# Defines the choices for the 'mood' field in the JournalEntry model.
# This tuple is used for database model choices and form fields.
# Placing it in a separate file helps prevent circular import errors.
MOOD_CHOICES = [
    ('happy', _('Happy')),
    ('excited', _('Excited')),
    ('calm', _('Calm')),
    ('neutral', _('Neutral')),
    ('sad', _('Sad')),
    ('angry', _('Angry')),
]

# NEW: Defines a numerical mapping for moods.
# This is used for quantitative analysis, like calculating average mood over time.
# Higher values represent more positive moods.
MOOD_NUMERICAL = {
    'happy': 2,
    'excited': 2,
    'calm': 1,
    'neutral': 0,
    'sad': -1,
    'angry': -2,
}
