import importlib
import logging
import os
import sys
from typing import List, Tuple

from django import forms
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.core.exceptions import ValidationError, FieldError
from django.core.files import File
from django.core.files.images import get_image_dimensions
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import FileExtensionValidator
from django.db.models import QuerySet
from django.forms import Field
from django.utils.datetime_safe import datetime
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _

from plusforms.form_widgets import CaptchaWidget

logger = logging.getLogger('plusforms')


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
    'CaptchaField',
    'SelectField',
    'SelectMultipleField',
]


class BaseFieldMixIn:
    in_submitted_form_data = True

    def serialize_field(self, value):
        return value

    def deserialize_field(self, value):
        return value

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def bound_field_values(cls, field_data):
        field_id = field_data['field_id']

        _attrs = {
            'placeholder': field_data.get('field_placeholder', ''),
            'id': field_id,
            'class': getattr(cls, 'widget_class', ''),
        }
        input_type = getattr(cls.widget, 'input_type', '')

        widget = cls.widget(attrs=_attrs)

        widget.name = field_id
        widget.type = input_type

        field_kwargs = {
            'label': field_data.get('label', ''),
            'help_text': field_data.get('help_text', field_data.get('value', '')),
            'widget': widget,
            'required': field_data.get('required', False),
        }
        return field_kwargs

    @classmethod
    def bound_field(cls, field_data):
        field_values = cls.bound_field_values(field_data)
        if field_values and isinstance(field_values, dict):
            field = cls(**field_values)
            return field
        return cls()


class FileFieldMixin(BaseFieldMixIn):
    @classmethod
    def bound_field_values(cls, field_data):
        field_kwargs = super(FileFieldMixin, cls).bound_field_values(field_data)
        allowed_extensions = field_data.get('allowed_extensions')
        if allowed_extensions:
            field_kwargs['allowed_extensions'] = allowed_extensions
            field_kwargs['help_text'] += " (%s) " % ", ".join(allowed_extensions)

        max_mb = field_data.get('max_mb')
        if max_mb:
            field_kwargs['max_mb'] = max_mb
            field_kwargs['help_text'] += " Max. %s MB." % max_mb

        return field_kwargs


class InputField(forms.CharField, BaseFieldMixIn):
    name = _('Text field')
    template_name = "plusforms/fields/input.html"
    widget_class = 'form-control'

    @classmethod
    def bound_field_values(cls, field_data):
        field_kwargs = super(InputField, cls).bound_field_values(field_data)
        max_length = field_data.get('max_length')
        if max_length:
            field_kwargs['max_length'] = max_length
            field_kwargs['help_text'] += (' %s' % _("Max. length: %s" % max_length))
        return field_kwargs


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
class ExactPixelResolutionValidator:
    message = _(
        "Image pixel resolution must be %(px_width)s x %(px_height)s. "
        "Uploaded image resolution is %(width)s x %(height)s."
    )
    code = 'invalid_pixel_resolution'

    def __init__(self, px_width=None, px_height=None, message=None, code=None):
        self.px_width = px_width
        self.px_height = px_height

        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

    def __call__(self, file: InMemoryUploadedFile):
        width, height = get_image_dimensions(file)

        if self.px_height != height or self.px_width != width:
            raise ValidationError(
                self.message,
                code=self.code,
                params={
                    'px_width': self.px_width,
                    'px_height': self.px_height,
                    'width': width,
                    'height': height,
                }
            )


@deconstructible
class MinPixelResolutionValidator:
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
    def __init__(self, *, min_px_width=None, min_px_height=None, px_width=None, px_height=None, **kwargs):
        super().__init__(**kwargs)
        if min_px_width is not None or min_px_height is not None:
            self.validators.append(MinPixelResolutionValidator(min_px_width, min_px_height))

        if px_width and px_height:
            self.validators.append(ExactPixelResolutionValidator(px_width=px_width, px_height=px_height))


class FileField(FileValidationMixin, forms.FileField, FileFieldMixin):
    widget = forms.ClearableFileInput
    name = _('File Field')
    template_name = "plusforms/fields/file.html"


