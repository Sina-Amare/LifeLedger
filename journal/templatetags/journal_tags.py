# journal/templatetags/journal_tags.py

from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Allows accessing dictionary items with a variable key in Django templates.
    Usage: {{ my_dictionary|get_item:my_key }}
    """
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None

@register.filter(name='attr')
def attr(obj, attr_name):
    """
    Allows accessing an attribute of an object using a variable.
    Usage: {{ my_object|attr:"attribute_name_as_string" }}
    """
    if hasattr(obj, str(attr_name)):
        return getattr(obj, str(attr_name))
    return None
