import os
from copy import deepcopy
from uuid import uuid4

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.forms.fields import FileField

from .models import SubmittedForm


class PlusFormBase(forms.ModelForm):
    """
    BaseForm for PlusForms.
    This ModelForm references to a SubmittedForm Model in order to write and read
    the glossary (form_data JSONField) and meta_data JSONField attribute.
    """

    class Meta:
        model = SubmittedForm
        exclude = ['name', 'by_user', 'form_data', 'meta_data']

    def __init__(self, *args, name=None, request=None, plugin_instance=None, **kwargs):
        if plugin_instance:
            self.plugin_instance = plugin_instance

        initial = {}
        if kwargs.get('initial'):
            initial.update(kwargs.pop('initial'))

        if kwargs.get('instance'):
            # set form initial values as our instance model attributes are in
            # form_data not in the instance itself
            initial.update(**self.deserialize_form_data(kwargs.get('instance').form_data))

        self.patch_file_fields(initial)

        self.name = name
        self.request = request
        super().__init__(*args, initial=initial, **kwargs)

    def patch_file_fields(self, initial: dict):
        """
        Monkey patch: Set required to False if inital is set in FileField.
        The expected behavoir should be: Field is required on create but optional on updates.
        """
        for field_name, value in self.base_fields.items():
            if issubclass(value.__class__, FileField):
                if not initial.get(field_name):
                    continue
                self.base_fields[field_name].required = False

    def clean(self):
        self.cleaned_data = super().clean()
        self.cleaned_data.update(self.serialize_form_data())

        # check if field value should be added to submitted forms via cleaned data (e.g. Captcha Field)
        _cleaned_data = deepcopy(self.cleaned_data)
        for key in _cleaned_data.keys():
            if not self.fields[key].in_submitted_form_data:
                self.cleaned_data.pop(key)

        return self.cleaned_data

    def save(self, commit=True):
        """
        Put serialized data to form_data field, then save.
        """
        if self.errors:
            raise ValueError("Can't save, because form does not validate.")

        self.instance.form_data = self.cleaned_data

        _glossary = self.plugin_instance.glossary
        self.instance.name = _glossary.get('name', _glossary['form_id'])

        if self.request:
            self.instance.meta_data = self._get_meta_data(self.request)
            self.instance.by_user = self.request.user if self.request.user.is_authenticated else None

        # handle upload for file fields
        for key, field in self.fields.items():
            if isinstance(field, FileField):
                value = field.widget.value_from_datadict(self.data, self.files, key)
                if issubclass(value.__class__, File):
                    new_file = handle_uploaded_file(value)
                    self.instance.form_data[key] = new_file.name
                    self.initial[key] = new_file

        return super().save(commit)

    def _get_meta_data(self, request):
        meta_data = {
            'host': request.META.get('HTTP_HOST'),
            'origin': request.META.get('HTTP_ORIGIN'),
            'referrer': request.META.get('HTTP_REFERER'),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'remote_ip': get_client_ip(request),
            'form_field_types': dict([(key, field.widget.type) for key, field in self.declared_fields.items()]),
        }
        if self.plugin_instance:
            meta_data.update({
                'plugin': {
                    'plugin_id': self.plugin_instance.id,
                    'plugin_class': self.plugin_instance.__class__.__name__,
                    'glossary': self.plugin_instance.glossary,
                }
            })
        return meta_data

    def serialize_form_data(self):
        """
        Takes form field values and calls "serialize_field" method for each field,
        if it is declared in the field class
        :return: Serialized data
        :rtype: dict
        """
        parsed_data = {}
        for key, field in self.declared_fields.items():
            value = self.cleaned_data.get(key)
            if key.startswith('_'):
                continue

            field = self.fields.get(key)
            if hasattr(field, "serialize_field") and callable(field.serialize_field):
                parsed_data[key] = field.serialize_field(value)
            else:
                parsed_data[key] = value
        return parsed_data

    def deserialize_form_data(self, data=None):
        """
        Deserialize data from form_data field into dict. Opposite of serialize function (see above)
        :return: Data
        :rtype: dict:
        """
        parsed_dict = {}
        data = data or self.data

        for field_name in self.declared_fields:
            value = data.get(field_name, None)

            field = self.declared_fields.get(field_name)
            if hasattr(field, "deserialize_field"):
                deserialize_field = getattr(field, "deserialize_field")
                if callable(deserialize_field):
                    try:
                        parsed_dict[field_name] = deserialize_field(value)
                    except ValidationError as e:
                        self._update_errors(e)
            else:
                parsed_dict[field_name] = value

        return parsed_dict


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def handle_uploaded_file(f: InMemoryUploadedFile):
    new_name = "{prefix}_{name}".format(
        prefix=uuid4(),
        name=f.name,
    )
    media_root = getattr(settings, 'MEDIA_ROOT')

    upload_folder = getattr(settings, 'PLUSFORMS_MEDIA_UPLOAD', 'plusforms')

    upload_media_root = os.path.join(media_root, upload_folder)

    if not os.path.exists(upload_media_root):
        os.makedirs(upload_media_root)

    path_name = os.path.join(upload_media_root, new_name)

    with open(path_name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    # return full_name of new created file
    return File(
        file=open(os.path.join(media_root, upload_folder, new_name)),
        name=os.path.join(upload_folder, new_name))
