from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import register
from django.urls import reverse
from django.utils.html import format_html


@register.filter
def get_item(dictionary, key):
    if dictionary and type(dictionary) == dict:
        return dictionary.get(key)
    return None


@register.simple_tag
def file_media_url(media_rel_path):
    return "%s%s" % (settings.MEDIA_URL, media_rel_path)


@register.filter
def as_dict(obj) -> dict:
    return dict(obj.__dict__)


@register.simple_tag
def ct_field_admin_link(value):
    if not isinstance(value, list):
        selected_values = [value]
    else:
        selected_values = value

    r = []
    for selected_value in selected_values:
        value_split = str(selected_value).split('_')
        if not selected_value.startswith('ct_') or not len(value_split) == 3:
            r.append(selected_value)
            continue

        _ct, ct_id, obj_id = value_split
        ct = ContentType.objects.get(id=ct_id)
        obj = ct.get_object_for_this_type(id=obj_id)

        link = reverse(f'admin:{ct.app_label}_{ct.model}_change', args=(obj_id,))
        r.append(f'<a target="_blank" href="{link}">{obj}</a>')

    return format_html('<br>'.join(r))
