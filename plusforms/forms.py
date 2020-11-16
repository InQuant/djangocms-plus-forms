import os
from uuid import uuid4

from django.conf import settings
from django import forms
from django.core.files import File
from django.core.exceptions import ValidationError
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

    def __init__(self, *args, name=None, request=None, **kwargs):

        initial = {}
        if kwargs.get('initial'):
            initial.update(kwargs.pop('initial'))

        if kwargs.get('instance'):
            # set form initial values as our instance model attributes are in
            # form_data not in the instance itself
            initial.update(**self.deserialize_form_data(kwargs.get('instance').form_data))

        self.name = name
        self.request = request
        super().__init__(*args, initial=initial, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data.update(self.serialize_form_data())

    def save(self, commit=True):
        """
        Put serialized data to form_data field, then save.
        """
        if self.errors:
            raise ValueError("Can't save, because form does not validate.")

        self.instance.form_data = self.cleaned_data

        if self.name:
            self.instance.name = self.name
        if self.request:
            self.instance.meta_data = self._get_meta_data(self.request)
            self.instance.by_user = self.request.user

        # handle upload for file fields
        for key, field in self.fields.items():
            if isinstance(field, FileField):
                value = field.widget.value_from_datadict(self.data, self.files, key)
                if isinstance(value, InMemoryUploadedFile):
                    new_file = handle_uploaded_file(value)
                    self.instance.form_data[key] = new_file.name
                    self.initial[key] = new_file

        return super().save(commit)

    def _get_meta_data(self, request):
        return {
            'host': request.META.get('HTTP_HOST'),
            'origin': request.META.get('HTTP_ORIGIN'),
            'referrer': request.META.get('HTTP_REFERER'),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'remote_ip': get_client_ip(request),
            'form_field_types': dict([(key, field.widget.type) for key, field in self.declared_fields.items()])
        }

    def serialize_form_data(self):
        """
        Takes form field values and calls "serialize_field" method for each field,
        if it is declared in the field class
        :return: Serialized data
        :rtype: dict
        """
        parsed_data = {}
        for key in self.declared_fields.keys():
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
