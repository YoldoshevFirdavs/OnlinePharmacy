from rest_framework import filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from pharmacy.models import Medicine
from pharmacy.serializers.misc import MedicineListSerializer


class MedicinePagination(PageNumberPagination):
    """Default pagination with 50 items per page"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class MedicineListView(ListAPIView):
    """
    Medicine list endpoint with pagination and ordering.
    
    Default ordering: -reviews_count, -average_rating, -updated_at
    Default pagination: 50 per page
    """
    serializer_class = MedicineListSerializer
    pagination_class = MedicinePagination
    permission_classes = [AllowAny]
    
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ['name', 'short_description']
    ordering_fields = ['price', 'reviews_count', 'average_rating', 'updated_at', 'stock']
    ordering = ['-reviews_count', '-average_rating', '-updated_at']
    
    def get_queryset(self):
        queryset = Medicine.objects.all().order_by('-reviews_count', '-average_rating', '-updated_at')
        
        # Category filter
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Active filter
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
