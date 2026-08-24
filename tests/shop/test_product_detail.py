from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory

from pharmacy.views.detail import product_detail


def test_product_detail_view_success():
    rf = RequestFactory()
    request = rf.get("/products/1/")
    request.user = SimpleNamespace(is_authenticated=False)

    mock_product = MagicMock()
    mock_product.id = 1
    mock_product.name = "Aspirin"
    mock_product.category = MagicMock()

    mock_qs = MagicMock()
    mock_qs.exclude.return_value = []

    with (
        patch("pharmacy.views.detail.get_object_or_404", return_value=mock_product),
        patch("pharmacy.models.Medicine.objects.filter", return_value=mock_qs),
        patch("pharmacy.views.detail.render") as mock_render,
    ):
        mock_render.return_value = SimpleNamespace(status_code=200)
        response = product_detail(request, product_id=1)

    assert response.status_code == 200
    mock_render.assert_called_once()


def test_product_detail_404_when_not_found():
    rf = RequestFactory()
    request = rf.get("/products/999/")
    request.user = SimpleNamespace(is_authenticated=False)

    from django.http import Http404

    with patch("pharmacy.views.detail.get_object_or_404", side_effect=Http404):
        try:
            product_detail(request, product_id=999)
            assert False, "Should raise Http404"
        except Http404:
            assert True
