import logging

import stripe
from django.conf import settings
from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import Payment
from orders.models import Order

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


# Stripe online charging (legacy token-based)
class CreateChargeView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["stripeToken", "order_id"],
            properties={
                "stripeToken": openapi.Schema(type=openapi.TYPE_STRING),
                "order_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        )
    )
    def post(self, request, *args, **kwargs):
        stripe_token = request.data.get("stripeToken")
        order_id = request.data.get("order_id")

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            total_amount = order.total_price * 100
            charge = stripe.Charge.create(amount=int(total_amount), currency="usd", source=stripe_token)
            Payment.objects.create(order=order, stripe_charge_id=charge.id, amount=order.total_price)
            order.status = "Paid"
            order.save()

            return Response({"status": "Payment successful"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StripeCheckoutSessionView(APIView):
    """
    POST /api/v1/payments/checkout-session/
    Creates a Stripe Checkout Session and returns the redirect URL.
    Requires an authenticated user (JWT token) and a valid `order_id`.
    Enhanced error handling and logging are added.
    """

    permission_classes = [IsAuthenticated]
    # Use logger for detailed debugging
    logger = logging.getLogger(__name__)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["order_id"],
            properties={
                "order_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        )
    )
    def post(self, request):
        order_id = request.data.get("order_id")

        if not order_id:
            logger.warning("Checkout session request missing order_id from user %s", request.user)
            return Response(
                {"error": "order_id kiritilishi shart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure the user is authenticated – IsAuthenticated should handle this, but add explicit guard
        if not request.user or not request.user.is_authenticated:
            logger.warning("Unauthenticated access to checkout session endpoint")
            return Response(
                {"error": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            logger.error("Order %s not found for user %s", order_id, request.user)
            return Response(
                {"error": "Buyurtma topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status == "Paid":
            return Response(
                {"error": "Bu buyurtma allaqachon to'langan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build line items from OrderItems
        line_items = []
        order_items = order.order_items.select_related("product").all()
        for oi in order_items:
            product_name = oi.product.name if oi.product else f"Mahsulot #{oi.id}"
            unit_price = int(oi.price_at_order * 100)  # Stripe uses cents

            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": unit_price,
                        "product_data": {
                            "name": product_name,
                        },
                    },
                    "quantity": oi.quantity,
                }
            )

        if not line_items:
            return Response(
                {"error": "Buyurtmada mahsulotlar topilmadi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build success and cancel URLs
        host = request.build_absolute_uri("/")
        success_url = f"{host}order/?payment=success&order_id={order.id}"
        cancel_url = f"{host}order/?payment=cancelled&order_id={order.id}"

        try:
            # Update order payment_method to 'card' for Stripe
            order.payment_method = "card"
            order.save(update_fields=["payment_method"])

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "order_id": str(order.id),
                    "user_id": str(request.user.id),
                },
            )
            logger.info("Created Stripe checkout session %s for order %s", checkout_session.id, order.id)
            return Response(
                {
                    "success": True,
                    "checkout_url": checkout_session.url,
                    "session_id": checkout_session.id,
                },
                status=status.HTTP_200_OK,
            )
        except stripe.error.AuthenticationError as auth_err:
            logger.error("Stripe authentication error: %s", auth_err)
            return Response(
                {"error": "Stripe API kaliti noto'g'ri sozlangan. Admin bilan bog'laning."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except stripe.error.StripeError as stripe_err:
            logger.error("Stripe error during checkout session creation: %s", stripe_err)
            return Response(
                {"error": f"Stripe xatosi: {str(stripe_err)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.exception("Unexpected error while creating Stripe checkout session")
            return Response(
                {"error": f"Server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StripeWebhookView(APIView):
    """
    POST /api/v1/payments/webhook/
    Stripe webhook — to'lov muvaffaqiyatli bo'lganda order statusini yangilash.
    """

    permission_classes = []  # Stripe webhook — autentifikatsiya kerak emas
    authentication_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

        try:
            if webhook_secret:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            else:
                import json

                event = json.loads(payload)
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response({"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)

        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            order_id = session.get("metadata", {}).get("order_id")

            if order_id:
                with transaction.atomic():
                    try:
                        order = Order.objects.select_for_update().get(id=int(order_id))
                        if order.status != "Paid":
                            order.status = "Paid"
                            order.save(update_fields=["status"])

                            Payment.objects.create(
                                order=order,
                                stripe_charge_id=session.get("payment_intent", session.get("id", "")),
                                amount=order.total_price,
                                status="completed",
                                payment_method="card",  # Stripe checkout is card payment
                            )

                            # Log to History and AuditLog
                            def log_stripe_payment():
                                user = order.user

                                # History - har bir user uchun
                                try:
                                    from pharmacy.models.misc import UserHistory

                                    UserHistory.objects.create(
                                        user=user,
                                        action="STRIPE_PAYMENT",
                                        description=f"Buyurtma #{order.id} Stripe orqali to'landi. Jami: {order.total_price} so'm.",
                                        metadata={
                                            "order_id": order.id,
                                            "total_price": str(order.total_price),
                                            "payment_method": "card",
                                        },
                                    )
                                except:
                                    pass

                                # AuditLog - faqat admin uchun (role='admin', is_superuser=True, is_staff=True)
                                if user.role == "admin" and user.is_superuser and user.is_staff:
                                    from security.models import AuditLog

                                    AuditLog.objects.create(
                                        user=user,
                                        action="STRIPE_PAYMENT",
                                        description=f"Buyurtma #{order.id} Stripe orqali muvaffaqiyatli to'landi. Jami: {order.total_price} so'm.",
                                        target_type="order",
                                        target_id=order.id,
                                        meta={
                                            "order_id": order.id,
                                            "total_price": str(order.total_price),
                                            "payment_method": "card",
                                            "session_id": session.get("id"),
                                        },
                                    )

                            transaction.on_commit(log_stripe_payment)
                    except Order.DoesNotExist:
                        pass

        return Response({"status": "ok"}, status=status.HTTP_200_OK)
