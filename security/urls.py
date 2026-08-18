from django.urls import path

from .views import (
    FingerprintBanStatusView,
    ClearIPBlockView,
    UnbanFingerprintView,
    AdminBanStatsView,
    UnbanRecordView,
)

app_name = "security"

urlpatterns = [
    path("api/fingerprint-ban-status/", FingerprintBanStatusView.as_view(), name="api_fingerprint_ban_status"),
    path("api/clear-ip-block/", ClearIPBlockView.as_view(), name="api_clear_ip_block"),
    path("api/unban-fingerprint/", UnbanFingerprintView.as_view(), name="api_unban_fingerprint"),
    path("api/ban-stats/", AdminBanStatsView.as_view(), name="api_ban_stats"),
    path("api/unban-record/<int:pk>/", UnbanRecordView.as_view(), name="api_unban_record"),
]
