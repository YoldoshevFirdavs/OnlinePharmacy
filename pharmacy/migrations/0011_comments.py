# Generated migration for ProductComment, CommentLike, CommentAnalysis models

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0010_customeruserhistory"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField()),
                (
                    "rating",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="1-5 rating (optional, only for top-level comments)",
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                    ),
                ),
                ("is_approved", models.BooleanField(default=True)),
                ("is_ai_checked", models.BooleanField(default=False)),
                (
                    "ai_summary",
                    models.TextField(blank=True, help_text="AI-generated summary (for moderation purposes)"),
                ),
                (
                    "ai_toxicity_score",
                    models.FloatField(
                        blank=True,
                        help_text="Toxicity score 0-1 from AI analysis",
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(1),
                        ],
                    ),
                ),
                ("likes_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="replies",
                        to="pharmacy.productcomment",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="pharmacy.medicine"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="product_comments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CommentLike",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "emoji",
                    models.CharField(
                        choices=[
                            ("like", "👍"),
                            ("heart", "❤️"),
                            ("laugh", "😂"),
                            ("wow", "😮"),
                            ("sad", "😢"),
                            ("angry", "😠"),
                        ],
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "comment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="emoji_reactions",
                        to="pharmacy.productcomment",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comment_reactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("comment", "user", "emoji")},
            },
        ),
        migrations.CreateModel(
            name="CommentAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("summary", models.TextField(help_text="AI-generated summary of comments batch")),
                (
                    "toxicity_score",
                    models.FloatField(
                        help_text="Average toxicity score for batch",
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(1),
                        ],
                    ),
                ),
                (
                    "flagged_count",
                    models.PositiveIntegerField(default=0, help_text="Number of toxic/problematic comments in batch"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("comments", models.ManyToManyField(related_name="analyses", to="pharmacy.productcomment")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="productcomment",
            index=models.Index(fields=["product", "-created_at"], name="pharmacy_pr_product_created_idx"),
        ),
        migrations.AddIndex(
            model_name="productcomment",
            index=models.Index(fields=["user", "-created_at"], name="pharmacy_pr_user_created_idx"),
        ),
        migrations.AddIndex(
            model_name="productcomment",
            index=models.Index(fields=["is_approved", "-created_at"], name="pharmacy_pr_approved_created_idx"),
        ),
    ]
