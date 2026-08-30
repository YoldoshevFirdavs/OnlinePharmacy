"""
Admin Dashboard API endpoints for AJAX charts and analytics
- Analytics data for charts (1min auto-refresh)
- User history and order details
"""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from pharmacy.models import Medicine
from pharmacy.models.history import CustomerUserHistory
from users.models import CustomUser


class AdminAnalyticsAPIView(APIView):
    """
    Analytics dashboard data (AJAX, 1min refresh)
    Returns metrics for charts: orders, revenue, products, comments
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        """Return analytics data for dashboard"""
        try:
            # Time ranges
            now = timezone.now()
            last_7_days = now - timedelta(days=7)
            last_30_days = now - timedelta(days=30)
            last_year = now - timedelta(days=365)

            # Orders metrics
            total_orders = Order.objects.count()
            orders_7d = Order.objects.filter(created_at__gte=last_7_days).count()
            orders_30d = Order.objects.filter(created_at__gte=last_30_days).count()

            pending_orders = Order.objects.filter(status="Pending").count()
            delivered_orders = Order.objects.filter(status="Delivered").count()

            # Revenue metrics
            total_revenue = Order.objects.aggregate(Sum("total_price"))["total_price__sum"] or 0
            revenue_7d = (
                Order.objects.filter(created_at__gte=last_7_days).aggregate(Sum("total_price"))["total_price__sum"] or 0
            )
            revenue_30d = (
                Order.objects.filter(created_at__gte=last_30_days).aggregate(Sum("total_price"))["total_price__sum"]
                or 0
            )

            # Products metrics
            total_products = Medicine.objects.count()
            out_of_stock = Medicine.objects.filter(stock=0).count()
            low_stock = Medicine.objects.filter(stock__gt=0, stock__lte=10).count()

            # Users metrics
            total_users = CustomUser.objects.count()
            customers = CustomUser.objects.filter(seller__isnull=True, is_staff=False).count()
            sellers = CustomUser.objects.filter(seller__isnull=False).count()

            # Comments metrics
            from pharmacy.models.comments import ProductComment

            total_comments = ProductComment.objects.count()
            approved_comments = ProductComment.objects.filter(is_approved=True).count()
            unapproved_comments = ProductComment.objects.filter(is_approved=False).count()

            # Orders by status (pie chart)
            order_status_dist = Order.objects.values("status").annotate(count=Count("id"))

            # Daily orders (last 30 days for line chart)
            daily_orders = []
            for i in range(30):
                day = now - timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                count = Order.objects.filter(created_at__gte=day_start, created_at__lt=day_end).count()
                daily_orders.append({"date": day.strftime("%Y-%m-%d"), "orders": count})

            # Daily revenue (last 30 days)
            daily_revenue = []
            for i in range(30):
                day = now - timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                revenue = (
                    Order.objects.filter(created_at__gte=day_start, created_at__lt=day_end).aggregate(
                        Sum("total_price")
                    )["total_price__sum"]
                    or 0
                )
                daily_revenue.append({"date": day.strftime("%Y-%m-%d"), "revenue": float(revenue)})

            # Payment method distribution (for charts)
            payment_method_qs = (
                Order.objects.values("payment_method")
                .annotate(count=Count("id"), total=Sum("total_price"))
                .order_by("-count")
            )

            # Map payment methods to readable labels
            payment_method_labels = {
                "cash": "Naqd pul",
                "card": "Karta",
                "payme": "Payme",
                "click": "Click",
                "": "Noma'lum",
            }

            payment_method_dist = []
            for item in payment_method_qs:
                method = item.get("payment_method") or ""
                label = payment_method_labels.get(method.lower(), method or "Noma'lum")
                payment_method_dist.append(
                    {"payment_method": label, "count": item["count"] or 0, "total": float(item["total"] or 0)}
                )

            # Category-based revenue (for charts)
            category_revenue = (
                Medicine.objects.select_related("category")
                .values("category__name")
                .annotate(total_sold=Sum("orderitem__quantity"), total_revenue=Sum("orderitem__price_at_order"))
                .filter(orderitem__isnull=False)
                .order_by("-total_revenue")[:10]
            )

            return Response(
                {
                    "status": "success",
                    "data": {
                        "orders": {
                            "total": total_orders,
                            "last_7_days": orders_7d,
                            "last_30_days": orders_30d,
                            "pending": pending_orders,
                            "delivered": delivered_orders,
                        },
                        "revenue": {
                            "total": float(total_revenue),
                            "last_7_days": float(revenue_7d),
                            "last_30_days": float(revenue_30d),
                        },
                        "products": {
                            "total": total_products,
                            "out_of_stock": out_of_stock,
                            "low_stock": low_stock,
                        },
                        "users": {
                            "total": total_users,
                            "customers": customers,
                            "sellers": sellers,
                        },
                        "comments": {
                            "total": total_comments,
                            "approved": approved_comments,
                            "unapproved": unapproved_comments,
                        },
                        "charts": {
                            "daily_orders": daily_orders,
                            "daily_revenue": daily_revenue,
                            "order_status": list(order_status_dist),
                            "payment_method": payment_method_dist,
                            "category_revenue": [
                                {
                                    "category_name": cat["category__name"],
                                    "total_revenue": float(cat["total_revenue"] or 0),
                                    "total_sold": cat["total_sold"] or 0,
                                }
                                for cat in category_revenue
                            ],
                        },
                    },
                }
            )
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserHistoryAPIView(APIView):
    """
    User history page data
    Returns paginated audit log for specific user
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request, user_id):
        """Get user history log"""
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 50))
            offset = (page - 1) * page_size

            # Verify user exists
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return Response({"status": "error", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            # Get history
            history = CustomerUserHistory.objects.filter(user_id=user_id).order_by("-timestamp")
            total_count = history.count()

            # Paginate
            items = history[offset : offset + page_size]

            # Serialize
            results = []
            for item in items:
                results.append(
                    {
                        "id": item.id,
                        "action": item.get_action_display() if hasattr(item, "get_action_display") else item.action,
                        "product_id": item.product_id,
                        "product_name": item.product.name if item.product else None,
                        "seller": item.seller.shop_name if item.seller else None,
                        "meta": item.meta,
                        "timestamp": item.timestamp.isoformat(),
                        "ip_address": item.ip_address,
                    }
                )

            return Response(
                {
                    "status": "success",
                    "user": {
                        "id": user.id,
                        "name": user.full_name or user.phone_number,
                        "email": user.email,
                    },
                    "data": {
                        "count": total_count,
                        "page": page,
                        "page_size": page_size,
                        "results": results,
                    },
                }
            )
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserOrderDetailAPIView(APIView):
    """
    Order detail page for admin
    Returns full order info with line items
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request, user_id, order_id):
        """Get order details"""
        try:
            # Verify user and order exist
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return Response({"status": "error", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            try:
                order = Order.objects.get(id=order_id, customer=user)
            except Order.DoesNotExist:
                return Response({"status": "error", "message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

            # Serialize order with items
            items = []
            for item in order.items.all():
                items.append(
                    {
                        "id": item.id,
                        "product_name": item.product.name if item.product else "Deleted product",
                        "quantity": item.quantity,
                        "price": float(item.price),
                        "subtotal": float(item.quantity * item.price),
                    }
                )

            return Response(
                {
                    "status": "success",
                    "order": {
                        "id": order.id,
                        "customer": {
                            "id": user.id,
                            "name": user.full_name or user.phone_number,
                            "email": user.email,
                            "phone": user.phone_number,
                        },
                        "status": order.status,
                        "total_price": float(order.total_price),
                        "created_at": order.created_at.isoformat(),
                        "updated_at": order.updated_at.isoformat(),
                        "items": items,
                    },
                }
            )
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
