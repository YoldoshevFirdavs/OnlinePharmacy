from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView


class UndoDeleteAPIView(APIView):
    """O'chirilgan obyektni qaytarish (Undo) API"""

    permission_classes = [IsAdminUser]

    def post(self, request):
        """Undo delete operation"""
        item_type = request.data.get("item_type")
        item_id = request.data.get("item_id")
        action = request.data.get("action")

        # Check if this is an undo action
        if action != "undo":
            return Response(
                {"success": False, "message": "Invalid action. Use action='undo' to restore deleted items."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find undo log entry
        from security.models import UndoLog

        try:
            with transaction.atomic():
                undo_log = UndoLog.objects.select_for_update().get(
                    item_type=item_type, item_id=item_id, is_restored=False, restore_until__gt=timezone.now()
                )
                success, message = undo_log.restore()
        except UndoLog.DoesNotExist:
            return Response(
                {"success": False, "message": "Undo entry not found or period expired (24 hours)"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if success:
            return Response({"success": True, "message": message}, status=status.HTTP_200_OK)
        else:
            return Response({"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST)


class DeletedItemsPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


class DeletedItemsAPIView(APIView):
    """O'chirilgan obyektlar ro'yxati (Undo uchun)"""

    permission_classes = [IsAdminUser]
    pagination_class = DeletedItemsPagination

    def get(self, request):
        """O'chirilgan va hali qaytarilishi mumkin bo'lgan obyektlar"""
        from security.models import UndoLog

        # Get all non-restored items within 24 hours
        deleted_items = (
            UndoLog.objects.filter(is_restored=False, restore_until__gt=timezone.now())
            .select_related("deleted_by")
            .order_by("-deleted_at")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(deleted_items, request, view=self)

        items_to_serialize = page if page is not None else deleted_items
        items_data = []
        for item in items_to_serialize:
            items_data.append(
                {
                    "id": item.id,
                    "item_type": item.item_type,
                    "item_id": item.item_id,
                    "item_name": item.item_name,
                    "deleted_at": item.deleted_at.isoformat(),
                    "restore_until": item.restore_until.isoformat(),
                    "is_expired": item.is_expired(),
                    "deleted_by": (
                        {
                            "id": item.deleted_by.id,
                            "full_name": item.deleted_by.full_name,
                            "email": item.deleted_by.email,
                        }
                        if item.deleted_by
                        else None
                    ),
                }
            )

        if page is not None:
            return paginator.get_paginated_response(items_data)

        return Response(
            {
                "count": len(items_data),
                "next": None,
                "previous": None,
                "results": items_data,
            },
            status=status.HTTP_200_OK,
        )
