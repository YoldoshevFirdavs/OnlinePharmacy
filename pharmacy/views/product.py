from datetime import timedelta

from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

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

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def popular(self, request):
        """
        Returns a list of popular medicines based on view count in a given time range.
        Accepts a 'range' query parameter (in days). Defaults to 7 days.
        """
        try:
            range_days = int(request.query_params.get("range", 7))
        except (ValueError, TypeError):
            range_days = 7

        if not 1 <= range_days <= 365:
            return Response({"error": "Range must be between 1 and 365 days."}, status=400)

        since_date = timezone.now() - timedelta(days=range_days)

        # Get top 10 most viewed product IDs
        popular_medicine_ids = (
            ProductViewHistory.objects.filter(timestamp__gte=since_date)
            .values("product")
            .annotate(view_count=Count("product"))
            .order_by("-view_count")
            .values_list("product", flat=True)[:10]
        )

        if not popular_medicine_ids:
            return Response([], status=200)

        # Fetch the actual medicine objects
        queryset = Medicine.available.filter(id__in=list(popular_medicine_ids))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(parent=None)  # Only show top-level categories by default
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated]  # Only authenticated users can create/update/delete categories
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


def product_list(request):
    products = Medicine.objects.all()
    return render(request, "pharmacy/product_list.html", {"products": products})
