from django.http import Http404
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Order, OrderItem, Cart, CartItem, OrderDelivery
from .serializers import (
    OrderItemSerializer,
    CartSummarySerializer,
    CartItemSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
    OrderDeliverySerializer,
    DriverOrderSerializer,
)
from users.permissions import IsDriver
from pharmacy.models.medicine import Medicine


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


class DriverOrdersListView(generics.ListAPIView):
    """
    Lists orders assigned to the authenticated delivery driver.
    """

    queryset = Order.objects.all()
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated, IsDriver]

    def get_queryset(self):
        # drf_yasg workaround for AnonymousUser
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()

        if not self.request.user.is_authenticated:
            return Order.objects.none()
        driver_profile = getattr(
            self.request.user, "deliverer_profile", None
        )  # Changed to deliverer_profile
        if driver_profile is None:
            return Order.objects.none()
        return (
            self.queryset.filter(driver=driver_profile)
            .exclude(status__in=["Delivered", "Canceled", "Returned"])
            .order_by("-created_at")
        )


class DriverOrderDetailView(generics.RetrieveAPIView):
    """
    Retrieves details of a specific order assigned to the authenticated delivery driver.
    """

    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated, IsDriver]
    lookup_field = "pk"

    def get_queryset(self):
        # drf_yasg workaround for AnonymousUser
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()

        if not self.request.user.is_authenticated:
            return Order.objects.none()
        driver_profile = getattr(
            self.request.user, "deliverer_profile", None
        )  # Changed to deliverer_profile
        if driver_profile is None:
            return Order.objects.none()
        return self.queryset.filter(driver=driver_profile)


