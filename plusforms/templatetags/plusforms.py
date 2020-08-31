from pprint import pprint

from django.template.defaultfilters import register

from plusforms.cms_plugins import GenericFormPlugin


@register.filter
def get_field_instance_from_form(plugin, key):
    pi, pc = plugin.get_plugin_instance()
    children = pc.field_plugins(pi)
    for child in children:
        pi, pc = child.get_plugin_instance()
        if pi.glossary.get('field_id') == key:
            return pi
