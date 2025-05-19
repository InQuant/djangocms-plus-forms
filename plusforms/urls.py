from django.urls import path
from .views import EmailVerificationView

urlpatterns = [
    path('verify-email/', EmailVerificationView.as_view(), name='verify_email'),
]
