import stripe
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from billing.models import Payment
from orders.models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY


# Stripe online charging
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
            return Response(
                {"error": "Order not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            total_amount = order.total_price * 100
            charge = stripe.Charge.create(
                amount=int(total_amount), currency="usd", source=stripe_token
            )
            Payment.objects.create(
                order=order, stripe_charge_id=charge.id, amount=order.total_price
            )
            order.status = "Paid"
            order.save()

            return Response(
                {"status": "Payment successful"}, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
