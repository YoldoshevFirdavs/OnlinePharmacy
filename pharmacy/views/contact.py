from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from pharmacy.models.misc import ContactMessage
from pharmacy.serializers.misc import ContactMessageSerializer


class ContactMessageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for contact form submissions.
    - POST /api/v1/contact/ - Submit contact form (public)
    - GET /api/v1/contact/ - List all messages (admin only)
    """

    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer

    def get_permissions(self):
        """
        Allow anyone to create, admins to list/view/update.
        """
        if self.action == "create":
            return [AllowAny()]
        return [IsAdminUser()]

    def create(self, request, *args, **kwargs):
        """
        Handle contact form submission.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"success": True, "message": "Xabaringiz muvaffaqiyatli yuborildi!", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        """
        Admin only - list all contact messages.
        """
        queryset = self.filter_queryset(self.get_queryset()).order_by("-created_at")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUser])
    def mark_as_read(self, request):
        """Mark selected messages as read."""
        message_ids = request.data.get("ids", [])
        ContactMessage.objects.filter(id__in=message_ids).update(is_read=True)
        return Response(
            {"success": True, "message": f"{len(message_ids)} ta xabar o'qildi deb belgilandi."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def mark_replied(self, request, pk=None):
        """Mark a message as replied."""
        contact = self.get_object()
        contact.replied = True
        contact.save()
        return Response({"success": True, "message": "Xabar javob bergan deb belgilandi."}, status=status.HTTP_200_OK)
