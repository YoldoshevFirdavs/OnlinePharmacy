from rest_framework import serializers

from pharmacy.models.comments import CommentLike, ProductComment


class CommentLikeSerializer(serializers.ModelSerializer):
    """Serializer for emoji reactions on comments"""

    user_id = serializers.IntegerField(read_only=True, source="user.id")
    emoji_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CommentLike
        fields = ["id", "user_id", "emoji", "emoji_display", "created_at"]
        read_only_fields = fields

    def get_emoji_display(self, obj):
        """Return emoji character"""
        return dict(CommentLike.EMOJI_CHOICES).get(obj.emoji, obj.emoji)


class ProductCommentNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for replies (to prevent infinite recursion)"""

    user = serializers.SerializerMethodField(read_only=True)
    author_type = serializers.SerializerMethodField(read_only=True)
    emoji_reactions = CommentLikeSerializer(many=True, read_only=True)

    class Meta:
        model = ProductComment
        fields = [
            "id",
            "user",
            "author_type",
            "content",
            "rating",
            "is_approved",
            "likes_count",
            "emoji_reactions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_user(self, obj):
        """Return user info (name only, no PII)"""
        avatar_url = None
        try:
            if hasattr(obj.user, "avatar") and obj.user.avatar and obj.user.avatar.name:
                avatar_url = obj.user.avatar.url
        except (ValueError, AttributeError):
            avatar_url = None

        return {
            "id": obj.user.id,
            "name": obj.user.full_name or obj.user.phone_number or "Anonymous",
            "avatar": avatar_url,
        }

    def get_author_type(self, obj):
        """Return 'seller' if author is a seller"""
        return obj.get_author_type()


class ProductCommentSerializer(serializers.ModelSerializer):
    """Full serializer for product comments with nested replies"""

    user = serializers.SerializerMethodField(read_only=True)
    author_type = serializers.SerializerMethodField(read_only=True)
    replies = ProductCommentNestedSerializer(many=True, read_only=True)
    emoji_reactions = CommentLikeSerializer(many=True, read_only=True)

    class Meta:
        model = ProductComment
        fields = [
            "id",
            "product",
            "user",
            "author_type",
            "content",
            "rating",
            "is_approved",
            "likes_count",
            "replies",
            "emoji_reactions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["is_approved", "likes_count", "replies", "emoji_reactions"]

    def get_user(self, obj):
        """Return user info (name and avatar only, no email/phone)"""
        avatar_url = None
        try:
            if hasattr(obj.user, "avatar") and obj.user.avatar and obj.user.avatar.name:
                avatar_url = obj.user.avatar.url
        except (ValueError, AttributeError):
            avatar_url = None

        return {
            "id": obj.user.id,
            "name": obj.user.full_name or obj.user.phone_number or "Anonymous",
            "avatar": avatar_url,
        }

    def get_author_type(self, obj):
        """Return 'seller' if author is a seller"""
        return obj.get_author_type()


class ProductCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new comments"""

    class Meta:
        model = ProductComment
        fields = ["product", "content", "rating", "parent"]

    def validate_rating(self, value):
        """Rating only allowed for top-level comments"""
        parent = self.initial_data.get("parent")
        if parent and value is not None:
            raise serializers.ValidationError("Replies cannot have ratings")
        if not parent and value is None:
            # Rating is optional for top-level
            pass
        if value and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

    def create(self, validated_data):
        """Create comment and auto-trigger AI analysis check"""
        # Add user from request context
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
