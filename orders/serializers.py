from rest_framework import serializers
from orders.models import Cart, CartItem, Order, OrderItem, OrderDelivery
from pharmacy.models.medicine import Medicine
from users.serializers import DriverSerializer
from django.utils import timezone

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price_at_order']

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'customer', 'order_items', 'total_price', 'status', 'address', 'created_at']
        read_only_fields = ['customer', 'total_price']

    def get_total_price(self, obj):
        return sum(item.price_at_order * item.quantity for item in obj.order_items.all())

    def create(self, validated_data):
        user = self.context['request'].user
        cart_items = CartItem.objects.filter(cart__user=user)
        if not cart_items.exists():
            raise serializers.ValidationError("Savatcha bo'sh.")

        for item in cart_items:
            if item.quantity > item.product.stock:
                raise serializers.ValidationError(f"{item.product.name} uchun yetarli stock yo'q.")

        total = sum(item.product.price * item.quantity for item in cart_items)
        order = Order.objects.create(customer=user, total_price=total, **validated_data)
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_at_order=item.product.price
            )
            item.product.stock -= item.quantity
            item.product.save()
        cart_items.delete()
        return order

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'quantity', 'total_price']

    def get_total_price(self, obj):
        return obj.product.price * obj.quantity

    def validate_quantity(self, value):
        product_id = self.initial_data.get('product')
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
        fields = ['id', 'items', 'grand_total', 'created_at']

    def get_grand_total(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())

class OrderDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDelivery
        fields = '__all__'
        read_only_fields = ('order', 'driver', 'created_at', 'updated_at', 'driver_earnings')

class DriverOrderSerializer(serializers.ModelSerializer):
    customer_full_name = serializers.ReadOnlyField(source='customer.full_name')
    customer_phone_number = serializers.ReadOnlyField(source='customer.phone_number')
    order_items = OrderItemSerializer(many=True, read_only=True)
    driver = DriverSerializer(read_only=True)
    delivery_details = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer_full_name', 'customer_phone_number', 'driver',
            'total_price', 'status', 'address', 'created_at',
            'assigned_at', 'accepted_at', 'picked_up_at', 'on_the_way_at', 'delivered_at',
            'driver_notes', 'order_items', 'delivery_details'
        ]
        read_only_fields = [
            'id', 'customer_full_name', 'customer_phone_number', 'driver',
            'total_price', 'created_at', 'assigned_at', 'accepted_at',
            'picked_up_at', 'on_the_way_at', 'delivered_at', 'order_items', 'delivery_details'
        ]

    def get_delivery_details(self, obj):
        try:
            if hasattr(obj, 'delivery_details') and obj.delivery_details is not None:
                return OrderDeliverySerializer(obj.delivery_details).data
            delivery = OrderDelivery.objects.filter(order=obj).first()
            if delivery:
                return OrderDeliverySerializer(delivery).data
            return None
        except OrderDelivery.DoesNotExist:
            return None

class OrderListSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()
    short_address = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'status', 'total_price', 'short_address', 'created_at']
        read_only_fields = ['id', 'status', 'total_price', 'short_address', 'created_at']

    def get_total_price(self, obj):
        if hasattr(obj, 'total_price') and obj.total_price is not None:
            return obj.total_price
        return sum(item.price_at_order * item.quantity for item in obj.order_items.all())

    def get_short_address(self, obj):
        return (obj.address[:80] + '...') if obj.address and len(obj.address) > 80 else obj.address

class OrderDetailSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    delivery_details = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'order_items', 'total_price', 'status',
            'address', 'created_at', 'delivery_details'
        ]
        read_only_fields = ['id', 'customer', 'order_items', 'total_price', 'created_at', 'delivery_details']

    def get_delivery_details(self, obj):
        delivery = OrderDelivery.objects.filter(order=obj).first()
        if delivery:
            return OrderDeliverySerializer(delivery).data
        return None

class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            ('Accepted', 'Accepted by Driver'),
            ('Picked Up', 'Picked Up by Driver'),
            ('On The Way', 'On The Way for Delivery'),
            ('Arrived', 'Arrived at Customer Location'),
            ('Delivered', 'Delivered'),
        ]
    )

class ArrivalSerializer(serializers.Serializer):
    arrived_at = serializers.DateTimeField(required=True, help_text="Timestamp when the driver arrived at the customer's location.")
    wait_seconds = serializers.IntegerField(required=False, default=0, min_value=0, help_text="Time in seconds the driver waited at the customer's location.")

    def validate_arrived_at(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("Arrival time cannot be in the future.")
        return value

class LocationSerializer(serializers.Serializer):
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    timestamp = serializers.DateTimeField(required=False, default=timezone.now)

    def validate_timestamp(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("Timestamp cannot be in the future.")
        return value