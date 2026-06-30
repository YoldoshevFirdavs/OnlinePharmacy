import phonenumbers
from django.conf import settings
from django.core.management.base import BaseCommand
from users.models import CustomUser, Deliverer

class Command(BaseCommand):
    help = 'Normalizes phone numbers in CustomUser and Deliverer models to E.164 format.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting phone number normalization...'))
        
        # Normalize CustomUser phone numbers
        users_updated = 0
        users_skipped = 0
        for user in CustomUser.objects.all():
            if user.phone_number:
                old_phone_number = user.phone_number
                try:
                    parsed_number = phonenumbers.parse(old_phone_number, settings.PHONENUMBER_DEFAULT_REGION)
                    if phonenumbers.is_valid_number(parsed_number):
                        e164_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                        if old_phone_number != e164_number:
                            user.phone_number = e164_number
                            user.save(update_fields=['phone_number'])
                            self.stdout.write(self.style.SUCCESS(f'Updated CustomUser {user.id}: {old_phone_number} -> {e164_number}'))
                            users_updated += 1
                        else:
                            self.stdout.write(self.style.MIGRATE_HEADING(f'CustomUser {user.id}: {old_phone_number} already in E.164 format.'))
                            users_skipped += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'Skipping CustomUser {user.id}: Invalid phone number {old_phone_number}'))
                        users_skipped += 1
                except phonenumbers.phonenumberutil.NumberParseException:
                    self.stdout.write(self.style.ERROR(f'Skipping CustomUser {user.id}: Could not parse phone number {old_phone_number}'))
                    users_skipped += 1
            else:
                users_skipped += 1

        self.stdout.write(self.style.SUCCESS(f'CustomUser phone numbers: {users_updated} updated, {users_skipped} skipped.'))

        # Normalize Deliverer phone numbers
        deliverers_updated = 0
        deliverers_skipped = 0
        for deliverer in Deliverer.objects.all():
            if deliverer.phone_number:
                old_phone_number = deliverer.phone_number
                try:
                    parsed_number = phonenumbers.parse(old_phone_number, settings.PHONENUMBER_DEFAULT_REGION)
                    if phonenumbers.is_valid_number(parsed_number):
                        e164_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                        if old_phone_number != e164_number:
                            deliverer.phone_number = e164_number
                            deliverer.save(update_fields=['phone_number'])
                            self.stdout.write(self.style.SUCCESS(f'Updated Deliverer {deliverer.id}: {old_phone_number} -> {e164_number}'))
                            deliverers_updated += 1
                        else:
                            self.stdout.write(self.style.MIGRATE_HEADING(f'Deliverer {deliverer.id}: {old_phone_number} already in E.164 format.'))
                            deliverers_skipped += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'Skipping Deliverer {deliverer.id}: Invalid phone number {old_phone_number}'))
                        deliverers_skipped += 1
                except phonenumbers.phonenumberutil.NumberParseException:
                    self.stdout.write(self.style.ERROR(f'Skipping Deliverer {deliverer.id}: Could not parse phone number {old_phone_number}'))
                    deliverers_skipped += 1
            else:
                deliverers_skipped += 1

        self.stdout.write(self.style.SUCCESS(f'Deliverer phone numbers: {deliverers_updated} updated, {deliverers_skipped} skipped.'))
        self.stdout.write(self.style.SUCCESS('Phone number normalization completed.'))