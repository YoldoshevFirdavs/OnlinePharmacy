from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q

from pharmacy.models.comments import ProductComment, CommentLike
from pharmacy.models.medicine import Medicine
from pharmacy.serializers.comments import (
    ProductCommentSerializer,
    ProductCommentCreateSerializer,
    CommentLikeSerializer,
)


class CommentPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductCommentViewSet(viewsets.ModelViewSet):
    """
    Viewset for product comments (YouTube-style threaded)
    
    Endpoints:
    - GET /api/v1/products/<product_id>/comments/ - List comments (paginated)
    - POST /api/v1/products/<product_id>/comments/ - Create comment
    - GET /api/v1/comments/<id>/ - Retrieve comment
    - PATCH /api/v1/comments/<id>/ - Update comment (author only)
    - DELETE /api/v1/comments/<id>/ - Delete comment (author only)
    - POST /api/v1/comments/<id>/like/ - Like/react to comment
    - POST /api/v1/comments/<id>/unlike/ - Remove like/reaction
    """
    
    serializer_class = ProductCommentSerializer
    pagination_class = CommentPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Get comments for product, only approved ones for non-staff"""
        product_id = self.kwargs.get('product_id')
        queryset = ProductComment.objects.filter(
            product_id=product_id,
            parent__isnull=True  # Only top-level comments
        ).select_related('user', 'parent')
        
        # Staff can see unapproved comments
        if not (self.request.user and self.request.user.is_staff):
            queryset = queryset.filter(is_approved=True)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProductCommentCreateSerializer
        return ProductCommentSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        """Auto-set user to request user"""
        product_id = self.kwargs.get('product_id')
        product = get_object_or_404(Medicine, id=product_id)
        serializer.save(product=product, user=self.request.user)
    
    def perform_update(self, serializer):
        """Only allow author to edit"""
        if serializer.instance.user != self.request.user:
            raise permissions.PermissionDenied("You can only edit your own comments")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only allow author to delete"""
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("You can only delete your own comments")
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """
        Add emoji reaction to comment
        
        Body:
        {
            "emoji": "like"  # or "heart", "laugh", "wow", "sad", "angry"
        }
        """
        comment = self.get_object()
        emoji = request.data.get('emoji')
        
        if not emoji:
            return Response(
                {'error': 'emoji is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_emojis = [choice[0] for choice in CommentLike.EMOJI_CHOICES]
        if emoji not in valid_emojis:
            return Response(
                {'error': f'Invalid emoji. Valid options: {", ".join(valid_emojis)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reaction, created = CommentLike.objects.get_or_create(
            comment=comment,
            user=request.user,
            emoji=emoji
        )
        
        # Update likes count if this is a "like" emoji
        if emoji == 'like':
            comment.likes_count = comment.emoji_reactions.filter(emoji='like').count()
            comment.save()
        
        serializer = CommentLikeSerializer(reaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def unlike(self, request, pk=None):
        """
        Remove emoji reaction from comment
        
        Body:
        {
            "emoji": "like"
        }
        """
        comment = self.get_object()
        emoji = request.data.get('emoji')
        
        if not emoji:
            return Response(
                {'error': 'emoji is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            reaction = CommentLike.objects.get(
                comment=comment,
                user=request.user,
                emoji=emoji
            )
            reaction.delete()
            
            # Update likes count if this is a "like" emoji
            if emoji == 'like':
                comment.likes_count = comment.emoji_reactions.filter(emoji='like').count()
                comment.save()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CommentLike.DoesNotExist:
            return Response(
                {'error': 'Reaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
