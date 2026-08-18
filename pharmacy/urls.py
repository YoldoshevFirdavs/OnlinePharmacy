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
from .views.detail import product_detail, product_full_guide
from .views.seller import seller_detail
from .views.history import UserHistoryViewSet
from .views.comments import ProductCommentViewSet

from .api_views import MedicineListView, product_suggestions

app_name = 'pharmacy'
router = DefaultRouter()
router.register(r"products", MedicineViewSet)
router.register(r"reviews", ReviewViewSet)
router.register(r"view-history", ProductViewHistoryViewSet)
router.register(r"flash-sales", FlashSaleViewSet)
router.register(r"images", MedicineImageViewSet)
router.register(r"user/history", UserHistoryViewSet, basename="user-history")

urlpatterns = [
    # API endpoints
    path("api/v1/products/", MedicineListView.as_view(), name="product_list_api"),
    path("api/v1/products/suggest/", product_suggestions, name="product_suggestions_api"),
    
    # Comments nested under products
    path("api/v1/products/<int:product_id>/comments/", 
         ProductCommentViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name="product_comments_list"),
    path("api/v1/comments/<int:pk>/", 
         ProductCommentViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
         name="comment_detail"),
    path("api/v1/comments/<int:pk>/like/",
         ProductCommentViewSet.as_view({'post': 'like'}),
         name="comment_like"),
    path("api/v1/comments/<int:pk>/unlike/",
         ProductCommentViewSet.as_view({'post': 'unlike'}),
         name="comment_unlike"),
    
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