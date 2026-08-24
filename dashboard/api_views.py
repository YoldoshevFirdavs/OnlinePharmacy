from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from pharmacy.models import Category, Medicine
from users.models import CustomUser, DeliveryDriver
from users.serializers import BanUserSerializer, DeliveryDriverSerializer, UnbanUserSerializer, UserBanSerializer

from .permissions import IsDashboardAdmin
from .serializers import (
    DashboardCategorySerializer,
    DashboardOrderSerializer,
    DashboardProductSerializer,
    DashboardUserSerializer,
)

VALID_ORDER_STATUSES = {choice[0] for choice in Order.STATUS_CHOICES}
STATUS_ALIASES = {"Cancelled": "Canceled"}


class DashboardAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsDashboardAdmin]


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
        categories = Category.objects.annotate(product_count=Count("medicines")).order_by("name")
        serializer = DashboardCategorySerializer(categories, many=True, context={"request": request})
        return Response(serializer.data)


class ProductListView(DashboardAPIView):
    def get(self, request):
        products = Medicine.objects.select_related("category").order_by("-id")
        serializer = DashboardProductSerializer(products, many=True, context={"request": request})
        return Response(serializer.data)


class OrderListView(DashboardAPIView):
    def get(self, request):
        orders = Order.objects.select_related("user").prefetch_related("order_items").order_by("-created_at")
        serializer = DashboardOrderSerializer(orders, many=True, context={"request": request})
        return Response(serializer.data)


class RecentOrderListView(DashboardAPIView):
    def get(self, request):
        orders = Order.objects.select_related("user").prefetch_related("order_items").order_by("-created_at")[:10]
        serializer = DashboardOrderSerializer(orders, many=True, context={"request": request})
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
        serializer = DashboardUserSerializer(users, many=True, context={"request": request})
        return Response(serializer.data)


class SettingsView(DashboardAPIView):
    def post(self, request):
        return Response(
            {
                "saved": True,
                "theme": request.data.get("theme"),
                "accent": request.data.get("accent"),
            }
        )


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


