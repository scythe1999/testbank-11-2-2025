from django import template

register = template.Library()

@register.filter
def get_item(value, key):
    key = str(key)
    
    if isinstance(value, dict):
        return value.get(key, None)
    
    try:
        return getattr(value, key, None)
    except AttributeError:
        return None


@register.filter
def first_letters(value):
    if not value:
        return ''
    words = value.split()
    return ''.join([word[0].upper() for word in words if word])


@register.filter
def get_dict_value(dictionary, key):
    return dictionary.get(key, 0)



@register.filter
def get_dict_value(dictionary, key):
    return dictionary.get(key)
