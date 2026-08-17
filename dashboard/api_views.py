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
from users.serializers import DeliveryDriverSerializer, UserBanSerializer, BanUserSerializer, UnbanUserSerializer

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
            Order.objects.select_related("user")
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
            Order.objects.select_related("user")
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
            return Response(
                {"detail": "Buyurtma topilmadi."}, status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get("status")
        if not new_status:
            return Response(
                {"detail": "Status talab qilinadi."}, status=status.HTTP_400_BAD_REQUEST
            )

        new_status = STATUS_ALIASES.get(new_status, new_status)
        if new_status not in VALID_ORDER_STATUSES:
            return Response(
                {"detail": "Noto'g'ri status."}, status=status.HTTP_400_BAD_REQUEST
            )

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
        total_categories = Category.objects.count()
        total_medicines = Medicine.objects.count()
        total_customers = CustomUser.objects.filter(
            is_staff=False, seller__isnull=True
        ).count()
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status="Pending").count()
        delivered_orders = Order.objects.filter(status="Delivered").count()
        total_users = CustomUser.objects.count()
        total_drivers = DeliveryDriver.objects.count()
        out_of_stock = Medicine.objects.filter(stock=0).count()
        total_staff = CustomUser.objects.filter(is_staff=True).count()

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
        serializer = DeliveryDriverSerializer(
            drivers, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = DeliveryDriverSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        driver = get_object_or_404(DeliveryDriver, pk=pk)
        serializer = DeliveryDriverSerializer(
            driver, data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        driver = get_object_or_404(DeliveryDriver, pk=pk)
        serializer = DeliveryDriverSerializer(
            driver, data=request.data, partial=True, context={"request": request}
        )
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

from users.serializers import UserBanSerializer, BanUserSerializer, UnbanUserSerializer


class BannedUsersListView(APIView):
    """Bannalangan foydalanuvchilar ro'yxati."""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Vaqtli va permanent banlar jadvalini olish."""
        from django.utils import timezone
        
        # Hozirda bannalangan foydalanuvchilar
        banned_users = CustomUser.objects.filter(
            banned_for__isnull=False
        ).select_related('banned_by').order_by('-ban_until', '-date_joined')
        
        serializer = UserBanSerializer(banned_users, many=True)
        
        return Response({
            'count': banned_users.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class BanUserView(APIView):
    """Foydalanuvchini ban qilish."""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """Ban berish."""
        serializer = BanUserSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'success': True,
                'message': f'{user.full_name or user.email} bannalandi.',
                'user': UserBanSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UnbanUserView(APIView):
    """Ban olib tashlash."""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """Ban olib tashlash."""
        serializer = UnbanUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'success': True,
                'message': f'{user.full_name or user.email} unbanned qilindi.',
                'user': UserBanSerializer(user).data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserBanDetailView(APIView):
    """Alohida foydalanuvchining ban status-ini olish."""
    permission_classes = [IsAdminUser]
    
    def get(self, request, user_id):
        """Foydalanuvchining ban ma'lumotlari."""
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'Foydalanuvchi topilmadi.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UserBanSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
