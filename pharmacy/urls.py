from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.product import (
    CategoryViewSet,
    FlashSaleViewSet,
    MedicineImageViewSet,
    MedicineViewSet,
    ProductViewHistoryViewSet,
    ReviewViewSet,
    product_list
)

from .api_views import MedicineListView

app_name = 'pharmacy'
router = DefaultRouter()
router.register(r"products", MedicineViewSet)
router.register(r"reviews", ReviewViewSet)
router.register(r"view-history", ProductViewHistoryViewSet)
router.register(r"flash-sales", FlashSaleViewSet)
router.register(r"images", MedicineImageViewSet)

urlpatterns = [
    # DRF API endpoint - must be before /products/ to avoid HTML fallback
    path("products/", MedicineListView.as_view(), name="product_list_api"),
    path("products/<int:pk>/", MedicineListView.as_view(), name="product_detail_api"),
    path("products/", product_list, name="product_list"),
    path(
        "categories/",
        CategoryViewSet.as_view({"get": "list", "post": "create"}),
        name="category-list",
    ),
    path(
        "categories/<int:pk>/",
        CategoryViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="category-detail",
    ),
    path("", include(router.urls)),
]