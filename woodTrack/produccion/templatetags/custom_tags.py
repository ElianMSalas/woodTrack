# custom_tags.py
from django import template

register = template.Library()

@register.filter
def dictget(dict_data, key):
    return dict_data.get(key, None)

@register.filter
def get_item(list_data, key):
    return list_data.get(key)
