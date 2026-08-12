import json
import logging

import stripe
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from users.models import DeliveryDriver

from .models import Payout
from .serializers import AdminPayoutCreateSerializer, PayoutSerializer

logger = logging.getLogger(__name__)

# Stripe API kalitini o'rnatish
stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
@api_view(["POST"])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        logger.warning(f"Stripe Webhook ValueError: {e}")
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.warning(f"Stripe Webhook SignatureVerificationError: {e}")
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Handle the event
    if event["type"] == "transfer.succeeded":
        transfer = event["data"]["object"]
        # Payout statusini yangilash
        try:
            payout = Payout.objects.get(stripe_transfer_id=transfer["id"])
            payout.status = "Completed"
            payout.processed_at = timezone.now()
            payout.save()
            logger.info(
                f"Stripe Transfer Succeeded: Payout {payout.id} updated to completed."
            )
        except Payout.DoesNotExist:
            logger.warning(
                f"Stripe Transfer Succeeded: Payout with transfer ID {transfer['id']} not found."
            )
    elif event["type"] == "transfer.failed":
        transfer = event["data"]["object"]
        # Payout statusini failed ga yangilash
        try:
            payout = Payout.objects.get(stripe_transfer_id=transfer["id"])
            payout.status = "Failed"
            payout.error_message = transfer.get("failure_message", "Transfer failed")
            payout.save()
            logger.warning(
                f"Stripe Transfer Failed: Payout {payout.id} updated to failed."
            )
        except Payout.DoesNotExist:
            logger.warning(
                f"Stripe Transfer Failed: Payout with transfer ID {transfer['id']} not found."
            )
    else:
        logger.info(f"Unhandled Stripe event type {event['type']}")

    return Response(status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])  # Changed permission to IsAdminUser
def create_payout(request):
    """
    Endpoint for creating a payout for a driver.
    This would typically be triggered by an admin or an automated process.
    """
    serializer = AdminPayoutCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    driver_id = serializer.validated_data["driver_id"]
    amount_gross = serializer.validated_data["amount_gross"]
    tax_amount = serializer.validated_data["tax_amount"]
    commission_amount = serializer.validated_data["commission_amount"]
    period_start = serializer.validated_data.get("period_start")
    period_end = serializer.validated_data.get("period_end")

    try:
        driver_profile = DeliveryDriver.objects.get(id=driver_id)
    except DeliveryDriver.DoesNotExist:
        return Response(
            {"detail": "Driver not found."}, status=status.HTTP_404_NOT_FOUND
        )

    net_amount = amount_gross - tax_amount - commission_amount

    if net_amount < 0:
        return Response(
            {"detail": "Net amount cannot be negative."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not driver_profile.stripe_account_id:
        return Response(
            {"detail": "Driver does not have a connected Stripe account for payouts."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Stripe transfer create
        transfer = stripe.Transfer.create(
            amount=int(net_amount * 100),  # Stripe amounts are in cents
            currency="usd",  # Yoki sizning mahalliy valyutangiz
            destination=driver_profile.stripe_account_id,
            description=f"Driver payout for {driver_profile.user.email or driver_profile.user.phone_number}",
            metadata={
                "driver_id": str(driver_profile.id),
                "user_id": str(driver_profile.user.id),
            },
        )

        payout = Payout.objects.create(
            driver=driver_profile,
            amount_gross=amount_gross,  # Changed to amount_gross
            tax_amount=tax_amount,
            commission_amount=commission_amount,
            net_amount=net_amount,
            stripe_transfer_id=transfer.id,
            status="Pending",  # Status webhook orqali yangilanadi
            period_start=period_start,
            period_end=period_end,
        )

        serializer = PayoutSerializer(payout)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except stripe.error.StripeError as e:
        logger.error(f"Stripe transfer failed for driver {driver_id}: {e}")
        return Response(
            {"detail": f"Stripe transfer failed: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


from rest_framework import permissions, status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payout
from .serializers import PayoutSerializer


class PayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    permission_classes = [IsAdminUser]
