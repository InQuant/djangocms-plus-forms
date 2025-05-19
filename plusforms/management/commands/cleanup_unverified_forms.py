from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from plusforms.models import EmailVerification, SubmittedForm

class Command(BaseCommand):
    help = "Deletes EmailVerification entries and related Subfomrs older than 24 hours which are not verified."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        ev_qs = EmailVerification.objects.filter(verified=False, created__lt=cutoff)
        emails = [ev.email for ev in ev_qs]
        sf_qs = SubmittedForm.objects.filter(email_to_verify__in=emails)
        count = sf_qs.count()
        sf_qs.delete()
        ev_qs.delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {count} unverified email(s) and forms older than 24 hours."))
