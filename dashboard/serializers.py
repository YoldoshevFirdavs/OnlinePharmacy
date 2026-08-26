from django.urls import reverse
from rest_framework import serializers

from orders.models import Order
from pharmacy.models import Category, Medicine
from users.models import CustomUser

# Default image URLs
DEFAULT_AVATAR_URL = "/static/images/default/default_avatar.png"
DEFAULT_PRODUCT_URL = "/static/images/default/default_product.png"
DEFAULT_ICON_URL = "/static/images/default/default_icon.png"


class DashboardCategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    medicines_count = serializers.IntegerField(source="product_count", read_only=True)
    edit_url = serializers.SerializerMethodField()
    delete_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "product_count",
            "medicines_count",
            "edit_url",
            "delete_url",
        ]

    def get_edit_url(self, obj):
        return reverse("dashboard:category_edit", kwargs={"pk": obj.pk})

    def get_delete_url(self, obj):
        return reverse("dashboard:category_delete", kwargs={"pk": obj.pk})


class DashboardProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="—")
    quantity = serializers.IntegerField(source="stock", read_only=True)
    image_url = serializers.SerializerMethodField()
    edit_url = serializers.SerializerMethodField()
    delete_url = serializers.SerializerMethodField()

    class Meta:
        model = Medicine
        fields = [
            "id",
            "name",
            "slug",
            "category_name",
            "price",
            "stock",
            "quantity",
            "is_active",
            "image_url",
            "edit_url",
            "delete_url",
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

    def get_edit_url(self, obj):
        return reverse("dashboard:medicine_edit", kwargs={"pk": obj.pk})

    def get_delete_url(self, obj):
        return reverse("dashboard:medicine_delete", kwargs={"pk": obj.pk})


class DashboardOrderSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "username",
            "total_price",
            "total",
            "status",
            "items_count",
            "item_count",
            "created_at",
        ]

    def get_user(self, obj):
        if obj.user:
            request = self.context.get("request")
            avatar_url = DEFAULT_AVATAR_URL
            if (
                obj.user.avatar
                and hasattr(obj.user.avatar, "url")
                and hasattr(obj.user.avatar, "name")
                and obj.user.avatar.name
            ):
                avatar_url = request.build_absolute_uri(obj.user.avatar.url) if request else obj.user.avatar.url

            return {
                "id": obj.user.id,
                "email": obj.user.email,
                "full_name": obj.user.full_name,
                "avatar_url": avatar_url,
            }
        return None

    def get_username(self, obj):
        if obj.user:
            return obj.user.full_name or obj.user.email or obj.user.phone_number or str(obj.user.pk)
        return "Anonymous"

    def get_total(self, obj):
        return str(obj.total_price)

    def get_items_count(self, obj):
        return obj.order_items.count()

    def get_item_count(self, obj):
        return self.get_items_count(obj)


class DashboardUserSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)
    edit_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "phone_number",
            "role",
            "is_staff",
            "is_superuser",
            "is_active",
            "date_joined",
            "edit_url",
        ]

    def get_username(self, obj):
        return obj.email or obj.phone_number or obj.full_name or str(obj.pk)

    def get_edit_url(self, obj):
        return reverse("dashboard:user_edit", kwargs={"pk": obj.pk})
