from pprint import pprint

from django.contrib import admin

from plusforms.form_fields import get_available_form_fields
from plusforms.models import SubmittedForm


@admin.register(SubmittedForm)
class SubmittedFormAdmin(admin.ModelAdmin):
    change_form_template = "plusforms/admin/change_submitted_form.html"

    readonly_fields = ['form', 'by_user', ]
    exclude = ['form_data', 'meta_data', ]

    list_display = ['get_name', 'by_user', 'created_on', ]

    def get_name(self, obj):
        return obj.__str__()

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if obj.form:
            pi, pc = obj.form.get_plugin_instance()
            context['link_to_page'] = pi.placeholder.page.get_absolute_url()
            pprint(context['link_to_page'])

        return super(SubmittedFormAdmin, self).render_change_form(request, context, add, change, form_url, obj)

