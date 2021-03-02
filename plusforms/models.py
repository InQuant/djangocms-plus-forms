from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models
from jsonfield import JSONField


class SubmittedForm(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=512)

    by_user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)

    form_data = JSONField()
    meta_data = JSONField()

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or str(self.uuid)
