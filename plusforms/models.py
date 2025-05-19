from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

class SubmittedForm(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=512)

    by_user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    email_to_verify = models.EmailField(blank=True, default='')
    is_processed = models.BooleanField(default=True)

    form_data = models.JSONField()
    meta_data = models.JSONField()

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or str(self.uuid)


class EmailVerification(models.Model):
    email = models.EmailField(unique=True)
    verified = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.email}: {self.verified}'

    def mark_verified(self):
        self.verified = True
        self.verified_at = timezone.now()
        self.save()
