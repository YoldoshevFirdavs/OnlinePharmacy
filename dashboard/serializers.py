from django.urls import reverse
from rest_framework import serializers

from pharmacy.models import Category, Medicine
from orders.models import Order
from users.models import CustomUser


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
        if obj.main_image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.main_image.url)
            return obj.main_image.url
        return None

    def get_edit_url(self, obj):
        return reverse("dashboard:medicine_edit", kwargs={"pk": obj.pk})

    def get_delete_url(self, obj):
        return reverse("dashboard:medicine_delete", kwargs={"pk": obj.pk})


class DashboardOrderSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    driver = serializers.SerializerMethodField()
    deliverer = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "username",
            "total_price",
            "total",
            "status",
            "items_count",
            "item_count",
            "driver",
            "deliverer",
            "created_at",
        ]

    def get_customer(self, obj):
        user = obj.customer
        return user.full_name or user.email or user.phone_number or str(user.pk)

    def get_username(self, obj):
        return self.get_customer(obj)

    def get_total(self, obj):
        return str(obj.total_price)

    def get_items_count(self, obj):
        return obj.order_items.count()

    def get_item_count(self, obj):
        return self.get_items_count(obj)

    def get_driver(self, obj):
        if not obj.driver:
            return "Tayinlanmagan"
        return obj.driver.full_name or obj.driver.email or obj.driver.phone_number

    def get_deliverer(self, obj):
        return self.get_driver(obj)


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
