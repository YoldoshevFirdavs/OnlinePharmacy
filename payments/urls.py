from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter

from billing.views import CreateChargeView, StripeCheckoutSessionView, StripeWebhookView

from .views import SalaryViewSet, create_salary

router = DefaultRouter()
router.register(r"salaries", SalaryViewSet, basename="salary")

urlpatterns = [
    path("salaries/create/", create_salary, name="admin-salary-create"),
    path("charge/", CreateChargeView.as_view(), name="payment-charge"),
    path("checkout-session/", StripeCheckoutSessionView.as_view(), name="stripe-checkout-session"),
    path("webhook/", csrf_exempt(StripeWebhookView.as_view()), name="stripe-webhook"),
]

urlpatterns += router.urls
