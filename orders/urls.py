from django.urls import include, path
from rest_framework.routers import DefaultRouter

from orders.views import CartViewSet, OrderViewSet

router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="orders")
router.register(r"cart", CartViewSet, basename="cart")

urlpatterns = [
    path("my_orders/", OrderViewSet.as_view({"get": "list"}), name="my-orders"),
    path("", include(router.urls)),
]
