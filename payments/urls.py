from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import stripe_webhook, create_payout, DriverPayoutListView, PayoutViewSet

router = DefaultRouter()
router.register(r'payouts', PayoutViewSet, basename='payout')

urlpatterns = [
    path('webhook/stripe/', stripe_webhook, name='stripe-webhook'),
    path('payouts/create/', create_payout, name='admin-payout-create'),
    path('driver/payouts/', DriverPayoutListView.as_view(), name='driver-payouts-list-payments'),
]

urlpatterns += router.urls