class ImageField(ImageValidationMixIn, forms.ImageField, FileFieldMixin):
    widget = forms.FileInput
    name = _('Image Field')
    template_name = "plusforms/fields/file.html"

    @classmethod
    def bound_field_values(cls, field_data):
        field_kwargs = super(ImageField, cls).bound_field_values(field_data)

        min_w = field_data.get('min_px_width')
        if min_w:
            field_kwargs['min_px_width'] = min_w

        min_h = field_data.get('min_px_height')
        if min_h:
            field_kwargs['min_px_height'] = min_h

        if min_w or min_h:
            field_kwargs['help_text'] += ' Minimum %s x %s. ' % (
                "*" if not min_w else "%spx" % min_w,
                "*" if not min_h else "%spx" % min_h,
            )

        exact_width = field_data.get('px_width')
        exact_height = field_data.get('px_height')
        if (exact_width and exact_height) and (not min_w or not min_h):
            field_kwargs['px_width'] = exact_width
            field_kwargs['px_height'] = exact_height

            field_kwargs['help_text'] += ' Pixel format: %s x %s. ' % (exact_width, exact_height, )

        return field_kwargs


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


class CaptchaField(forms.Field, BaseFieldMixIn):
    in_submitted_form_data = False
    widget = CaptchaWidget
    template_name = "plusforms/fields/captcha.html"
    widget_class = 'form-control'

    def validate(self, field_value):
        value_signed, value = field_value
        _value = signing.loads(value_signed)

        if str(_value) != value:
            raise ValidationError(
                _('Wrong Captcha. Please check your Input.')
            )


class SelectFieldMixIn(BaseFieldMixIn):
    template_name = 'plusforms/fields/choice.html'
    _choices = None

    @classmethod
    def get_qs_from_content_type(cls, content_type_id: int, filter_kwargs: dict = None) -> QuerySet():
        try:
            ct = ContentType.objects.get(id=content_type_id)
        except ContentType.DoesNotExist:
            raise ContentType.DoesNotExist(
                f'Couldn\'t find ContentType with id {content_type_id} for generating choices'
            )

        if filter_kwargs:
            try:
                return ct.model_class().objects.filter(**filter_kwargs)
            except FieldError as e:
                logger.error(f'Can not filter model "{ct.model_class().__name__}" with {filter_kwargs}. {e}')
                return ct.model_class().objects.none()

        else:
            return ct.model_class().objects.all()

    @staticmethod
    def get_tuple_from_data(data):
        return [(obj['value'], obj['name']) for obj in data]

    @staticmethod
    def get_tuple_from_qs(queryset: QuerySet, display_attribute_name: str = None) -> List[Tuple]:
        """
        :param queryset: QuerySet to make tuple of
        :param display_attribute_name: Change displayed value in select by getting given attribute from object.
        """
        r = []
        ct = ContentType.objects.get_for_model(queryset.model)
        for obj in queryset:
            value = f'ct_{ct.id}_{obj.id}'
            display_str = str(obj)
            if display_attribute_name:
                display_str = getattr(obj, display_attribute_name, obj)
            r.append((value, display_str))
        return r

    @classmethod
    def bound_field_values(cls, field_data):
        field_kwargs = super(SelectFieldMixIn, cls).bound_field_values(field_data)
        choices_static = field_data.get('choices_static')
        choices_dynamic_content_type_id = field_data.get('choices_dynamic')
        choices_dynamic_filter = field_data.get('choices_dynamic_filter')
        choices_allow_empty = field_data.get('choices_allow_empty')

        choices = []

        if choices_dynamic_content_type_id:
            choices = cls.get_tuple_from_qs(
                cls.get_qs_from_content_type(
                    choices_dynamic_content_type_id,
                    choices_dynamic_filter if bool(choices_dynamic_filter) else None
                )
            )
        elif choices_static:
            choices = cls.get_tuple_from_data(choices_static)

        if choices_allow_empty:
            choices.insert(0, ('', '------'))

        field_kwargs['choices'] = choices
        return field_kwargs


class SelectField(forms.ChoiceField, SelectFieldMixIn):
    widget_class = 'form-control'
    widget = forms.Select


class SelectMultipleField(forms.MultipleChoiceField, SelectFieldMixIn):
    widget_class = 'form-control'
    widget = forms.SelectMultiple