class DeliveryDriverViewSet(DashboardAPIView):
    def get(self, request, pk=None):
        if pk:
            driver = get_object_or_404(DeliveryDriver, pk=pk)
            serializer = DeliveryDriverSerializer(driver)
            return Response(serializer.data)
        drivers = DeliveryDriver.objects.all()
        serializer = DeliveryDriverSerializer(drivers, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DeliveryDriverSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        driver = get_object_or_404(DeliveryDriver, pk=pk)
        serializer = DeliveryDriverSerializer(driver, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        driver = get_object_or_404(DeliveryDriver, pk=pk)
        serializer = DeliveryDriverSerializer(driver, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        driver = get_object_or_404(DeliveryDriver, pk=pk)
        driver.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardStatsApiView(DashboardAPIView):
    def get(self, request):
        now = timezone.now()
        total_categories = Category.objects.count()
        total_medicines = Medicine.objects.count()
        total_customers = CustomUser.objects.filter(is_staff=False, role="user").count()
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status="Pending").count()
        delivered_orders = Order.objects.filter(status="Delivered").count()
        total_users = CustomUser.objects.count()
        total_drivers = DeliveryDriver.objects.count()
        out_of_stock = Medicine.objects.filter(stock=0).count()
        total_staff = CustomUser.objects.filter(is_staff=True).count()

        # Real dynamic category revenue
        category_qs = (
            Category.objects.annotate(total_rev=Sum("medicines__orderitem__price_at_order"))
            .filter(total_rev__gt=0)
            .order_by("-total_rev")[:5]
        )
        cat_labels = [c.name for c in category_qs]
        cat_values = [float(c.total_rev or 0) for c in category_qs]
        if not cat_labels:
            # Fallback to category products count if no orders yet
            cat_list = Category.objects.annotate(p_count=Count("medicines")).order_by("-p_count")[:4]
            cat_labels = [c.name for c in cat_list]
            cat_values = [c.p_count for c in cat_list]

        # Real last 14 days orders
        since_14_days = now - timedelta(days=13)
        orders_14_qs = (
            Order.objects.filter(created_at__gte=since_14_days)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(cnt=Count("id"))
            .order_by("day")
        )
        dict_14 = {r["day"].strftime("%d-%b") if r["day"] else "": r["cnt"] for r in orders_14_qs}
        labels_14 = []
        values_14 = []
        for i in range(14):
            d = since_14_days + timedelta(days=i)
            l = d.strftime("%d-%b")
            labels_14.append(l)
            values_14.append(dict_14.get(l, 0))

        # Real top sold medicines & Product Revenue
        from orders.models import OrderItem

        top_items_qs = (
            OrderItem.objects.filter(product__isnull=False)
            .values("product__id", "product__name")
            .annotate(total_sold=Sum("quantity"), total_revenue=Sum("price_at_order"))
            .order_by("-total_sold")[:10]
        )

        top_products = []
        prod_revenue_labels = []
        prod_revenue_values = []

        if top_items_qs.exists():
            for idx, item in enumerate(top_items_qs):
                p_name = item["product__name"] or f"Dori #{item['product__id']}"
                top_products.append({"rank": idx + 1, "name": p_name, "sold": item["total_sold"] or 0})
                if idx < 5:
                    prod_revenue_labels.append(p_name)
                    prod_revenue_values.append(float(item["total_revenue"] or 0.0))
        else:
            # Fallback to existing top medicines by stock/orders if OrderItems were directly created
            meds = Medicine.objects.all().order_by("-id")[:5]
            for idx, m in enumerate(meds):
                top_products.append({"rank": idx + 1, "name": m.name, "sold": int(m.stock or 0)})
                prod_revenue_labels.append(m.name)
                prod_revenue_values.append(float(m.price or 0.0))

        data = {
            "total_categories": total_categories,
            "total_medicines": total_medicines,
            "total_customers": total_customers,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "delivered_orders": delivered_orders,
            "total_users": total_users,
            "total_drivers": total_drivers,
            "out_of_stock": out_of_stock,
            "total_staff": total_staff,
            "updated_at": now.strftime("%H:%M:%S"),
            "category_revenue": {"labels": cat_labels or ["Kategoriya yo'q"], "values": cat_values or [0]},
            "product_revenue": {"labels": prod_revenue_labels, "values": prod_revenue_values},
            "last_14_days": {"labels": labels_14, "values": values_14},
            "top_products": top_products,
        }
        return Response(data)


class DriverApiView(DashboardAPIView):
    """
    Admin dashboard uchun driverlarni boshqarish API.
    Full CRUD: list, create, retrieve, update, delete.
    """

    def get(self, request, pk=None):
        if pk:
            driver = get_object_or_404(DeliveryDriver, pk=pk)
            serializer = DeliveryDriverSerializer(driver, context={"request": request})
            return Response(serializer.data)
        drivers = DeliveryDriver.objects.all().order_by("id")
        serializer = DeliveryDriverSerializer(drivers, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        serializer = DeliveryDriverSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        driver = get_object_or_404(DeliveryDriver, pk=pk)
        serializer = DeliveryDriverSerializer(driver, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        driver = get_object_or_404(DeliveryDriver, pk=pk)
        serializer = DeliveryDriverSerializer(driver, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        driver = get_object_or_404(DeliveryDriver, pk=pk)
        driver.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================
# BAN MANAGEMENT ENDPOINTS
# ============================================

from users.serializers import BanUserSerializer, UnbanUserSerializer, UserBanSerializer


class BannedUsersListView(APIView):
    """Bannalangan foydalanuvchilar ro'yxati."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Vaqtli va permanent banlar jadvalini olish."""

        # Hozirda bannalangan foydalanuvchilar
        banned_users = (
            CustomUser.objects.filter(banned_for__isnull=False)
            .select_related("banned_by")
            .order_by("-ban_until", "-date_joined")
        )

        serializer = UserBanSerializer(banned_users, many=True)

        return Response({"count": banned_users.count(), "results": serializer.data}, status=status.HTTP_200_OK)


class BanUserView(APIView):
    """Foydalanuvchini ban qilish."""

    permission_classes = [IsAdminUser]

    def post(self, request):
        """Ban berish."""
        serializer = BanUserSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "success": True,
                    "message": f"{user.full_name or user.email} bannalandi.",
                    "user": UserBanSerializer(user).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UnbanUserView(APIView):
    """Ban olib tashlash."""

    permission_classes = [IsAdminUser]

    def post(self, request):
        """Ban olib tashlash."""
        serializer = UnbanUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "success": True,
                    "message": f"{user.full_name or user.email} unbanned qilindi.",
                    "user": UserBanSerializer(user).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserBanDetailView(APIView):
    """Alohida foydalanuvchining ban status-ini olish."""

    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        """Foydalanuvchining ban ma'lumotlari."""
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "Foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserBanSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Fingerprint Ban Management Views
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated


def get_client_ip(request):
    """Get client IP from request"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


class UnbanFingerprintView(DashboardAPIView):
    """Unban a fingerprint (admin only)"""

    permission_classes = [IsAdminUser]

    def post(self, request):
        fingerprint = request.data.get("fingerprint")
        if not fingerprint:
            return Response(
                {"ok": False, "error": "fingerprint is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from users.services import BanService

        BanService.unban_by_fp(fingerprint)
        return Response({"ok": True, "message": "Fingerprint unbanned"}, status=status.HTTP_200_OK)


class ClearIPBlockView(DashboardAPIView):
    """Clear IP block (admin only)"""

    permission_classes = [IsAdminUser]

    def post(self, request):
        client_ip = get_client_ip(request)
        cache_key = f"ip_block:{client_ip}"
        cache.delete(cache_key)

        return Response({"ok": True, "message": "IP block cleared"}, status=status.HTTP_200_OK)


class FingerprintBanStatusView(APIView):
    """Check fingerprint ban status"""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        fingerprint = request.COOKIES.get("device_fp")
        if not fingerprint:
            return Response(
                {"ok": False, "banned": False},
                status=status.HTTP_200_OK,
            )

        from users.services import BanService

        is_banned = BanService.is_fp_banned(fingerprint)
        ban_info = BanService.get_fp_ban_info(fingerprint) if is_banned else None

        return Response(
            {
                "ok": True,
                "banned": is_banned,
                "ban_info": ban_info,
            },
            status=status.HTTP_200_OK,
        )
