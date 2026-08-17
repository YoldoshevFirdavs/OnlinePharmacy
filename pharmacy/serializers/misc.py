from rest_framework import serializers

from orders.models import Cart, CartItem
from pharmacy.models.medicine import Category, Medicine
from pharmacy.models.misc import FlashSale, MedicineImage, ProductViewHistory, Review


class RecursiveField(serializers.Serializer):
    """
    Recursive serializer for nested categories.
    """

    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class CategorySerializer(serializers.ModelSerializer):
    children = RecursiveField(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "is_default", "children"]


class MedicineImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineImage
        fields = ["image", "is_primary"]


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.full_name")

    class Meta:
        model = Review
        fields = ["id", "user", "rating", "content", "date_posted"]


class MedicineListSerializer(serializers.ModelSerializer):
    category = serializers.ReadOnlyField(source="category.name")

    class Meta:
        model = Medicine
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "price",
            "main_image",
            "average_rating",
            "stock",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product_details = MedicineListSerializer(source="product", read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_details", "quantity", "total_price"]

    def get_total_price(self, obj):
        return obj.product.price * obj.quantity


class MedicineDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    images = MedicineImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Medicine
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "price",
            "stock",
            "images",
            "reviews",
            "short_description",
            "instruction",
            "side_effects",
            "contraindications",
            "average_rating",
            "reviews_count",
        ]


class FlashSaleSerializer(serializers.ModelSerializer):
    product_details = MedicineListSerializer(source="product", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = FlashSale
        fields = [
            "id",
            "product",
            "product_details",
            "discount_percentage",
            "start_time",
            "end_time",
            "is_active",
        ]


class ProductViewHistorySerializer(serializers.ModelSerializer):

    product = MedicineListSerializer(read_only=True)

    class Meta:
        model = ProductViewHistory
        fields = ["id", "product", "timestamp"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "user", "items", "grand_total", "created_at"]

    def get_grand_total(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())
