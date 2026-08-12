from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.product import (
    CategoryViewSet,
    FlashSaleViewSet,
    MedicineImageViewSet,
    MedicineViewSet,
    ProductViewHistoryViewSet,
    ReviewViewSet,
)

router = DefaultRouter()
router.register(r"products", MedicineViewSet)
router.register(r"reviews", ReviewViewSet)
router.register(r"view-history", ProductViewHistoryViewSet)
router.register(r"flash-sales", FlashSaleViewSet)
router.register(r"images", MedicineImageViewSet)

urlpatterns = [
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
