from django.urls import include, path
from rest_framework.routers import DefaultRouter

from orders.views import CartViewSet, DriverOrderViewSet, OrderAcceptView, OrderStatusUpdateView, OrderViewSet

router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="orders")
router.register(r"cart", CartViewSet, basename="cart")
router.register(
    r"deliverer/orders", DriverOrderViewSet, basename="deliverer-orders"
)  # NOTE: Changed path and basename to match frontend

urlpatterns = [
    path("my_orders/", OrderViewSet.as_view({"get": "list"}), name="my-orders"),
    path("orders/<int:pk>/accept/", OrderAcceptView.as_view(), name="order-accept"),
    path("orders/<int:pk>/status/", OrderStatusUpdateView.as_view(), name="order-status"),
    path("", include(router.urls)),
]