class DriverOrderAcceptView(APIView):
    """
    Allows the authenticated delivery driver to accept an assigned order.
    """

    permission_classes = [IsAuthenticated, IsDriver]

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        order = get_object_or_404(
            Order, pk=pk, driver=getattr(request.user, "deliverer_profile", None)
        )  # Changed to deliverer_profile

        if order.status == "Assigned":
            order.status = "Accepted"
            order.accepted_at = timezone.now()
            order.save()
            return Response(
                {"detail": f"Order {pk} accepted."}, status=status.HTTP_200_OK
            )
        return Response(
            {"detail": "Order cannot be accepted at this stage."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class DriverOrderStatusUpdateView(APIView):
    """
    Allows the authenticated delivery driver to update the status of an order.
    Payload: {status: "Picked Up" | "On The Way" | "Delivered"}
    """

    permission_classes = [IsAuthenticated, IsDriver]

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        status_update = request.data.get("status")
        allowed = ["Picked Up", "Delivered", "On The Way", "Arrived"]
        if status_update not in allowed:
            return Response(
                {"detail": f"Invalid status. Must be one of {allowed}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = get_object_or_404(
            Order, pk=pk, driver=getattr(request.user, "deliverer_profile", None)
        )  # Changed to deliverer_profile

        if status_update == "Picked Up" and order.status in ["Accepted", "Assigned"]:
            order.status = "Picked Up"
            order.picked_up_at = timezone.now()
            order.save()
            return Response(
                {"detail": f"Order {pk} status updated to Picked Up."},
                status=status.HTTP_200_OK,
            )

        if status_update == "On The Way" and order.status == "Picked Up":
            order.status = "On The Way"
            order.on_the_way_at = timezone.now()
            order.save()
            return Response(
                {"detail": f"Order {pk} status updated to On The Way."},
                status=status.HTTP_200_OK,
            )

        if status_update == "Arrived" and order.status in ["On The Way"]:
            order.status = "Arrived"
            order.save()
            return Response(
                {"detail": f"Order {pk} status updated to Arrived."},
                status=status.HTTP_200_OK,
            )

        if status_update == "Delivered" and order.status in [
            "On The Way",
            "Arrived",
            "Picked Up",
        ]:
            order.status = "Delivered"
            order.delivered_at = timezone.now()
            order.save()
            return Response(
                {"detail": f"Order {pk} status updated to Delivered."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "detail": f"Order cannot be updated to {status_update} at its current stage ({order.status})."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class DriverOrderArrivalView(APIView):
    """
    Records arrival time and wait seconds for an order.
    Payload: {wait_seconds: int}
    """

    permission_classes = [IsAuthenticated, IsDriver]

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        wait_seconds = request.data.get("wait_seconds")
        try:
            wait_seconds = int(wait_seconds)
        except (TypeError, ValueError):
            return Response(
                {"detail": "wait_seconds must be a non-negative integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if wait_seconds < 0:
            return Response(
                {"detail": "wait_seconds must be a non-negative integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = get_object_or_404(
            Order, pk=pk, driver=getattr(request.user, "deliverer_profile", None)
        )  # Changed to deliverer_profile
        order_delivery, created = OrderDelivery.objects.get_or_create(order=order)

        if order.status in ["On The Way"]:
            order.status = "Arrived"
            order_delivery.arrived_at = timezone.now()
            order_delivery.wait_seconds = wait_seconds
            order.save()
            order_delivery.save()
            return Response(
                {"detail": f"Order {pk} arrival time and wait seconds recorded."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "Order cannot be marked as arrived at this stage."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class DriverOrderViewSet(viewsets.ViewSet):
    """
    Consolidated ViewSet for driver workflows.
    - list: GET /driver-orders/         -> list assigned orders (OrderListSerializer)
    - retrieve: GET /driver-orders/{pk}/ -> detailed order (DriverOrderSerializer)
    - accept: POST /driver-orders/{pk}/accept/
    - status: POST /driver-orders/{pk}/status/  {status: "..."}
    - arrival: POST /driver-orders/{pk}/arrival/ {wait_seconds: int}
    """

    permission_classes = [IsAuthenticated, IsDriver]

    def list(self, request):
        # drf_yasg workaround for AnonymousUser
        if getattr(self, "swagger_fake_view", False):
            return Response([], status=status.HTTP_200_OK)

        if not request.user.is_authenticated:
            return Response([], status=status.HTTP_200_OK)
        driver_profile = getattr(
            request.user, "deliverer_profile", None
        )  # Changed to deliverer_profile
        if driver_profile is None:
            return Response([], status=status.HTTP_200_OK)
        qs = (
            Order.objects.filter(driver=driver_profile)
            .exclude(status__in=["Delivered", "Canceled", "Returned"])
            .order_by("-created_at")
        )
        serializer = OrderListSerializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        # drf_yasg workaround for AnonymousUser
        if getattr(self, "swagger_fake_view", False):
            raise Http404("Swagger fake view")

        if not request.user.is_authenticated:
            raise Http404("Authentication credentials were not provided.")
        driver_profile = getattr(
            request.user, "deliverer_profile", None
        )  # Changed to deliverer_profile
        order = get_object_or_404(Order, pk=pk, driver=driver_profile)
        serializer = DriverOrderSerializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        driver_profile = getattr(
            request.user, "deliverer_profile", None
        )  # Changed to deliverer_profile
        order = get_object_or_404(Order, pk=pk, driver=driver_profile)
        if order.status == "Assigned":
            order.status = "Accepted"
            order.accepted_at = timezone.now()
            order.save()
            return Response(
                {"detail": f"Order {pk} accepted."}, status=status.HTTP_200_OK
            )
        return Response(
            {"detail": "Order cannot be accepted at this stage."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"], url_path="status")
    def status(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        driver_profile = getattr(
            request.user, "deliverer_profile", None
        )  # Changed to deliverer_profile
        order = get_object_or_404(Order, pk=pk, driver=driver_profile)
        status_update = request.data.get("status")
        allowed = ["Picked Up", "On The Way", "Arrived", "Delivered"]
        if status_update not in allowed:
            return Response(
                {"detail": f"Invalid status. Must be one of {allowed}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if status_update == "Picked Up" and order.status in ["Accepted", "Assigned"]:
            order.status = "Picked Up"
            order.picked_up_at = timezone.now()
            order.save()
            return Response(
                {"detail": f"Order {pk} status updated to Picked Up."},
                status=status.HTTP_200_OK,
            )

        if status_update == "On The Way" and order.status == "Picked Up":
            order.status = "On The Way"
            order.on_the_way_at = timezone.now()
            order.save()
            return Response(
                {"detail": f"Order {pk} status updated to On The Way."},
                status=status.HTTP_200_OK,
            )

        if status_update == "Arrived" and order.status in ["On The Way"]:
            order.status = "Arrived"
            order.save()
            return Response(
                {"detail": f"Order {pk} status updated to Arrived."},
                status=status.HTTP_200_OK,
            )

        if status_update == "Delivered" and order.status in [
            "On The Way",
            "Arrived",
            "Picked Up",
        ]:
            order.status = "Delivered"
            order.delivered_at = timezone.now()
            order.save()
            return Response(
                {"detail": f"Order {pk} status updated to Delivered."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "detail": f"Order cannot be updated to {status_update} at its current stage ({order.status})."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"], url_path="arrival")
    def arrival(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        driver_profile = getattr(
            request.user, "deliverer_profile", None
        )  # Changed to deliverer_profile
        order = get_object_or_404(Order, pk=pk, driver=driver_profile)
        wait_seconds = request.data.get("wait_seconds", 0)
        try:
            wait_seconds = int(wait_seconds)
        except (TypeError, ValueError):
            return Response(
                {"detail": "wait_seconds must be a non-negative integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if wait_seconds < 0:
            return Response(
                {"detail": "wait_seconds must be a non-negative integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_delivery, created = OrderDelivery.objects.get_or_create(order=order)
        if order.status in ["On The Way"]:
            order.status = "Arrived"
            order_delivery.arrived_at = timezone.now()
            order_delivery.wait_seconds = wait_seconds
            order.save()
            order_delivery.save()
            return Response(
                {"detail": f"Order {pk} arrival time and wait seconds recorded."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "Order cannot be marked as arrived at this stage."},
            status=status.HTTP_400_BAD_REQUEST,
        )


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import OrderDelivery


class OrderAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            od = OrderDelivery.objects.get(pk=pk, driver__user=request.user)
            od.accepted_at = timezone.now()
            od.save()
            return Response({"detail": "accepted"})
        except OrderDelivery.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)


class OrderStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        status_val = request.data.get("status")
        return Response({"detail": "status updated"})
