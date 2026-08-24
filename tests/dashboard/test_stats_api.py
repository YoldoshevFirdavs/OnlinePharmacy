from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from dashboard.api_stats import DailyOrdersStatsAPIView, SummaryStatsAPIView


def test_daily_orders_stats_api_returns_labels_and_data():
    mock_qs = MagicMock()
    mock_qs.values.return_value.annotate.return_value.order_by.return_value = []

    with (
        patch("orders.models.Order.objects.filter", return_value=mock_qs),
        patch("django.core.cache.cache.get", return_value=None),
        patch("django.core.cache.cache.set"),
    ):
        request = SimpleNamespace(
            query_params={"range": "7"}, user=SimpleNamespace(is_staff=True, is_authenticated=True)
        )
        response = DailyOrdersStatsAPIView().get(request=request)

    assert response.status_code == 200
    data = response.data
    assert "labels" in data
    assert "data" in data
    assert len(data["labels"]) == 7
    assert len(data["data"]) == 7
    assert data["count_total"] == 0


def test_summary_stats_api_returns_expected_kpis():
    mock_orders_qs = MagicMock()
    mock_orders_qs.count.return_value = 5
    mock_orders_qs.aggregate.return_value = {"total": 150000.0}

    mock_user_qs = MagicMock()
    mock_user_qs.count.return_value = 42

    with (
        patch("orders.models.Order.objects.filter", return_value=mock_orders_qs),
        patch("orders.models.Order.objects.count", return_value=25),
        patch("users.models.CustomUser.objects.filter", return_value=mock_user_qs),
        patch("django.core.cache.cache.get", return_value=None),
        patch("django.core.cache.cache.set"),
    ):
        request = SimpleNamespace(query_params={}, user=SimpleNamespace(is_staff=True, is_authenticated=True))
        response = SummaryStatsAPIView().get(request=request)

    assert response.status_code == 200
    data = response.data
    assert data["orders_today"] == 5
    assert data["revenue_today"] == 150000.0
    assert data["active_users"] == 42
    assert data["orders_total"] == 25
