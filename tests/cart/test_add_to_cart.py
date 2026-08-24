from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from orders.api_cart_checkout import CartAddAPIView, CartSummaryAPIView, CheckoutAPIView


@pytest.mark.django_db
def test_cart_add_authenticated():
    request = SimpleNamespace(data={"product_id": 1, "quantity": 2}, user=SimpleNamespace(is_authenticated=True, pk=1))

    mock_product = MagicMock()
    mock_product.id = 1
    mock_product.name = "Aspirin"
    mock_product.price = 10000

    mock_cart = MagicMock()
    mock_item = MagicMock()
    mock_item.quantity = 2
    mock_item.product = mock_product

    mock_cart.items.all.return_value = [mock_item]
    mock_cart.items.select_related.return_value.all.return_value = [mock_item]

    with (
        patch("orders.api_cart_checkout.get_object_or_404", return_value=mock_product),
        patch("orders.models.Cart.objects.get_or_create", return_value=(mock_cart, False)),
        patch("orders.models.CartItem.objects.select_for_update") as mock_item_mgr,
    ):
        mock_item_mgr.return_value.get_or_create.return_value = (mock_item, True)
        view = CartAddAPIView()
        response = view.post(request)

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["item_count"] == 2
    assert response.data["cart_total"] == 20000.0


@pytest.mark.django_db
def test_cart_summary_authenticated():
    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, pk=1))
    mock_cart = MagicMock()
    mock_item = MagicMock()
    mock_item.id = 1
    mock_item.quantity = 3
    mock_item.product.id = 10
    mock_item.product.name = "Paracetamol"
    mock_item.product.price = 5000
    mock_item.product.image = None

    mock_cart.items.select_related.return_value.all.return_value = [mock_item]

    with patch("orders.models.Cart.objects.filter") as mock_filter:
        mock_filter.return_value.first.return_value = mock_cart
        view = CartSummaryAPIView()
        response = view.get(request)

    assert response.status_code == 200
    assert response.data["item_count"] == 3
    assert response.data["cart_total"] == 15000.0
