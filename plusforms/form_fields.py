import importlib
import sys

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import FileExtensionValidator
from django.forms import Field
from django.utils.datetime_safe import datetime
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
    'DecimalField',
    'FloatField',
    'IntegerField',
    'PasswordField',
    'EmailField',
    'CheckboxField',
    'FileField',
    'ImageField',
    'URLField',
    'DateField',
    'TimeField',
    'DateTimeField',
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

    def check_size(self, value, instance):
        """
        Check if mb limit is set and validate
        """
        if isinstance(value, list):
            for item in value:
                self.check_size(item, instance)
        else:
            max_mb = instance.glossary.get('max_mb')
            if instance and value and max_mb:
                file_size_in_mb = value.size / (1000*1000)
                if file_size_in_mb > max_mb:
                    print(file_size_in_mb)
                    raise ValidationError(_('Maximum file size exceeded. Your file: %d MB (max. %i MB)' % (file_size_in_mb, max_mb)))

    def check_extension(self, value, instance):
        if isinstance(value, list):
            for item in value:
                self.check_extension(item, instance)
        else:
            ext = instance.glossary.get('ext')
            if instance and value and ext:
                FileExtensionValidator(allowed_extensions=ext)(value)


class ImageField(forms.ImageField):
    widget = forms.FileInput
    name = _('Image Field')
    template_name = "plusforms/fields/input.html"


def get_date_input_examples(FieldClass) -> list:
    """
    Generate examples for a valid input value.
    :param FieldClass: InputField
    :return: List of input examples.
    """
    r = []
    for f in FieldClass.input_formats:
        now = datetime.now()
        r.append(now.strftime(f))
    return r


class DateField(forms.DateField):
    name = _('Date Field')
    template_name = "plusforms/fields/input.html"
    widget = forms.DateInput
    widget_class = 'form-control'

    default_error_messages = {
        'invalid': '%s [%s]' % (
            forms.DateField.default_error_messages['invalid'],
            ', '.join(get_date_input_examples(forms.DateField))
        )
    }


class TimeField(forms.TimeField):
    name = _('Time Field')
    template_name = "plusforms/fields/input.html"
    widget = forms.TimeInput
    widget_class = 'form-control'

    default_error_messages = {
        'invalid': '%s. Format [%s]' % (
            forms.TimeField.default_error_messages['invalid'],
            ', '.join(get_date_input_examples(forms.TimeField))
        ),
    }


class DateTimeField(forms.DateTimeField):
    name = _('Date Time Field')
    widget = forms.DateTimeInput
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'

    default_error_messages = {
        'invalid': '%s [%s]' % (
            forms.DateTimeField.default_error_messages['invalid'],
            ', '.join(get_date_input_examples(forms.DateTimeField))
        )
    }


class URLField(forms.URLField):
    name = _('URL Field')
    widget = forms.URLInput
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'


class IntegerField(forms.IntegerField):
    name = _('Integer Field')
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'


class FloatField(forms.FloatField):
    name = _('Float Field')
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'


class DecimalField(forms.DecimalField):
    name = _('Decimal Field')
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'
