from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from pharmacy.models import Category, Medicine
from users.models import CustomUser, Deliverer

from .permissions import IsDashboardAdmin, IsDashboardDeliverer
from .serializers import (
    DashboardCategorySerializer,
    DashboardOrderSerializer,
    DashboardProductSerializer,
    DashboardUserSerializer,
    DelivererSerializer,
    DelivererUpdateSerializer,
)

VALID_ORDER_STATUSES = {choice[0] for choice in Order.STATUS_CHOICES}
STATUS_ALIASES = {"Cancelled": "Canceled"}


class DashboardAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsDashboardAdmin]


class DelivererAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsDashboardDeliverer]


class SessionCheckView(DashboardAPIView):
    def get(self, request):
        return Response({"authenticated": True, "user_id": request.user.pk})


class SalesStatsView(DashboardAPIView):
    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError):
            days = 30
        days = max(1, min(days, 365))

        since = timezone.now() - timedelta(days=days)
        rows = (
            Order.objects.filter(created_at__gte=since, status="Delivered")
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("total_price"))
            .order_by("day")
        )

        labels = []
        values = []
        for row in rows:
            day = row["day"]
            labels.append(day.strftime("%d.%m") if day else "")
            values.append(float(row["total"] or 0))

        return Response({"labels": labels, "values": values, "data": values})


class CategoryListView(DashboardAPIView):
    def get(self, request):
        categories = Category.objects.annotate(
            product_count=Count("medicines")
        ).order_by("name")
        serializer = DashboardCategorySerializer(
            categories, many=True, context={"request": request}
        )
        return Response(serializer.data)


class ProductListView(DashboardAPIView):
    def get(self, request):
        products = Medicine.objects.select_related("category").order_by("-id")
        serializer = DashboardProductSerializer(
            products, many=True, context={"request": request}
        )
        return Response(serializer.data)


class OrderListView(DashboardAPIView):
    def get(self, request):
        orders = (
            Order.objects.select_related("customer", "driver")
            .prefetch_related("order_items")
            .order_by("-created_at")
        )
        serializer = DashboardOrderSerializer(
            orders, many=True, context={"request": request}
        )
        return Response(serializer.data)


class RecentOrderListView(DashboardAPIView):
    def get(self, request):
        orders = (
            Order.objects.select_related("customer", "driver")
            .prefetch_related("order_items")
            .order_by("-created_at")[:10]
        )
        serializer = DashboardOrderSerializer(
            orders, many=True, context={"request": request}
        )
        return Response(serializer.data)


class OrderStatusUpdateView(DashboardAPIView):
    def patch(self, request, pk):
        order = Order.objects.filter(pk=pk).first()
        if not order:
            return Response({"detail": "Buyurtma topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        if not new_status:
            return Response({"detail": "Status talab qilinadi."}, status=status.HTTP_400_BAD_REQUEST)

        new_status = STATUS_ALIASES.get(new_status, new_status)
        if new_status not in VALID_ORDER_STATUSES:
            return Response({"detail": "Noto'g'ri status."}, status=status.HTTP_400_BAD_REQUEST)

        order.status = new_status
        if new_status == "Delivered" and not order.delivered_at:
            order.delivered_at = timezone.now()
        order.save(update_fields=["status", "delivered_at"])

        serializer = DashboardOrderSerializer(order, context={"request": request})
        return Response(serializer.data)


class UserListView(DashboardAPIView):
    def get(self, request):
        users = CustomUser.objects.all().order_by("id")
        serializer = DashboardUserSerializer(
            users, many=True, context={"request": request}
        )
        return Response(serializer.data)


class SettingsView(DashboardAPIView):
    def post(self, request):
        return Response({"saved": True, "theme": request.data.get("theme"), "accent": request.data.get("accent")})


class CalendarEventsView(DashboardAPIView):
    def get(self, request):
        orders = Order.objects.order_by("-created_at")[:50]
        events = []
        for order in orders:
            title = f"Buyurtma #{order.id}"
            events.append(
                {
                    "title": title,
                    "start": order.created_at.isoformat(),
                    "url": f"/dashboard/orders/",
                }
            )
        return Response(events)


class DelivererProfileView(DelivererAPIView):
    """
    Get or update deliverer profile data.
    Endpoint: /api/v1/dashboard/me/
    """
    def get(self, request):
        """Get deliverer profile data"""
        try:
            deliverer = Deliverer.objects.get(user=request.user)
            serializer = DelivererSerializer(deliverer)
            return Response(serializer.data)
        except Deliverer.DoesNotExist:
            # Return user data only if no deliverer profile
            return Response({
                "user": {
                    "id": request.user.id,
                    "full_name": request.user.full_name,
                    "email": request.user.email,
                    "phone_number": request.user.phone_number,
                },
                "notify_order": False,
                "notify_status": False,
                "notify_push": False,
            })

    def put(self, request):
        """Update deliverer profile data"""
        try:
            deliverer = Deliverer.objects.get(user=request.user)
        except Deliverer.DoesNotExist:
            return Response(
                {"detail": "Yetkazib beruvchi profili topilmadi."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DelivererUpdateSerializer(
            deliverer, data=request.data, partial=True
        )
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data)
            except Exception as e:
                logger.error(f"Error updating deliverer profile: {str(e)}")
                return Response(
                    {"detail": "Profilni yangilashda xatolik yuz berdi."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Re-import logger at the end since it's used by DelivererProfileView
import logging
logger = logging.getLogger(__name__)
