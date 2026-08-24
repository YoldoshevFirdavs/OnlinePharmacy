"""
Admin Order API endpoints
- Create Order with items
- Update Order
"""

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order, OrderItem
from users.models import CustomUser


class AdminOrderCreateAPIView(APIView):
    """
    Admin Order Create API
    POST /admin/api/orders/

    Request body:
    {
        "customer_id": 1,
        "status": "Pending",
        "address": "Address text",
        "notes": "Notes",
        "items": [
            {"product_id": 1, "quantity": 2, "unit_price": 100.0}
        ]
    }
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            data = request.data

            # Validate required fields
            if not data.get("customer_id"):
                return Response(
                    {"status": "error", "message": "customer_id required"}, status=status.HTTP_400_BAD_REQUEST
                )

            if not data.get("items") or len(data.get("items", [])) == 0:
                return Response({"status": "error", "message": "items required"}, status=status.HTTP_400_BAD_REQUEST)

            # Validate customer exists
            try:
                customer = CustomUser.objects.get(id=data["customer_id"])
            except CustomUser.DoesNotExist:
                return Response({"status": "error", "message": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

            # Calculate total and validate stock
            total_price = 0
            items_data = data.get("items", [])

            for item in items_data:
                if not item.get("product_id") or not item.get("quantity"):
                    return Response(
                        {"status": "error", "message": "Each item must have product_id and quantity"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                quantity = item.get("quantity", 0)
                unit_price = item.get("unit_price", 0)

                # Calculate line total
                total_price += quantity * unit_price

            # Create order with transaction
            with transaction.atomic():
                order = Order.objects.create(
                    user=customer,
                    status=data.get("status", "Pending"),
                    address=data.get("address", ""),
                    notes=data.get("notes", ""),
                    total_price=total_price,
                )

                # Create order items
                for item in items_data:
                    OrderItem.objects.create(
                        order=order,
                        product_id=item["product_id"],
                        quantity=item["quantity"],
                        price_at_order=item.get("unit_price", 0),
                    )

            return Response(
                {
                    "status": "success",
                    "message": "Order created successfully",
                    "order_id": order.id,
                    "total_price": total_price,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminOrderUpdateAPIView(APIView):
    """
    Admin Order Update API
    PUT/PATCH /admin/api/orders/<id>/
    """

    permission_classes = [IsAdminUser]

    def get_order(self, pk):
        try:
            return Order.objects.get(id=pk)
        except Order.DoesNotExist:
            return None

    def put(self, request, pk):
        order = self.get_order(pk)

        if not order:
            return Response({"status": "error", "message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            data = request.data

            # Update with transaction
            with transaction.atomic():
                # Update order fields
                if "status" in data:
                    order.status = data["status"]
                if "address" in data:
                    order.address = data["address"]
                if "notes" in data:
                    order.notes = data["notes"]

                # Update items if provided
                if "items" in data:
                    # Delete existing items
                    order.items.all().delete()

                    # Calculate new total
                    total_price = 0
                    for item in data["items"]:
                        if item.get("product_id") and item.get("quantity"):
                            total_price += item["quantity"] * item.get("unit_price", 0)
                            OrderItem.objects.create(
                                order=order,
                                product_id=item["product_id"],
                                quantity=item["quantity"],
                                price_at_order=item.get("unit_price", 0),
                            )

                    order.total_price = total_price

                order.save()

            return Response(
                {
                    "status": "success",
                    "message": "Order updated successfully",
                    "order_id": order.id,
                    "total_price": order.total_price,
                }
            )

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminOrderListAPIView(APIView):
    """
    Admin Order List API
    GET /admin/api/orders/

    Query params:
    - page: page number
    - page_size: items per page (default: 25)
    - search: search by id, customer, status
    - ordering: created_at, total_price (default: -created_at)
    - status: filter by status
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            from django.db.models import Q

            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 25))
            search = request.query_params.get("search", "")
            ordering = request.query_params.get("ordering", "-created_at")
            status_filter = request.query_params.get("status", "")

            # Base query
            orders = Order.objects.select_related("user").all()

            # Search
            if search:
                orders = orders.filter(
                    Q(id__icontains=search)
                    | Q(user__email__icontains=search)
                    | Q(user__full_name__icontains=search)
                    | Q(status__icontains=search)
                )

            # Status filter
            if status_filter:
                orders = orders.filter(status=status_filter)

            # Ordering
            orders = orders.order_by(ordering)

            # Total count
            total_count = orders.count()

            # Pagination
            offset = (page - 1) * page_size
            orders = orders[offset : offset + page_size]

            # Serialize
            results = []
            for order in orders:
                results.append(
                    {
                        "id": order.id,
                        "customer": {
                            "id": order.user.id,
                            "email": order.user.email,
                            "name": order.user.full_name or order.user.phone_number,
                        },
                        "total_price": float(order.total_price),
                        "status": order.status,
                        "created_at": order.created_at.isoformat(),
                        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
                        "items_count": order.items.count(),
                    }
                )

            return Response(
                {
                    "status": "success",
                    "count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "results": results,
                }
            )

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminOrderDetailAPIView(APIView):
    """
    Admin Order Detail API
    GET /dashboard/api/admin/orders/<id>/
    """

    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            order = Order.objects.select_related("user").prefetch_related("order_items").get(id=pk)

            # Get items with product info
            items = []
            for item in order.order_items.all():
                items.append(
                    {
                        "id": item.id,
                        "product_id": item.product_id,
                        "product_name": item.product.name if item.product else "Unknown",
                        "quantity": item.quantity,
                        "price_at_order": float(item.price_at_order),
                        "line_total": float(item.quantity * item.price_at_order),
                    }
                )

            return Response(
                {
                    "status": "success",
                    "order": {
                        "id": order.id,
                        "customer": {
                            "id": order.user.id,
                            "email": order.user.email,
                            "name": order.user.full_name or order.user.phone_number,
                            "phone": order.user.phone_number,
                            "address": order.user.address,
                        },
                        "total_price": float(order.total_price),
                        "status": order.status,
                        "address": order.address,
                        "notes": order.notes,
                        "items": items,
                        "created_at": order.created_at.isoformat(),
                        "updated_at": order.updated_at.isoformat() if hasattr(order, "updated_at") else None,
                        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
                    },
                }
            )

        except Order.DoesNotExist:
            return Response({"status": "error", "message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
