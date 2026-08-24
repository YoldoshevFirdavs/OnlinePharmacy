from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from users.models import CustomUser


class DailyOrdersStatsAPIView(APIView):
    """
    Oxirgi N kunlik kunlik buyurtmalar va daromad agregatsiyasi.
    GET /dashboard/api/stats/orders/?range=7
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            days_range = int(request.query_params.get("range", 7))
        except (ValueError, TypeError):
            days_range = 7

        # 1 dan 90 kungacha cheklash
        days_range = max(1, min(90, days_range))
        cache_key = f"stats:orders:daily:{days_range}"

        # 1) Redis Cache dan tekshirish
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data, status=status.HTTP_200_OK)
        except Exception:
            cached_data = None

        now = timezone.now()
        start_date = (now - timedelta(days=days_range - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

        # 2) DB dan kunlik agregatsiya olish
        qs = (
            Order.objects.filter(created_at__gte=start_date)
            .annotate(order_date=TruncDate("created_at"))
            .values("order_date")
            .annotate(order_count=Count("id"), revenue=Sum("total_price"))
            .order_by("order_date")
        )

        db_results = {
            item["order_date"].strftime("%Y-%m-%d"): {
                "count": item["order_count"],
                "revenue": float(item["revenue"] or 0.0),
            }
            for item in qs
            if item["order_date"]
        }

        # 3) Barcha kunlar uchun bo'sh kunlarni 0 qilib to'ldirish
        labels = []
        counts_data = []
        revenue_data = []
        count_total = 0
        revenue_total = 0.0

        for i in range(days_range):
            current_day = start_date + timedelta(days=i)
            day_str = current_day.strftime("%Y-%m-%d")
            day_label = current_day.strftime("%d-%b")  # Masalan: 16-Aug

            day_data = db_results.get(day_str, {"count": 0, "revenue": 0.0})
            labels.append(day_label)
            counts_data.append(day_data["count"])
            revenue_data.append(day_data["revenue"])
            count_total += day_data["count"]
            revenue_total += day_data["revenue"]

        payload = {
            "range_days": days_range,
            "labels": labels,
            "data": counts_data,
            "revenue_data": revenue_data,
            "count_total": count_total,
            "revenue_total": round(revenue_total, 2),
            "has_data": count_total > 0,
        }

        # 4) Redis keshga 50 soniya saqlash
        try:
            cache.set(cache_key, payload, timeout=50)
        except Exception:
            pass

        return Response(payload, status=status.HTTP_200_OK)


class SummaryStatsAPIView(APIView):
    """
    Umumiy va bugungi KPI statistikasi:
    GET /dashboard/api/stats/summary/
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        cache_key = "stats:summary:kpi"

        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data, status=status.HTTP_200_OK)
        except Exception:
            cached_data = None

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Bugungi buyurtmalar va daromad
        today_orders_qs = Order.objects.filter(created_at__gte=today_start)
        orders_today = today_orders_qs.count()
        revenue_today = float(today_orders_qs.aggregate(total=Sum("total_price"))["total"] or 0.0)

        # Jami faol foydalanuvchilar
        active_users = CustomUser.objects.filter(is_active=True).count()

        # Jami buyurtmalar
        orders_total = Order.objects.count()

        payload = {
            "orders_today": orders_today,
            "revenue_today": round(revenue_today, 2),
            "active_users": active_users,
            "orders_total": orders_total,
            "updated_at": now.strftime("%H:%M:%S"),
        }

        try:
            cache.set(cache_key, payload, timeout=50)
        except Exception:
            pass

        return Response(payload, status=status.HTTP_200_OK)
