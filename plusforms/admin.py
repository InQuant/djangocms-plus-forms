from django.contrib import admin

from plusforms.models import SubmittedForm


@admin.register(SubmittedForm)
class SubmittedFormAdmin(admin.ModelAdmin):
    change_form_template = "plusforms/admin/change_submitted_form.html"

    readonly_fields = ['by_user', 'uuid']
    exclude = ['form_data', 'meta_data', ]

    list_display = ['get_name', 'by_user', 'created_on', ]

    def get_name(self, obj):
        return obj.__str__()
