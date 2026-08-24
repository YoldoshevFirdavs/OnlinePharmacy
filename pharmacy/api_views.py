from decimal import Decimal

from django.db.models import Q
from rest_framework import filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from pharmacy.models import Medicine
from pharmacy.serializers.misc import MedicineListSerializer


class MedicinePagination(PageNumberPagination):
    """Default pagination with 50 items per page for shop"""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class MedicineListView(ListAPIView):
    """
    Enhanced medicine list endpoint with comprehensive filtering and pagination.

    Supports:
    - Full-text search (name, short_description)
    - Category filtering (single or multiple)
    - Price range (min_price, max_price)
    - Brand/Seller filtering
    - Availability (has stock)
    - Rating range (rating_min, rating_max)
    - Review count range (reviews_min, reviews_max)
    - Multiple ordering options

    Query params:
    - q: Search query
    - category: Category ID (comma-separated for multiple)
    - min_price, max_price: Price range
    - brand: Seller/Brand ID
    - has_stock: true/false
    - rating_min, rating_max: Rating range (0-5)
    - reviews_min, reviews_max: Review count range
    - ordering: Field name with optional - prefix (e.g., -price, name)
    - page: Page number
    - page_size: Items per page (default 24, max 100)
    """

    serializer_class = MedicineListSerializer
    pagination_class = MedicinePagination
    permission_classes = [AllowAny]

    filter_backends = [
        filters.OrderingFilter,
    ]
    ordering_fields = [
        "price",
        "reviews_count",
        "average_rating",
        "updated_at",
        "stock",
        "name",
    ]
    ordering = ["-reviews_count", "-average_rating", "-updated_at"]

    def get_queryset(self):
        queryset = Medicine.objects.all().select_related("category", "seller").filter(is_active=True)

        # Search query
        search_q = self.request.query_params.get("q", "").strip()
        if search_q:
            queryset = queryset.filter(Q(name__icontains=search_q) | Q(short_description__icontains=search_q))

        # Category filter (comma-separated for multiple)
        category_ids = self.request.query_params.get("category", "").strip()
        if category_ids:
            try:
                cat_list = [int(c.strip()) for c in category_ids.split(",") if c.strip()]
                if cat_list:
                    queryset = queryset.filter(category_id__in=cat_list)
            except (ValueError, TypeError):
                pass

        # Price range filters
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")

        if min_price:
            try:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            except (ValueError, TypeError):
                pass

        if max_price:
            try:
                queryset = queryset.filter(price__lte=Decimal(max_price))
            except (ValueError, TypeError):
                pass

        # Brand/Seller filter
        brand_id = self.request.query_params.get("brand")
        if brand_id:
            try:
                queryset = queryset.filter(seller_id=int(brand_id))
            except (ValueError, TypeError):
                pass

        # Availability filter (has_stock)
        has_stock = self.request.query_params.get("has_stock")
        if has_stock:
            if has_stock.lower() == "true":
                queryset = queryset.filter(stock__gt=0)
            elif has_stock.lower() == "false":
                queryset = queryset.filter(stock=0)

        # Rating range filters
        rating_min = self.request.query_params.get("rating_min")
        rating_max = self.request.query_params.get("rating_max")

        if rating_min:
            try:
                queryset = queryset.filter(average_rating__gte=Decimal(rating_min))
            except (ValueError, TypeError):
                pass

        if rating_max:
            try:
                queryset = queryset.filter(average_rating__lte=Decimal(rating_max))
            except (ValueError, TypeError):
                pass

        # Reviews count range filters
        reviews_min = self.request.query_params.get("reviews_min")
        reviews_max = self.request.query_params.get("reviews_max")

        if reviews_min:
            try:
                queryset = queryset.filter(reviews_count__gte=int(reviews_min))
            except (ValueError, TypeError):
                pass

        if reviews_max:
            try:
                queryset = queryset.filter(reviews_count__lte=int(reviews_max))
            except (ValueError, TypeError):
                pass

        # Ordering
        ordering = self.request.query_params.get("ordering")
        if ordering:
            # Validate ordering field to prevent injection
            order_field = ordering.lstrip("-")
            if order_field in self.ordering_fields:
                queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by(*self.ordering)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def product_suggestions(request):
    """
    Search suggestions endpoint - returns product names/descriptions matching query.

    Query params:
    - q: Search query (minimum 1 character)
    - limit: Max number of suggestions (default 10, max 50)

    Returns: List of {id, name, rating, price}
    """
    query = request.query_params.get("q", "").strip()

    if not query or len(query) < 1:
        return Response({"suggestions": []})

    try:
        limit = int(request.query_params.get("limit", 10))
        limit = min(max(limit, 1), 50)  # Clamp between 1-50
    except (ValueError, TypeError):
        limit = 10

    suggestions = (
        Medicine.objects.filter(
            Q(name__icontains=query) | Q(short_description__icontains=query), is_active=True, stock__gt=0
        )
        .select_related("category")
        .values("id", "name", "average_rating", "price")
        .order_by("-reviews_count", "-average_rating")[:limit]
    )

    return Response({"suggestions": list(suggestions)})


@api_view(["GET"])
@permission_classes([AllowAny])
def product_detail(request, product_id):
    """
    Product detail endpoint - returns full product information including stock, images, etc.

    Path params:
    - product_id: Medicine ID

    Returns: {id, name, description, price, stock, average_rating, reviews_count, category, seller, ...}
    """
    try:
        product = Medicine.objects.select_related("category", "seller").get(id=product_id, is_active=True)
    except Medicine.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    data = {
        "id": product.id,
        "name": product.name,
        "instruction": product.instruction,
        "short_description": product.short_description,
        "price": float(product.price),
        "stock": product.stock,
        "average_rating": float(product.average_rating) if product.average_rating else 0,
        "reviews_count": product.reviews_count,
        "category": (
            {
                "id": product.category.id,
                "name": product.category.name,
            }
            if product.category
            else None
        ),
        "seller": (
            {
                "id": product.seller.id,
                "name": product.seller.shop_name or product.seller.user.full_name,
            }
            if product.seller
            else None
        ),
        "is_active": product.is_active,
    }

    return Response(data)
