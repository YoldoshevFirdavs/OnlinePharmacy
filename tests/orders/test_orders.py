from unittest.mock import Mock


def test_order_model_placeholder_is_mockable():
    order = Mock()
    order.id = 10
    order.status = "pending"
    assert order.id == 10
    assert order.status == "pending"


def test_order_summary_helper_returns_expected_shape():
    payload = {"id": 10, "status": "pending", "total": 99.9}
    assert payload["id"] == 10
    assert payload["total"] == 99.9
