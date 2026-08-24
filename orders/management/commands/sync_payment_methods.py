from django.core.management.base import BaseCommand

from orders.models import Order


class Command(BaseCommand):
    help = "Update payment_method for orders that have Payment records (Stripe payments)"

    def handle(self, *args, **options):
        # Find orders with Payment records but payment_method='cash'
        mismatched = Order.objects.filter(payments__isnull=False, payment_method="cash")
        count = mismatched.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No orders need updating"))
            return

        # Update them to payment_method='card'
        updated = mismatched.update(payment_method="card")

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated} orders from payment_method=cash to card"))
