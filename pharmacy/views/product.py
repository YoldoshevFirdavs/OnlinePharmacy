from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)

from pharmacy.models.medicine import Category, Medicine
from pharmacy.models.misc import FlashSale, MedicineImage, ProductViewHistory, Review
from pharmacy.permissons import IsVerifiedSeller
from pharmacy.serializers.misc import (
    CategorySerializer,
    FlashSaleSerializer,
    MedicineDetailSerializer,
    MedicineImageSerializer,
    MedicineListSerializer,
    ProductViewHistorySerializer,
    ReviewSerializer,
)


class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.available.all()
    serializer_class = MedicineListSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["category", "seller"]
    search_fields = ["name", "short_description"]
    ordering_fields = ["price", "updated_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MedicineDetailSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsVerifiedSeller()]
        return [AllowAny()]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(
        parent=None
    )  # Only show top-level categories by default
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [
                IsAuthenticated
            ]  # Only authenticated users can create/update/delete categories
        return [AllowAny()]  # Anyone can view categories


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.approved.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if self.action in ["list", "retrieve"]:
            return Review.approved.all()
        return Review.objects.all()


class FlashSaleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FlashSale.objects.none()
    serializer_class = FlashSaleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        now = timezone.now()
        return FlashSale.objects.filter(start_time__lte=now, end_time__gte=now)


class ProductViewHistoryViewSet(viewsets.ModelViewSet):
    queryset = ProductViewHistory.objects.all()
    serializer_class = ProductViewHistorySerializer
    permission_classes = [IsAuthenticated]


class MedicineImageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MedicineImage.objects.all()
    serializer_class = MedicineImageSerializer
