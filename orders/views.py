from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from pharmacy.models.medicine import Medicine

from .models import Cart, CartItem, Order, OrderItem
from .serializers import (
    CartItemSerializer,
    CartSummarySerializer,
    OrderDetailSerializer,
    OrderItemSerializer,
    OrderListSerializer,
)


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSummarySerializer(cart)
        return Response(serializer.data)

    def create(self, request):
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity", 1)

        try:
            product = Medicine.objects.get(id=product_id)
        except Medicine.DoesNotExist:
            return Response(
                {"error": "Mahsulot topilmadi."}, status=status.HTTP_400_BAD_REQUEST
            )

        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        cart_item.quantity = int(quantity)
        cart_item.save()

        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="add-item")
    def add_item(self, request):
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity", 1)

        try:
            product = Medicine.objects.get(id=product_id)
        except Medicine.DoesNotExist:
            return Response(
                {"error": "Mahsulot topilmadi."}, status=status.HTTP_400_BAD_REQUEST
            )

        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        cart_item.quantity = cart_item.quantity + int(quantity)
        cart_item.save()

        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="remove-item")
    def remove_item(self, request):
        product_id = request.data.get("product_id")

        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, cart=cart, product__id=product_id)
        cart_item.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="update-item")
    def update_item(self, request):
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity")

        if quantity is None:
            return Response(
                {"error": "Quantity is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, cart=cart, product__id=product_id)

        if int(quantity) <= 0:
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        cart_item.quantity = int(quantity)
        cart_item.save()

        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data)

    @action(detail=False, methods=["delete"], url_path="clear")
    def clear_cart(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderViewSet(viewsets.ModelViewSet):
    """
    Customer-facing Order endpoints.
    List uses OrderListSerializer, retrieve uses OrderDetailSerializer.
    """

    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # drf_yasg workaround for AnonymousUser
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()

        # Check if the user is authenticated
        if self.request.user.is_authenticated:
            return self.queryset.filter(customer=self.request.user)
        return (
            self.queryset.none()
        )  # Return an empty queryset for unauthenticated users

    def get_serializer_class(self):
        if self.action in ["retrieve"]:
            return OrderDetailSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk, customer=request.user)
        if order.status in ["Pending", "Processing"]:
            order.status = "Canceled"
            order.save()
            return Response({"status": "order canceled"})
        return Response(
            {"error": "Order cannot be canceled at this stage."},
            status=status.HTTP_400_BAD_REQUEST,
        )
