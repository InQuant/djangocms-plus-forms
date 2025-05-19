from django.views.generic import TemplateView
from django.utils.safestring import mark_safe
from django.contrib import messages
from .models import EmailVerification
from .utils import verify_token, handle_unprocessed_forms

import logging
logger = logging.getLogger(__name__)

class EmailVerificationView(TemplateView):
    template_name = 'plusforms/email_verified.html'  # Display result

    def get(self, request, *args, **kwargs):
        token = request.GET.get('token')
        email = verify_token(token)

        if email:
            try:
                ev, _ = EmailVerification.objects.get_or_create(email=email)
                if not ev.verified:
                    ev.mark_verified()
                    handle_unprocessed_forms(email)
                message = "✅ Your email has been verified. Your request will now be processed."
            except Exception as e:
                message = "❌ Your request cannot be handled - please forward to support."
                logger.exception(e)
        else:
            message = "❌ Invalid or expired verification link."

        # Optional: message as Django messages
        messages.info(request, mark_safe(message))

        return self.render_to_response(self.get_context_data(message=message))
