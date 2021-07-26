import csv
from pprint import pprint

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from plusforms.models import SubmittedForm


@admin.register(SubmittedForm)
class SubmittedFormAdmin(admin.ModelAdmin):
    ordering = ['-updated_on', ]
    change_form_template = "plusforms/admin/change_submitted_form.html"
    actions = ['export_fields_csv', ]
    list_filter = ['name', ]
    readonly_fields = ['name', 'get_description_meta_data', 'get_by_user', 'uuid', 'get_form_id_meta_data']
    exclude = ['form_data', 'meta_data', ]
    list_display = ['get_name', 'by_user', 'updated_on']

    def get_by_user(self, obj):
        link_href = reverse(
            f'admin:{get_user_model()._meta.app_label}_{get_user_model()._meta.model_name}_change',
            args=(obj.by_user.id, )
        )

        link = f'<a href="{link_href}" target="_blank">{obj.by_user}</a>'
        display_str = [
            link,
            obj.by_user.email if hasattr(obj.by_user, 'email') else None,
            obj.by_user.get_full_name() if hasattr(obj.by_user, 'get_full_name') else None,
        ]
        return format_html('<br>'.join(filter(None, display_str)))

    get_by_user.short_description = get_user_model()._meta.verbose_name

    def get_name(self, obj):
        return str(obj)

    get_name.short_description = _('Name')

    def get_description_meta_data(self, obj):
        try:
            return obj.meta_data['plugin']['glossary']['description'] or "-"
        except (KeyError, TypeError):
            return "-"

    get_description_meta_data.short_description = _('Description')

    def get_form_id_meta_data(self, obj):
        try:
            return obj.meta_data['plugin']['glossary']['form_id']
        except (KeyError, TypeError):
            return "-"

    get_form_id_meta_data.short_description = _('Form identifier')

    def export_fields_csv(self, request, queryset):
        if not request.GET.get('name'):
            messages.error(request, _(f'Error! Please first filter objects by "Name"'))
            return

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="export.csv"'

        writer = csv.writer(response)

        obj = queryset.last()
        keys = obj.form_data.keys()
        writer.writerow(keys)

        for obj in queryset.all():
            writer.writerow(obj.form_data.values())

        return response

    export_fields_csv.short_description = _('Export rows to CSV (filtered by Name)')
