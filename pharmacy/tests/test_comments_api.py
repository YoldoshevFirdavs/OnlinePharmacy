"""
Unit and integration tests for Comments API (YouTube-style threaded)
Tests: ProductComment model, CommentLike model, ProductCommentViewSet
"""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from pharmacy.models.comments import CommentLike, ProductComment
from pharmacy.models.medicine import Category, Medicine
from users.models import CustomUser


class ProductCommentModelTestCase(TestCase):
    """Test ProductComment model functionality"""

    @classmethod
    def setUpTestData(cls):
        """Create test data"""
        cls.user = CustomUser.objects.create_user(
            phone_number="+998901234567", password="testpass123", full_name="Test User"
        )
        cls.category = Category.objects.create(name="Test Category", slug="test-cat")
        cls.product = Medicine.objects.create(
            name="Test Medicine", slug="test-medicine", category=cls.category, price=100.0, is_active=True
        )

    def test_create_top_level_comment(self):
        """Test creating a top-level comment with rating"""
        comment = ProductComment.objects.create(
            product=self.product, user=self.user, content="Great product!", rating=5
        )
        self.assertEqual(comment.product.id, self.product.id)
        self.assertEqual(comment.user.id, self.user.id)
        self.assertEqual(comment.rating, 5)
        self.assertIsNone(comment.parent)
        self.assertTrue(comment.is_approved)
        self.assertFalse(comment.is_ai_checked)

    def test_create_reply_comment(self):
        """Test creating a reply (nested comment)"""
        parent = ProductComment.objects.create(product=self.product, user=self.user, content="Great product!", rating=5)

        reply = ProductComment.objects.create(product=self.product, user=self.user, content="I agree!", parent=parent)

        self.assertEqual(reply.parent.id, parent.id)
        self.assertIsNone(reply.rating)  # Replies shouldn't have rating
        self.assertTrue(reply.is_reply())

    def test_comment_ordering(self):
        """Test comments are ordered by creation date (newest first)"""
        comment1 = ProductComment.objects.create(
            product=self.product, user=self.user, content="First comment", rating=3
        )
        comment2 = ProductComment.objects.create(
            product=self.product, user=self.user, content="Second comment", rating=4
        )

        comments = ProductComment.objects.filter(parent__isnull=True)
        self.assertEqual(comments[0].id, comment2.id)
        self.assertEqual(comments[1].id, comment1.id)


class CommentLikeModelTestCase(TestCase):
    """Test CommentLike (emoji reactions) model"""

    @classmethod
    def setUpTestData(cls):
        """Create test data"""
        cls.user1 = CustomUser.objects.create_user(phone_number="+998901234567", password="testpass123")
        cls.user2 = CustomUser.objects.create_user(phone_number="+998901234568", password="testpass123")
        cls.category = Category.objects.create(name="Test", slug="test")
        cls.product = Medicine.objects.create(name="Test", slug="test", category=cls.category, price=100.0)
        cls.comment = ProductComment.objects.create(product=cls.product, user=cls.user1, content="Test comment")

    def test_add_emoji_reaction(self):
        """Test adding an emoji reaction to comment"""
        reaction = CommentLike.objects.create(comment=self.comment, user=self.user1, emoji="like")
        self.assertEqual(reaction.emoji, "like")
        self.assertEqual(reaction.comment.id, self.comment.id)

    def test_unique_reaction_per_user(self):
        """Test that user can have only one reaction per emoji per comment"""
        CommentLike.objects.create(comment=self.comment, user=self.user1, emoji="like")

        # Trying to add same reaction again should fail
        with self.assertRaises(Exception):
            CommentLike.objects.create(comment=self.comment, user=self.user1, emoji="like")

    def test_different_emojis_per_user(self):
        """Test user can have different emoji reactions to same comment"""
        CommentLike.objects.create(comment=self.comment, user=self.user1, emoji="like")
        CommentLike.objects.create(comment=self.comment, user=self.user1, emoji="heart")

        reactions = CommentLike.objects.filter(comment=self.comment, user=self.user1)
        self.assertEqual(reactions.count(), 2)


