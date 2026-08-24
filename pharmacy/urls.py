from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import MedicineListView, product_detail, product_suggestions
from .views.comments import ProductCommentViewSet
from .views.detail import product_detail, product_full_guide
from .views.product import (
    CategoryViewSet,
    FlashSaleViewSet,
    MedicineImageViewSet,
    MedicineViewSet,
    ProductViewHistoryViewSet,
    ReviewViewSet,
    product_list,
)
from .views.seller import seller_detail

app_name = "pharmacy"
router = DefaultRouter()
router.register(r"products", MedicineViewSet)
router.register(r"reviews", ReviewViewSet)
router.register(r"view-history", ProductViewHistoryViewSet)
router.register(r"flash-sales", FlashSaleViewSet)
router.register(r"images", MedicineImageViewSet)
router.register(r"comments", ProductCommentViewSet, basename="comment")

urlpatterns = [
    # API endpoints
    path("", MedicineListView.as_view(), name="product_list_api"),
    path("<int:product_id>/", product_detail, name="product_detail_api"),
    path("suggest/", product_suggestions, name="product_suggestions_api"),
    # Comments nested under products (handled by viewset)
    path(
        "<int:product_id>/comments/",
        ProductCommentViewSet.as_view({"get": "list", "post": "create"}),
        name="product_comments_list",
    ),
    # Product pages
    path("products/<int:product_id>/", product_detail, name="product_detail"),
    path("products/<int:product_id>/full/", product_full_guide, name="product_full_guide"),
    # Seller pages
    path("sellers/<int:seller_id>/", seller_detail, name="seller_detail"),
    # Legacy HTML views
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
