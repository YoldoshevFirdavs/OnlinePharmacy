from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import CustomUser, Seller
from pharmacy.models.medicine import Medicine


class ProductComment(models.Model):
    """
    Threaded comment system for products (YouTube-style)
    Supports nested replies, ratings, likes, and emoji reactions
    """
    
    product = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='product_comments'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    content = models.TextField()
    rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1-5 rating (optional, only for top-level comments)"
    )
    is_approved = models.BooleanField(default=True)
    is_ai_checked = models.BooleanField(default=False)
    ai_summary = models.TextField(
        blank=True,
        help_text="AI-generated summary (for moderation purposes)"
    )
    ai_toxicity_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Toxicity score 0-1 from AI analysis"
    )
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_approved', '-created_at']),
        ]
    
    def __str__(self):
        parent_str = f" (reply to {self.parent.id})" if self.parent else ""
        return f"{self.user.full_name or self.user.phone_number} - {self.product.name}{parent_str}"
    
    def is_reply(self):
        """Check if this comment is a reply to another comment"""
        return self.parent is not None
    
    def get_author_type(self):
        """Return 'seller' if author is a seller, 'user' otherwise"""
        try:
            Seller.objects.get(user=self.user)
            return 'seller'
        except Seller.DoesNotExist:
            return 'user'


class CommentLike(models.Model):
    """Track likes/emoji reactions on comments"""
    
    EMOJI_CHOICES = [
        ('like', '👍'),
        ('heart', '❤️'),
        ('laugh', '😂'),
        ('wow', '😮'),
        ('sad', '😢'),
        ('angry', '😠'),
    ]
    
    comment = models.ForeignKey(
        ProductComment,
        on_delete=models.CASCADE,
        related_name='emoji_reactions'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='comment_reactions'
    )
    emoji = models.CharField(max_length=10, choices=EMOJI_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('comment', 'user', 'emoji')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} reacted {self.emoji} to comment {self.comment.id}"


class CommentAnalysis(models.Model):
    """
    Store AI analysis results for comment batches
    Generated when batch of 10+ comments is sent to AI
    """
    
    comments = models.ManyToManyField(ProductComment, related_name='analyses')
    summary = models.TextField(help_text="AI-generated summary of comments batch")
    toxicity_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Average toxicity score for batch"
    )
    flagged_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of toxic/problematic comments in batch"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Analysis batch {self.id} - {self.comments.count()} comments - Toxicity: {self.toxicity_score:.2f}"
