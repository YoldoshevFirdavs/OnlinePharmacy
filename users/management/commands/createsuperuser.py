from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError


class Command(createsuperuser.Command):
    help = "Used to create a superuser with email as the USERNAME_FIELD."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove phone_number from required fields if it was there
        if "phone_number" in self.UserModel.REQUIRED_FIELDS:
            self.UserModel.REQUIRED_FIELDS.remove("phone_number")
        # Add email to required fields if it's not the USERNAME_FIELD
        if self.UserModel.USERNAME_FIELD != "email" and "email" not in self.UserModel.REQUIRED_FIELDS:
            self.UserModel.REQUIRED_FIELDS.append("email")

    def handle(self, *args, **options):
        # Ensure email is prompted as the username field
        self.username_field = self.UserModel._meta.get_field(self.UserModel.USERNAME_FIELD)

        # Temporarily set REQUIRED_FIELDS to ensure email is asked
        original_required_fields = self.UserModel.REQUIRED_FIELDS
        self.UserModel.REQUIRED_FIELDS = [self.UserModel.USERNAME_FIELD]  # Make email required for this command

        super().handle(*args, **options)

        # Restore original REQUIRED_FIELDS
        self.UserModel.REQUIRED_FIELDS = original_required_fields

    def get_input_data(self, field, message, default=None):
        # Override to handle email as the primary input for superuser creation
        if field.name == self.UserModel.USERNAME_FIELD:  # This will be 'email' now
            input_value = None
            while input_value is None:
                input_value = self.get_field_input(field, message, default)
                if not input_value:
                    self.stderr.write(self.style.ERROR(f"{field.verbose_name} bo'sh bo'lishi mumkin emas."))
                    input_value = None  # Ask again
            return input_value
        elif field.name == "phone_number":  # Make phone_number optional
            return self.get_field_input(field, message, default)
        return super().get_input_data(field, message, default)
