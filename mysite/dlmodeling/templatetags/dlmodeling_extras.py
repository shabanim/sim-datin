import json
from django import template

register = template.Library()


@register.filter(name='dict_lookup')
def dict_lookup(dict, key):
    return dict[key]

@register.filter(name='dictify')
def dictify(data):
    if data is None:
        return None
    if len(data) == 0:
        return None

    if isinstance(data, dict):
        return data
    else:
        return json.loads(data)
