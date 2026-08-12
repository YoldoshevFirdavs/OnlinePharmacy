from rest_framework import serializers

from orders.models import Cart, CartItem, Order, OrderItem
from pharmacy.models.medicine import Medicine


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "price_at_order"]


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "order_items",
            "total_price",
            "status",
            "address",
            "created_at",
        ]
        read_only_fields = ["customer", "total_price"]

    def get_total_price(self, obj):
        return sum(
            item.price_at_order * item.quantity for item in obj.order_items.all()
        )

    def create(self, validated_data):
        user = self.context["request"].user
        cart_items = CartItem.objects.filter(cart__user=user)
        if not cart_items.exists():
            raise serializers.ValidationError("Savatcha bo'sh.")

        for item in cart_items:
            if item.quantity > item.product.stock:
                raise serializers.ValidationError(
                    f"{item.product.name} uchun yetarli stock yo'q."
                )

        total = sum(item.product.price * item.quantity for item in cart_items)
        order = Order.objects.create(customer=user, total_price=total, **validated_data)
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_at_order=item.product.price,
            )
            item.product.stock -= item.quantity
            item.product.save()
        cart_items.delete()
        return order


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_name", "quantity", "total_price"]

    def get_total_price(self, obj):
        return obj.product.price * obj.quantity

    def validate_quantity(self, value):
        product_id = self.initial_data.get("product")
        try:
            medicine = Medicine.objects.get(id=product_id)
        except Medicine.DoesNotExist:
            raise serializers.ValidationError("Mahsulot topilmadi.")
        if value > medicine.stock:
            raise serializers.ValidationError("Omborda yetarli dori yo'q.")
        return value


class CartSummarySerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "grand_total", "created_at"]

    def get_grand_total(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())


class OrderListSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()
    short_address = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "status", "total_price", "short_address", "created_at"]
        read_only_fields = [
            "id",
            "status",
            "total_price",
            "short_address",
            "created_at",
        ]

    def get_total_price(self, obj):
        if hasattr(obj, "total_price") and obj.total_price is not None:
            return obj.total_price
        return sum(
            item.price_at_order * item.quantity for item in obj.order_items.all()
        )

    def get_short_address(self, obj):
        return (
            (obj.address[:80] + "...")
            if obj.address and len(obj.address) > 80
            else obj.address
        )


class OrderDetailSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "order_items",
            "total_price",
            "status",
            "address",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "order_items",
            "total_price",
            "created_at",
        ]
