import logging
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Cart, CartItem, Order, OrderItem
from pharmacy.models import Medicine
from security.models import AuditLog

logger = logging.getLogger(__name__)


class CartAddAPIView(APIView):
    """
    POST /api/v1/cart/add/
    Savatchaga mahsulot qo'shish yoki miqdorini oshirish.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity", 1)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                quantity = 1
        except (ValueError, TypeError):
            quantity = 1

        if not product_id:
            return Response({"error": "product_id kiritilishi shart."}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Medicine, id=product_id)

        with transaction.atomic():
            cart, _ = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.select_for_update().get_or_create(
                cart=cart, product=product, defaults={"quantity": quantity}
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save(update_fields=["quantity"])

            # Calculate updated summary
            total_items = sum(item.quantity for item in cart.items.all())
            cart_total = sum(item.quantity * item.product.price for item in cart.items.select_related("product").all())

        return Response(
            {
                "success": True,
                "message": f"{product.name} savatchaga qo'shildi.",
                "item_count": total_items,
                "cart_total": float(cart_total),
            },
            status=status.HTTP_200_OK,
        )


class CartSummaryAPIView(APIView):
    """
    GET /api/v1/cart/summary/
    Savatchadagi jami mahsulotlar soni va umumiy narx xulosasi.
    """

    permission_classes = []  # Allow anonymous — returns empty cart for non-auth users

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"item_count": 0, "cart_total": 0.0, "items": []}, status=status.HTTP_200_OK)

        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return Response({"item_count": 0, "cart_total": 0.0, "items": []}, status=status.HTTP_200_OK)

        items_qs = cart.items.select_related("product").all()
        item_count = sum(item.quantity for item in items_qs)
        cart_total = sum(item.quantity * item.product.price for item in items_qs)

        items_data = []
        for item in items_qs:
            img_url = "/static/images/default/default_product.png"
            try:
                if item.product.main_image and item.product.main_image.name:
                    img_url = item.product.main_image.url
            except (ValueError, AttributeError):
                img_url = "/static/images/default/default_product.png"

            items_data.append(
                {
                    "id": item.id,
                    "product_id": item.product.id,
                    "product_name": item.product.name,
                    "product_price": float(item.product.price),
                    "product_image": img_url,
                    "quantity": item.quantity,
                    "subtotal": float(item.quantity * item.product.price),
                }
            )

        return Response(
            {"item_count": item_count, "cart_total": float(cart_total), "items": items_data}, status=status.HTTP_200_OK
        )


class CheckoutAPIView(APIView):
    """
    POST /api/v1/checkout/
    Savatchadagi mahsulotlarni tekshirib Order va OrderItem yaratish.
    Stock select_for_update() bilan atomik bloklanadi.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        address = request.data.get("address", "").strip() or getattr(user, "address", "") or "Manzil kiritilmagan"
        phone = request.data.get("phone", "").strip()
        name = request.data.get("name", "").strip()

        # Combine recipient details cleanly into order address field if provided
        order_address_details = address
        if phone or name:
            contact_parts = []
            if name:
                contact_parts.append(f"Qabul qiluvchi: {name}")
            if phone:
                contact_parts.append(f"Tel: {phone}")
            order_address_details = f"{address} ({', '.join(contact_parts)})"

        with transaction.atomic():
            cart = Cart.objects.filter(user=user).first()
            if not cart:
                return Response({"error": "Savatcha topilmadi."}, status=status.HTTP_400_BAD_REQUEST)

            cart_items = list(CartItem.objects.select_for_update().filter(cart=cart).select_related("product"))

            if not cart_items:
                return Response({"error": "Savatchangiz bo'sh."}, status=status.HTTP_400_BAD_REQUEST)

            total_amount = Decimal("0.00")

            # Stock check with select_for_update on Medicine
            for item in cart_items:
                product = Medicine.objects.select_for_update().filter(id=item.product_id).first()
                if not product:
                    return Response(
                        {"error": f"{item.product.name} mahsuloti mavjud emas."}, status=status.HTTP_400_BAD_REQUEST
                    )

                if product.stock < item.quantity:
                    return Response(
                        {
                            "error": f"{product.name} uchun yetarli qoldiq yo'q. Mavjud: {product.stock} ta, so'ralgan: {item.quantity} ta."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                total_amount += Decimal(str(product.price)) * item.quantity

            # Get payment method from request (cash or card)
            payment_method = request.data.get("payment_method", "cash").lower()

            # Map any stripe/online payment to 'card'
            if payment_method in ["online_stripe", "stripe", "card_payment", "online"]:
                payment_method = "card"

            if payment_method not in ["cash", "card"]:
                payment_method = "cash"

            # Create Order
            order = Order.objects.create(
                user=user,
                total_price=total_amount,
                status="Pending",
                address=order_address_details,
                payment_method=payment_method,  # Save payment_method to order
                created_at=timezone.now(),
            )

            # Create OrderItems and reduce stock
            for item in cart_items:
                product = Medicine.objects.select_for_update().get(id=item.product_id)
                OrderItem.objects.create(
                    order=order, product=product, quantity=item.quantity, price_at_order=product.price
                )
                product.stock -= item.quantity
                product.save(update_fields=["stock"])

            # Clear cart
            cart.items.all().delete()

            # Record AuditLog and History inside on_commit
            def log_checkout():
                # History - har bir user uchun
                pass

                # Create order history entry
                history_description = (
                    f"Buyurtma #{order.id} yaratildi. Jami: {order.total_price} so'm. To'lov usuli: {payment_method}"
                )

                # Save to user's history (can be generic history or specific order history)
                try:
                    from pharmacy.models.misc import UserHistory

                    UserHistory.objects.create(
                        user=user,
                        action="ORDER_CREATED",
                        description=history_description,
                        metadata={
                            "order_id": order.id,
                            "total_price": str(order.total_price),
                            "items": len(cart_items),
                        },
                    )
                except:
                    pass

                # AuditLog - faqat admin uchun (role='admin', is_superuser=True, is_staff=True)
                if user.role == "admin" and user.is_superuser and user.is_staff:
                    AuditLog.objects.create(
                        user=user,
                        action="CHECKOUT_ORDER",
                        description=f"Buyurtma #{order.id} muvaffaqiyatli rasmiylashtirildi (Jami: {order.total_price} so'm). To'lov: {payment_method}",
                        target_type="order",
                        target_id=order.id,
                        meta={
                            "order_id": order.id,
                            "total_price": str(order.total_price),
                            "items_count": len(cart_items),
                            "payment_method": payment_method,
                        },
                    )

            transaction.on_commit(log_checkout)

        return Response(
            {
                "success": True,
                "status": "success",
                "message": "Buyurtmangiz muvaffaqiyatli qabul qilindi!",
                "order_id": order.id,
                "total_price": float(order.total_price),
            },
            status=status.HTTP_201_CREATED,
        )
