from cmsplus.models import PlusPlugin
from django.contrib.auth import get_user_model
from django.db import models
from jsonfield import JSONField


class SubmittedForm(models.Model):
    form = models.ForeignKey(PlusPlugin, on_delete=models.SET_NULL, null=True, blank=True)
    by_user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)

    form_data = JSONField(null=True, blank=True)
    meta_data = JSONField(null=True, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        if not self.form:
            return super(SubmittedForm, self).__str__()
        pi, pc = self.form.get_plugin_instance()
        return pi.glossary.get('name') or pi.glossary.get('form_id')
