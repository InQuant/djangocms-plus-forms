from pprint import pprint

from django.contrib import admin

from plusforms.models import SubmittedForm


@admin.register(SubmittedForm)
class SubmittedFormAdmin(admin.ModelAdmin):
    change_form_template = "plusforms/admin/change_submitted_form.html"

    readonly_fields = ['form', 'by_user', 'uuid']
    exclude = ['form_data', 'meta_data', ]

    list_display = ['get_name', 'by_user', 'created_on', ]

    def get_name(self, obj):
        return obj.__str__()

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if obj.form:
            pi, pc = obj.form.get_plugin_instance()
            context['link_to_page'] = pi.placeholder.page.get_absolute_url() if pi.placeholder.page else None
            context['obj_form'] = obj.form

        return super(SubmittedFormAdmin, self).render_change_form(request, context, add, change, form_url, obj)

