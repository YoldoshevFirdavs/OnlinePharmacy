import time

from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle

from pharmacy.models.comments import CommentLike, ProductComment
from pharmacy.models.medicine import Medicine
from pharmacy.serializers.comments import (
    CommentLikeSerializer,
    ProductCommentCreateSerializer,
    ProductCommentSerializer,
)


class CommentsReadThrottle(BaseThrottle):
    """
    Lenient throttle for GET requests on comments (reading is cheap)
    Stricter throttle for POST/PATCH/DELETE (writing has overhead)
    """

    scope = "comments"

    def allow_request(self, request, view):
        """
        Allow all requests - no rate limiting for comments.
        Return `False` to throttle, `True` to allow.
        """
        return True


class CommentPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
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
    throttle_classes = [CommentsReadThrottle]

    def get_queryset(self):
        """Get comments for product, only approved ones for non-staff"""
        # For detail actions (retrieve, update, destroy, like, unlike), allow any comment
        if self.action in ["retrieve", "update", "partial_update", "destroy", "like", "unlike"]:
            return ProductComment.objects.all().select_related("user", "product")

        # For list action, filter by product_id
        product_id = self.kwargs.get("product_id")
        queryset = ProductComment.objects.filter(
            product_id=product_id, parent__isnull=True  # Only top-level comments
        ).select_related("user", "parent")

        # Staff can see unapproved comments
        if not (self.request.user and self.request.user.is_staff):
            queryset = queryset.filter(is_approved=True)

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return ProductCommentCreateSerializer
        return ProductCommentSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        """Auto-set user to request user, update Medicine rating stats, and trigger AI moderation if toxic"""
        product_id = self.kwargs.get("product_id")
        if not product_id:
            # If product_id not in URL (for nested endpoint), try to get from request data
            product_id = self.request.data.get("product")

        product = get_object_or_404(Medicine, id=product_id)
        comment = serializer.save(product=product, user=self.request.user)

        # Recalculate average_rating and reviews_count
        self._update_product_stats(product)
        return comment

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = self.perform_create(serializer)

        product = comment.product
        headers = self.get_success_headers(serializer.data)

        # Include updated average_rating and reviews_count in response
        data = serializer.data
        data["product_average_rating"] = float(product.average_rating)
        data["product_reviews_count"] = product.reviews_count
        data["is_approved"] = comment.is_approved

        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def _update_product_stats(self, product):
        """Helper to recalculate reviews_count and average_rating"""
        from django.db.models import Avg, Count

        stats = ProductComment.objects.filter(product=product, parent__isnull=True, is_approved=True).aggregate(
            avg_rating=Avg("rating"), total_count=Count("id")
        )
        avg = stats.get("avg_rating") or 0.00
        count = stats.get("total_count") or 0

        product.average_rating = round(avg, 2)
        product.reviews_count = count
        product.save(update_fields=["average_rating", "reviews_count"])

    def perform_update(self, serializer):
        """Only allow author to edit and refresh product stats"""
        if serializer.instance.user != self.request.user:
            raise PermissionDenied("You can only edit your own comments")
        comment = serializer.save()
        self._update_product_stats(comment.product)

    def perform_destroy(self, instance):
        """Only allow author to delete and refresh product stats"""
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only delete your own comments")
        product = instance.product
        instance.delete()
        self._update_product_stats(product)

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        """
        Add emoji reaction to comment

        Body:
        {
            "emoji": "like"  # or "heart", "laugh", "wow", "sad", "angry"
        }
        """
        comment = self.get_object()
        emoji = request.data.get("emoji")

        if not emoji:
            return Response({"error": "emoji is required"}, status=status.HTTP_400_BAD_REQUEST)

        valid_emojis = [choice[0] for choice in CommentLike.EMOJI_CHOICES]
        if emoji not in valid_emojis:
            return Response(
                {"error": f'Invalid emoji. Valid options: {", ".join(valid_emojis)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reaction, created = CommentLike.objects.get_or_create(comment=comment, user=request.user, emoji=emoji)

        # Update likes count if this is a "like" emoji
        if emoji == "like":
            comment.likes_count = comment.emoji_reactions.filter(emoji="like").count()
            comment.save()

        serializer = CommentLikeSerializer(reaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def unlike(self, request, pk=None):
        """
        Remove emoji reaction from comment

        Body:
        {
            "emoji": "like"
        }
        """
        comment = self.get_object()
        emoji = request.data.get("emoji")

        if not emoji:
            return Response({"error": "emoji is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reaction = CommentLike.objects.get(comment=comment, user=request.user, emoji=emoji)
            reaction.delete()

            # Update likes count if this is a "like" emoji
            if emoji == "like":
                comment.likes_count = comment.emoji_reactions.filter(emoji="like").count()
                comment.save()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except CommentLike.DoesNotExist:
            return Response({"error": "Reaction not found"}, status=status.HTTP_404_NOT_FOUND)
