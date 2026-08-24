# Security app views - Contains security-related API endpoints

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import CustomUser


class SecurityAPIView(APIView):
    """Base API view for security endpoints."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]


class FingerprintBanStatusView(SecurityAPIView):
    """Fingerprint ban status for a user."""

    def get(self, request):
        """Get fingerprint ban status."""
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Import here to avoid circular imports
        from users.services import BanService

        ban_info = BanService.get_ban_info(user)

        return Response(
            {
                "is_banned": ban_info["is_banned"],
                "ban_reason": ban_info["ban_reason"],
                "ban_until": ban_info["ban_until"],
                "is_permanent": ban_info["is_permanent"],
                "fingerprint_banned": ban_info["fingerprint_banned"],
                "banned_by": ban_info["banned_by"],
            }
        )


class ClearIPBlockView(SecurityAPIView):
    """Clear IP block for a user."""

    def post(self, request):
        """Clear IP block."""
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        from users.services import BanService

        BanService.clear_ip_block(user)

        return Response({"success": True, "message": f"IP block cleared for {user.email}"})


class UnbanFingerprintView(SecurityAPIView):
    """Unban user by fingerprint."""

    def post(self, request):
        """Unban by fingerprint."""
        user_id = request.data.get("user_id")
        fingerprint = request.data.get("fingerprint")

        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        from users.services import BanService

        BanService.unban_fingerprint(user, fingerprint)

        return Response({"success": True, "message": f"Fingerprint unban processed for {user.email}"})


class AdminBanStatsView(SecurityAPIView):
    """Get admin ban statistics."""

    def get(self, request):
        """Get ban statistics."""
        from users.services import BanService

        stats = BanService.get_admin_ban_stats()

        return Response(
            {
                "total_bans": stats["total_bans"],
                "active_bans": stats["active_bans"],
                "permanent_bans": stats["permanent_bans"],
                "temporary_bans": stats["temporary_bans"],
                "fingerprint_bans": stats["fingerprint_bans"],
                "ip_blocks": stats["ip_blocks"],
                "unban_requests": stats["unban_requests"],
            }
        )


class UnbanRecordView(SecurityAPIView):
    """Unban a BanRecord by marking it inactive."""

    def post(self, request, pk):
        """Mark ban record as inactive (unban)."""
        from .models import BanRecord

        try:
            ban = BanRecord.objects.get(id=pk)
        except BanRecord.DoesNotExist:
            return Response({"success": False, "message": "Ban record not found"}, status=status.HTTP_404_NOT_FOUND)

        # Mark as inactive (unban)
        ban.is_active = False
        ban.save()

        return Response(
            {
                "success": True,
                "message": f"Ban record {pk} has been marked as inactive",
                "ban": {
                    "id": ban.id,
                    "ip": ban.ip,
                    "fingerprint": ban.fingerprint,
                    "is_active": ban.is_active,
                },
            }
        )