class ProductCommentAPITestCase(APITestCase):
    """Integration tests for ProductComment API endpoints"""

    @classmethod
    def setUpTestData(cls):
        """Create test data"""
        cls.user1 = CustomUser.objects.create_user(
            phone_number="+998901234567", password="testpass123", full_name="User One"
        )
        cls.user2 = CustomUser.objects.create_user(
            phone_number="+998901234568", password="testpass123", full_name="User Two"
        )
        cls.category = Category.objects.create(name="Test", slug="test-cat")
        cls.product = Medicine.objects.create(
            name="Test Product", slug="test-product", category=cls.category, price=100.0, is_active=True
        )

    def setUp(self):
        self.client = APIClient()

    def test_get_comments_list(self):
        """Test getting comments list for a product"""
        # Create test comments
        ProductComment.objects.create(product=self.product, user=self.user1, content="Great!", rating=5)
        ProductComment.objects.create(product=self.product, user=self.user2, content="Good!", rating=4)

        response = self.client.get(f"/api/v1/products/{self.product.id}/comments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_create_comment_authenticated(self):
        """Test creating a comment when authenticated"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.post(
            f"/api/v1/products/{self.product.id}/comments/",
            {"content": "Excellent product!", "rating": 5, "product": self.product.id},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProductComment.objects.count(), 1)
        comment = ProductComment.objects.first()
        self.assertEqual(comment.user.id, self.user1.id)

    def test_create_comment_unauthenticated_forbidden(self):
        """Test that unauthenticated users can't create comments"""
        response = self.client.post(
            f"/api/v1/products/{self.product.id}/comments/",
            {"content": "Test", "rating": 5, "product": self.product.id},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_edit_own_comment(self):
        """Test editing own comment"""
        comment = ProductComment.objects.create(
            product=self.product, user=self.user1, content="Original content", rating=3
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.patch(f"/api/v1/products/comments/{comment.id}/", {"content": "Updated content"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "Updated content")

    def test_cannot_edit_others_comment(self):
        """Test that users can't edit others' comments"""
        comment = ProductComment.objects.create(product=self.product, user=self.user1, content="Original", rating=3)

        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(f"/api/v1/products/comments/{comment.id}/", {"content": "Hacked!"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_comment(self):
        """Test deleting comment"""
        comment = ProductComment.objects.create(product=self.product, user=self.user1, content="To delete", rating=2)

        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f"/api/v1/products/comments/{comment.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProductComment.objects.filter(id=comment.id).exists())

    def test_like_comment(self):
        """Test adding emoji reaction to comment"""
        comment = ProductComment.objects.create(product=self.product, user=self.user1, content="Great!", rating=5)

        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f"/api/v1/products/comments/{comment.id}/like/", {"emoji": "like"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CommentLike.objects.filter(comment=comment, user=self.user2, emoji="like").exists())

    def test_unlike_comment(self):
        """Test removing emoji reaction"""
        comment = ProductComment.objects.create(product=self.product, user=self.user1, content="Good", rating=4)
        CommentLike.objects.create(comment=comment, user=self.user2, emoji="heart")

        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f"/api/v1/products/comments/{comment.id}/unlike/", {"emoji": "heart"})

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CommentLike.objects.filter(comment=comment, user=self.user2, emoji="heart").exists())

    def test_create_reply_to_comment(self):
        """Test creating a reply to another comment"""
        parent = ProductComment.objects.create(product=self.product, user=self.user1, content="Original", rating=5)

        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            f"/api/v1/products/{self.product.id}/comments/",
            {"content": "I agree!", "parent": parent.id, "product": self.product.id},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reply = ProductComment.objects.get(parent=parent)
        self.assertEqual(reply.user.id, self.user2.id)
        self.assertIsNone(reply.rating)  # Replies shouldn't have rating
