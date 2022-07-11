import logging
import os
import typing
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

if typing.TYPE_CHECKING:
    from django.core.handlers.wsgi import WSGIRequest
    from django.db.models import QuerySet


logger = logging.getLogger(__name__)


def get_file_path(form_file_value: str):
    media_url = urlparse(form_file_value)
    media_path = media_url.path.replace(settings.MEDIA_URL[1:], '')
    return os.path.join(settings.MEDIA_ROOT, media_path)


def export_submitted_form_as_zip(model_admin: admin.ModelAdmin, request: 'WSGIRequest', queryset: 'QuerySet'):
    """
    Must be used with SubmittedForms Models
    Exports selected items. ZIP including media
    """
    from plusforms.models import SubmittedForm
    import zipfile, io, csv
    from tempfile import NamedTemporaryFile

    if not issubclass(queryset.model, SubmittedForm):
        logger.error(f'This action can only be performed on "{SubmittedForm.__class__.__name__}" subclasses!')
        return

    out_zip = io.BytesIO()
    out_csv = NamedTemporaryFile(delete=True)

    form_fields = queryset.last().meta_data['form_field_types']

    # filter for type "file" and return list of keys of filtered dict
    _file_fields = dict(filter(lambda f: f[1] == 'file', form_fields.items())).keys()

    with zipfile.ZipFile(out_zip, 'w') as _zip:
        csv_file = open(out_csv.name, 'w', newline='')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(form_fields.keys())

        submitted_form: SubmittedForm
        form_media = []
        for submitted_form in queryset:
            form_values = submitted_form.form_data
            if not isinstance(form_values, dict):
                continue

            row = []
            for field_name, field_type in form_fields.items():
                if field_type == "file":
                    form_media.append({
                        'filepath': get_file_path(form_values[field_name]),
                        'arcname': form_values[field_name],
                    })

                row.append(form_values.get(field_name))
            csv_writer.writerow(row)

        [_zip.write(media['filepath'], arcname=media['arcname']) for media in form_media]

        csv_file.close()
        out_csv.seek(0)
        _zip.write(csv_file.name, 'export.csv', )

    out_zip.seek(0)

    # make downloadable
    response = HttpResponse(out_zip, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename=export_{timezone.now().timestamp()}.zip'

    return response


export_submitted_form_as_zip.short_description = _('Export selected forms')