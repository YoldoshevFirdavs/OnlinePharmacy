from django.contrib import admin
from orders.models import Order, OrderItem, Cart, CartItem, OrderDelivery

@admin.register(OrderDelivery)
class OrderDeliveryAdmin(admin.ModelAdmin):
    list_display = ('order', 'driver', 'arrived_at', 'wait_seconds', 'driver_earnings', 'created_at')
    list_filter = ('driver', 'created_at')
    search_fields = ('order__id', 'driver__user__full_name', 'driver__user__phone_number')
    raw_id_fields = ('order', 'driver')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'driver', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'driver']
    search_fields = ['id', 'customer__full_name', 'customer__phone_number', 'driver__user__full_name', 'driver__user__phone_number']
    raw_id_fields = ('customer', 'driver')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price_at_order']
    search_fields = ['order__id', 'product__name']
    raw_id_fields = ('order', 'product')

admin.site.register(Cart)
admin.site.register(CartItem)