# Generated migration - Remove plaintext card fields from Seller model

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0027_alter_seller_credit_card_and_more"),
    ]

    operations = [
        # Remove unsafe plaintext card fields
        migrations.RemoveField(
            model_name="seller",
            name="credit_card",
        ),
        migrations.RemoveField(
            model_name="seller",
            name="credit_card_expiry",
        ),
        migrations.RemoveField(
            model_name="seller",
            name="credit_card_holder",
        ),
        # Add safe Stripe Connect account reference
        migrations.AddField(
            model_name="seller",
            name="stripe_account_id",
            field=models.CharField(
                blank=True, help_text="Stripe Connect account ID for payouts", max_length=255, null=True
            ),
        ),
    ]
