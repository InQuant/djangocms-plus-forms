import importlib
import sys

from django import forms
from django.conf import settings
from django.forms import Field
from django.utils.translation import ugettext_lazy as _


def get_class_from_string(class_string: str):
    try:
        class_name = class_string.split('.')[-1]
        module_name = '.'.join(class_string.split('.')[:-1])
        importlib.import_module(module_name)
        CLS = getattr(sys.modules[module_name], class_name)
        return CLS
    except KeyError:
        raise ValueError('Could not get class from string "%s"' % class_string)


def get_class(class_name: str):
    for CLS in get_available_form_fields():
        if class_name == CLS.__name__:
            return CLS


def get_available_form_fields():
    fields = []
    for field in FORM_FIELDS:
        F_CLS = getattr(sys.modules[__name__], field, None)
        if not F_CLS:
            continue
        fields.append(F_CLS)

    # get from settings
    s_fields = getattr(settings, 'PLUSFORMS_FIELDS', [])
    for f in s_fields:
        try:
            CLS = get_class_from_string(f)
        except ValueError:
            raise ValueError('"%s" in PLUSFORMS_FIELDS settings could not be parsed into a class. '
                             'Does it exist?' % f)
        if not issubclass(CLS, Field):
            raise ValueError('"%s" is not a subclass of the forms.Field class.')
        fields.append(CLS)

    return fields


FORM_FIELDS = [
    'InputField',
    'TextField',
    'PasswordField',
    'EmailField',
    'CheckboxField',
    'FileField',
    'ImageField',
]


class InputField(forms.CharField):
    name = _('Text field')
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'


class TextField(InputField):
    name = _('Textarea field')
    template_name = "plusforms/fields/input.html"
    widget = forms.Textarea


class PasswordField(InputField):
    widget = forms.PasswordInput
    name = _('Password field')
    template_name = "plusforms/fields/input.html"


class EmailField(InputField):
    widget = forms.EmailInput
    name = _('Email field')


class CheckboxField(forms.BooleanField):
    name = _('Checkbox field')
    template_name = "plusforms/fields/checkbox.html"
    widget = forms.CheckboxInput
    widget_class = 'form-check-input'


class FileField(forms.FileField):
    widget = forms.FileInput
    name = _('File Field')
    template_name = "plusforms/fields/input.html"


class ImageField(forms.ImageField):
    widget = forms.FileInput
    name = _('Image Field')
    template_name = "plusforms/fields/input.html"
