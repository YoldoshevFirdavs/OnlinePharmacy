from rest_framework import serializers

from orders.models import Cart, CartItem
from pharmacy.models.medicine import Category, Medicine
from pharmacy.models.misc import ContactMessage, FlashSale, MedicineImage, ProductViewHistory, Review
from users.models import Seller

# Default image URLs
DEFAULT_AVATAR_URL = "/static/images/default/default_avatar.png"
DEFAULT_PRODUCT_URL = "/static/images/default/default_product.png"
DEFAULT_ICON_URL = "/static/images/default/default_icon.png"


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


class SellerBasicSerializer(serializers.ModelSerializer):
    """Minimal seller info for product lists"""

    user_name = serializers.ReadOnlyField(source="user.full_name")
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Seller
        fields = ["id", "shop_name", "user_name", "avatar", "avatar_url", "rating"]

    def get_avatar_url(self, obj):
        if obj.avatar and hasattr(obj.avatar, "url") and hasattr(obj.avatar, "name") and obj.avatar.name:
            return obj.avatar.url
        return DEFAULT_AVATAR_URL


class MedicineListSerializer(serializers.ModelSerializer):
    category = serializers.ReadOnlyField(source="category.name")
    seller_info = SellerBasicSerializer(source="seller", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Medicine
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "price",
            "main_image",
            "image_url",
            "average_rating",
            "reviews_count",
            "stock",
            "seller_info",
        ]

    def get_image_url(self, obj):
        if (
            obj.main_image
            and hasattr(obj.main_image, "url")
            and hasattr(obj.main_image, "name")
            and obj.main_image.name
        ):
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.main_image.url)
            return obj.main_image.url
        return DEFAULT_PRODUCT_URL


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
    seller_info = SellerBasicSerializer(source="seller", read_only=True)
    main_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Medicine
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "price",
            "stock",
            "main_image",
            "main_image_url",
            "images",
            "reviews",
            "short_description",
            "instruction",
            "side_effects",
            "contraindications",
            "average_rating",
            "reviews_count",
            "seller_info",
        ]

    def get_main_image_url(self, obj):
        if (
            obj.main_image
            and hasattr(obj.main_image, "url")
            and hasattr(obj.main_image, "name")
            and obj.main_image.name
        ):
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.main_image.url)
            return obj.main_image.url
        return DEFAULT_PRODUCT_URL


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


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "message", "created_at", "is_read", "replied"]
        read_only_fields = ["id", "created_at", "is_read", "replied"]
