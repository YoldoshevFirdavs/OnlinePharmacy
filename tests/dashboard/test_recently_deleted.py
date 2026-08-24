from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from dashboard.api_admin_undo import DeletedItemsAPIView, UndoDeleteAPIView


def test_deleted_items_api_returns_json_payload():
    item = SimpleNamespace(
        id=9,
        item_type="order",
        item_id=12,
        item_name="Order #12",
        deleted_at=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00Z"),
        restore_until=SimpleNamespace(isoformat=lambda: "2026-01-02T00:00:00Z"),
        is_expired=lambda: False,
        deleted_by=SimpleNamespace(id=3, full_name="Admin User", email="admin@example.com"),
    )

    mock_queryset = MagicMock()
    mock_queryset.select_related.return_value.order_by.return_value = [item]

    with patch("security.models.UndoLog.objects.filter", return_value=mock_queryset):
        response = DeletedItemsAPIView().get(request=SimpleNamespace(query_params={}))

    assert response.status_code == 200
    payload = response.data
    assert payload["count"] == 1
    assert payload["results"][0]["item_id"] == 12


def test_undo_delete_api_calls_restore():
    mock_log = MagicMock()
    mock_log.restore.return_value = (True, "Restored")

    with (
        patch("django.db.transaction.atomic"),
        patch("security.models.UndoLog.objects.select_for_update") as mock_select_for_update,
    ):
        mock_select_for_update.return_value.get.return_value = mock_log
        response = UndoDeleteAPIView().post(
            request=SimpleNamespace(
                data={"action": "undo", "item_type": "order", "item_id": 12},
            )
        )

    assert response.status_code == 200
    assert response.data["success"] is True
    mock_log.restore.assert_called_once()
