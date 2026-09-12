from django.contrib import admin

from orders.models import Cart, CartItem, DeliveryOrder, Order, OrderItem


@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "status",
        "assigned_at",
    )
    list_filter = ("status", "assigned_at")
    search_fields = ("order__id",)
    raw_id_fields = ("order",)


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
