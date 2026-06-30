from django.urls import path, include
from rest_framework.routers import DefaultRouter
from orders.views import (
    OrderViewSet,
    CartViewSet,
    DriverOrderViewSet,
    OrderAcceptView,
    OrderStatusUpdateView,
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'drivers/orders', DriverOrderViewSet, basename='driver-orders')

urlpatterns = [
    path('my-orders/', OrderViewSet.as_view({'get': 'list'}), name='my-orders'),
    path('orders/<int:pk>/accept/', OrderAcceptView.as_view(), name='order-accept'),
    path('orders/<int:pk>/status/', OrderStatusUpdateView.as_view(), name='order-status'),
    path('', include(router.urls)),
]
