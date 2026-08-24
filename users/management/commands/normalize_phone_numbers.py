import logging

import phonenumbers
from django.conf import settings
from django.core.management.base import BaseCommand

from users.models import CustomUser, Deliverer  # NOTE: Import models that might have phone numbers

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normalizes phone numbers in CustomUser and Deliverer models to E.164 format."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting phone number normalization..."))
        default_region = getattr(settings, "PHONENUMBER_DEFAULT_REGION", "UZ")  # NOTE: Get default region from settings

        # Normalize CustomUser phone numbers
        users_to_update = []
        for user in CustomUser.objects.all():
            if user.phone_number:
                try:
                    parsed_number = phonenumbers.parse(user.phone_number, default_region)
                    if phonenumbers.is_valid_number(parsed_number):
                        e164_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                        if user.phone_number != e164_number:
                            user.phone_number = e164_number
                            users_to_update.append(user)
                            self.stdout.write(self.style.SUCCESS(f"Normalized user {user.id} phone: {e164_number}"))
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"Invalid phone number for user {user.id}: {user.phone_number}")
                        )
                except phonenumbers.phonenumberutil.NumberParseException:
                    self.stdout.write(
                        self.style.ERROR(f"Could not parse phone number for user {user.id}: {user.phone_number}")
                    )
            else:
                self.stdout.write(self.style.NOTICE(f"User {user.id} has no phone number."))

        if users_to_update:
            CustomUser.objects.bulk_update(users_to_update, ["phone_number"])
            self.stdout.write(
                self.style.SUCCESS(f"Successfully updated {len(users_to_update)} CustomUser phone numbers.")
            )
        else:
            self.stdout.write(self.style.INFO("No CustomUser phone numbers needed normalization."))

        # Normalize Deliverer phone numbers (assuming Deliverer has a phone_number field or links to CustomUser)
        # If Deliverer model has its own phone_number field, uncomment and adjust below
        deliverers_to_update = []
        for deliverer in Deliverer.objects.all():
            if deliverer.phone_number:  # Assuming Deliverer has a direct phone_number field
                try:
                    parsed_number = phonenumbers.parse(deliverer.phone_number, default_region)
                    if phonenumbers.is_valid_number(parsed_number):
                        e164_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                        if deliverer.phone_number != e164_number:
                            deliverer.phone_number = e164_number
                            deliverers_to_update.append(deliverer)
                            self.stdout.write(
                                self.style.SUCCESS(f"Normalized deliverer {deliverer.id} phone: {e164_number}")
                            )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Invalid phone number for deliverer {deliverer.id}: {deliverer.phone_number}"
                            )
                        )
                except phonenumbers.phonenumberutil.NumberParseException:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Could not parse phone number for deliverer {deliverer.id}: {deliverer.phone_number}"
                        )
                    )
            else:
                self.stdout.write(self.style.NOTICE(f"Deliverer {deliverer.id} has no phone number."))

        if deliverers_to_update:
            Deliverer.objects.bulk_update(deliverers_to_update, ["phone_number"])
            self.stdout.write(
                self.style.SUCCESS(f"Successfully updated {len(deliverers_to_update)} Deliverer phone numbers.")
            )
        else:
            self.stdout.write(self.style.INFO("No Deliverer phone numbers needed normalization."))

        self.stdout.write(self.style.SUCCESS("Phone number normalization completed."))
