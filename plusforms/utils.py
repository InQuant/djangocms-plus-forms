from django.http import HttpRequest
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.urls import reverse

from cmsplus.models import PlusItem

from .models import SubmittedForm

import json

signer = TimestampSigner()

def generate_verification_token(email):
    return signer.sign(email)

def verify_token(token, max_age=86400):
    try:
        email = signer.unsign(token, max_age=max_age)
        return email
    except (BadSignature, SignatureExpired):
        return None

MESSAGE = '''Click here to verify your email: %s

If you didn't used one of our form submissions - please ignore this email!

Kind Regards, your team of %s
'''

def send_email_confirmation(request:HttpRequest, email:str):
    token = generate_verification_token(email)
    link = request.build_absolute_uri(
        reverse('plusforms:verify_email') + f'?token={token}'
    )
    site = get_current_site(request)

    send_mail(
        subject='Verify your email',
        message=MESSAGE % (link, site.domain),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )


NOTIFY_MESSAGE = '''A new "%s" was submitted by user "%s":

%s

'''

def send_notification_email(form_name:str, obj:SubmittedForm, email:str):
    user_name = obj.by_user.email or 'anonymous'
    pretty = json.dumps(obj.form_data, indent=4, sort_keys=True)
    send_mail(
        subject=f'New: {form_name}',
        message=NOTIFY_MESSAGE % (form_name, user_name, pretty),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )

def handle_unprocessed_forms(email:str):
    """ processes all forms with given email, which are not processed so far.

    Args:
        email (str): the email address
    """
    for sf in SubmittedForm.objects.filter(email_to_verify=email, is_processed=False):
        config = sf.meta_data.get('plugin', {}).get('glossary', {})
        if config.get('notify'):
            send_notification_email(config.get('name'), sf, config.get('notify'))
