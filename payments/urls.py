from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PayoutViewSet, create_payout, stripe_webhook

router = DefaultRouter()
router.register(r"payouts", PayoutViewSet, basename="payout")

urlpatterns = [
    path("webhook/stripe/", stripe_webhook, name="stripe-webhook"),
    path("payouts/create/", create_payout, name="admin-payout-create"),
]

urlpatterns += router.urls
