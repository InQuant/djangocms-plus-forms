import importlib
import sys
import os

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile, get_image_dimensions
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import FileExtensionValidator
from django.core.files import File
from django.forms import Field
from django.utils.datetime_safe import datetime
from django.utils.translation import ugettext_lazy as _
from django.utils.deconstruct import deconstructible


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


class BaseFieldMixIn:
    def serialize_field(self, value):
        return value

    def deserialize_field(self, value):
        return value


class InputField(forms.CharField, BaseFieldMixIn):
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


class CheckboxField(forms.BooleanField, BaseFieldMixIn):
    name = _('Checkbox field')
    template_name = "plusforms/fields/checkbox.html"
    widget = forms.CheckboxInput
    widget_class = 'form-check-input'


@deconstructible
class PixelResolutionValidator:
    message = _(
        "Minimum image pixel resolution must be %(min_px_width)s x %(min_px_height)s. "
        "Uploaded image resolution is %(width)s x %(height)s."
    )
    code = 'invalid_pixel_resolution'

    def __init__(self, min_px_width=None, min_px_height=None, message=None, code=None):
        self.min_px_width = min_px_width
        self.min_px_height = min_px_height
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

    def __call__(self, file: InMemoryUploadedFile):
        width, height = get_image_dimensions(file)

        min_val_1 = self.min_px_height
        min_val_2 = self.min_px_width
        val_1 = height
        val_2 = width

        # check if rotated (needed?)
        # if self.min_px_width >= self.min_px_height:
        #     min_val_1 = self.min_px_width
        #     min_val_2 = self.min_px_height
        #
        # if width > height:
        #     val_1 = width
        #     val_2 = height

        if val_1 < min_val_1 or val_2 < min_val_2:
            raise ValidationError(
                self.message,
                code=self.code,
                params={
                    'min_px_width': self.min_px_width,
                    'min_px_height': self.min_px_height,
                    'width': width,
                    'height': height,
                }
            )


@deconstructible
class FileSizeValidator:
    message = _(
        "File size of '%(size)sMB' is not allowed. "
        "Maximum allowed file size is: '%(allowed_size)sMB'."
    )
    code = 'invalid_file_size'

    def __init__(self, max_mb=None, message=None, code=None):
        self.max_mb = max_mb
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

    def __call__(self, value):
        file_size_in_mb = value.size / (1000*1000)
        if self.max_mb and file_size_in_mb > self.max_mb:
            raise ValidationError(
                self.message,
                code=self.code,
                params={
                    'size': file_size_in_mb,
                    'allowed_size': self.max_mb
                }
            )


class FileValidationMixin:

    def __init__(self, *, max_mb=None, allowed_extensions=None, **kwargs):
        super().__init__(**kwargs)
        if max_mb is not None:
            self.validators.append(FileSizeValidator(max_mb=max_mb))
        if allowed_extensions is not None:
            self.validators.append(FileExtensionValidator(allowed_extensions=allowed_extensions))

    def serialize_field(self, dj_file):
        try:
            return dj_file.name
        except Exception:
            return dj_file

    def deserialize_field(self, name):
        try:
            return File(open(os.path.join(settings.MEDIA_ROOT, name)), name=name)
        except Exception:
            return name


class ImageValidationMixIn(FileValidationMixin):
    def __init__(self, *, min_px_width=None, min_px_height=None, **kwargs):
        super().__init__(**kwargs)
        if min_px_width is not None or min_px_height is not None:
            self.validators.append(PixelResolutionValidator(min_px_width, min_px_height))


class FileField(FileValidationMixin, forms.FileField):
    widget = forms.ClearableFileInput
    name = _('File Field')
    template_name = "plusforms/fields/file.html"


class ImageField(ImageValidationMixIn, forms.ImageField):
    widget = forms.FileInput
    name = _('Image Field')
    template_name = "plusforms/fields/file.html"


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


class DateField(forms.DateField, BaseFieldMixIn):
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


class TimeField(forms.TimeField, BaseFieldMixIn):
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


class DateTimeField(forms.DateTimeField, BaseFieldMixIn):
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


class URLField(forms.URLField, BaseFieldMixIn):
    name = _('URL Field')
    widget = forms.URLInput
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'


class IntegerField(forms.IntegerField, BaseFieldMixIn):
    name = _('Integer Field')
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'


class FloatField(forms.FloatField, BaseFieldMixIn):
    name = _('Float Field')
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'


class DecimalField(forms.DecimalField, BaseFieldMixIn):
    name = _('Decimal Field')
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'
