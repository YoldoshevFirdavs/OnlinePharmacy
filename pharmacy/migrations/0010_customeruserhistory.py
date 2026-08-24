# Generated migration for CustomerUserHistory model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("pharmacy", "0010_populate_site_config"),  # Depend on the actual 0010
        ("users", "0001_initial"),  # Adjust to users app migrations
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerUserHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("view_product", "Mahsulot ko'rildi"),
                            ("view_seller", "Sotuvchi ko'rildi"),
                            ("add_to_cart", "Savatchaga qo'shildi"),
                            ("comment_create", "Fikr qoldirildi"),
                            ("comment_edit", "Fikr tahrirlandi"),
                            ("comment_delete", "Fikr o'chirildi"),
                            ("order_create", "Buyurtma qilindi"),
                            ("order_cancel", "Buyurtma bekor qilindi"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    "meta",
                    models.JSONField(
                        blank=True, default=dict, help_text="Additional action data (e.g., comment_id, order_id)"
                    ),
                ),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                (
                    "product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="view_history",
                        to="pharmacy.medicine",
                    ),
                ),
                (
                    "seller",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="seller_history",
                        to="users.seller",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_history",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Customer History",
                "verbose_name_plural": "Customer Histories",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="customeruserhistory",
            index=models.Index(fields=["user", "-timestamp"], name="pharmacy_cu_user_id_timestamp_idx"),
        ),
        migrations.AddIndex(
            model_name="customeruserhistory",
            index=models.Index(fields=["action", "-timestamp"], name="pharmacy_cu_action_timestamp_idx"),
        ),
        migrations.AddIndex(
            model_name="customeruserhistory",
            index=models.Index(fields=["product", "-timestamp"], name="pharmacy_cu_product_timestamp_idx"),
        ),
    ]
