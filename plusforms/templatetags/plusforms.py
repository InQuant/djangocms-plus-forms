from django.conf import settings
from django.template.defaultfilters import register


@register.filter
def get_item(dictionary, key):
    if dictionary and type(dictionary) == dict:
        return dictionary.get(key)
    return None


@register.simple_tag
def file_media_url(media_rel_path):
    return "%s%s" % (settings.MEDIA_URL, media_rel_path)
