from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import format_html

from plusforms.models import SubmittedForm


@admin.register(SubmittedForm)
class SubmittedFormAdmin(admin.ModelAdmin):
    change_form_template = "plusforms/admin/change_submitted_form.html"

    readonly_fields = ['name', 'get_by_user', 'uuid', ]
    exclude = ['form_data', 'meta_data', ]

    list_display = ['get_name', 'by_user', 'created_on', ]

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
        return obj.__str__()
