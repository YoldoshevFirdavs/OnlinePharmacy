from django.contrib import admin

from orders.models import Cart, CartItem, DeliveryOrder, Order, OrderItem


@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "driver",
        "status",
        "assigned_at",
    )
    list_filter = ("driver", "status", "assigned_at")
    search_fields = (
        "order__id",
        "driver__user__full_name",
        "driver__user__phone_number",
    )
    raw_id_fields = ("order", "driver")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "total_price", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = [
        "id",
        "user__full_name",
        "user__phone_number",
    ]
    raw_id_fields = ("user",)  # faqat mavjud fieldni yozamiz


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product", "quantity", "price_at_order"]
    search_fields = ["order__id", "product__name"]
    raw_id_fields = ("order", "product")


admin.site.register(Cart)
admin.site.register(CartItem)
