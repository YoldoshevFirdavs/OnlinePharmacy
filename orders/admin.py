from django.contrib import admin

from orders.models import Cart, CartItem, Order, OrderItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "total_price", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = [
        "id",
        "customer__full_name",
        "customer__phone_number",
    ]
    raw_id_fields = ("customer",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product", "quantity", "price_at_order"]
    search_fields = ["order__id", "product__name"]
    raw_id_fields = ("order", "product")


admin.site.register(Cart)
admin.site.register(CartItem)
