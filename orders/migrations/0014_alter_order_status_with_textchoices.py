# Generated migration - Add OrderStatus TextChoices enum

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0013_order_driver"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("Pending", "Pending"),
                    ("Processing", "Processing"),
                    ("Ready for Delivery", "Ready for Delivery"),
                    ("Accepted", "Accepted"),
                    ("Picked Up", "Picked Up"),
                    ("On The Way", "On The Way"),
                    ("Arrived", "Arrived"),
                    ("Delivered", "Delivered"),
                    ("Canceled", "Canceled"),
                    ("Returned", "Returned"),
                ],
                default="Pending",
                help_text="Order status",
                max_length=20,
            ),
        ),
    ]
