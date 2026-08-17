# scripts/seed_medicines.py
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from faker import Faker

# Disconnect signals before seed to prevent AuditLog entries
from django.db.models.signals import post_save, post_delete

# Store original signal receivers
_original_medicine_save = None
_original_medicine_delete = None
_original_category_save = None
_original_category_delete = None


def disconnect_signals():
    """Disconnect AuditLog signals before seed."""
    global _original_medicine_save, _original_medicine_delete, _original_category_save, _original_category_delete

    from pharmacy.signals import log_medicine_save, log_medicine_delete, log_category_save, log_category_delete
    from pharmacy.models import Medicine, Category

    _original_medicine_save = post_save.disconnect(sender=Medicine, dispatch_uid="log_medicine_save", receiver=log_medicine_save)
    _original_medicine_delete = post_delete.disconnect(sender=Medicine, dispatch_uid="log_medicine_delete", receiver=log_medicine_delete)
    _original_category_save = post_save.disconnect(sender=Category, dispatch_uid="log_category_save", receiver=log_category_save)
    _original_category_delete = post_delete.disconnect(sender=Category, dispatch_uid="log_category_delete", receiver=log_category_delete)


def reconnect_signals():
    """Reconnect AuditLog signals after seed."""
    from pharmacy.signals import log_medicine_save, log_medicine_delete, log_category_save, log_category_delete
    from pharmacy.models import Medicine, Category

    if _original_medicine_save is not False:
        post_save.connect(log_medicine_save, sender=Medicine, dispatch_uid="log_medicine_save")
    if _original_medicine_delete is not False:
        post_delete.connect(log_medicine_delete, sender=Medicine, dispatch_uid="log_medicine_delete")
    if _original_category_save is not False:
        post_save.connect(log_category_save, sender=Category, dispatch_uid="log_category_save")
    if _original_category_delete is not False:
        post_delete.connect(log_category_delete, sender=Category, dispatch_uid="log_category_delete")


faker = Faker()


def run(*args):
    """
    Usage:
      python manage.py runscript seed_medicines --script-args 20 30
    Default: 20 categories, 30 products per category
    """
    # Disconnect signals before seed
    disconnect_signals()

    try:
        num_categories = 20
        products_per_category = 30

        if args and len(args) >= 2:
            try:
                num_categories = int(args[0])
                products_per_category = int(args[1])
            except Exception:
                pass

        # Import models inside run() to avoid issues
        from pharmacy.models import Category, Medicine

        created_categories = []
        created_products = 0

        with transaction.atomic():
            # Create categories
            for i in range(num_categories):
                name = faker.unique.company()
                slug = faker.unique.slug()
                category = Category.objects.create(name=name, slug=slug)
                created_categories.append(category)

            print(f"Created {len(created_categories)} categories")

            # Create products for each category using bulk_create
            medicines_to_create = []
            for category in created_categories:
                for _ in range(products_per_category):
                    name = faker.unique.word().title() + ' ' + faker.word().title()
                    slug = faker.unique.slug()
                    price = round(faker.pyfloat(left_digits=3, right_digits=2, positive=True), 2)
                    stock = faker.random_int(min=0, max=500)
                    avg_rating = round(faker.pyfloat(left_digits=1, right_digits=2, min_value=0, max_value=5), 2)
                    reviews_count = faker.random_int(min=0, max=500)
                    short_desc = faker.sentence(nb_words=10)
                    instruction = faker.sentence(nb_words=12)
                    side_effects = faker.sentence(nb_words=8)
                    contraindications = faker.sentence(nb_words=8)
                    storage_conditions = faker.sentence(nb_words=6)
                    is_prescription_required = faker.boolean(chance_of_getting_true=20)
                    is_active = True
                    updated_at = timezone.now()

                    medicine = Medicine(
                        name=name,
                        slug=slug,
                        category=category,
                        average_rating=Decimal(str(avg_rating)),
                        reviews_count=reviews_count,
                        price=Decimal(str(price)),
                        stock=stock,
                        is_active=is_active,
                        short_description=short_desc,
                        instruction=instruction,
                        side_effects=side_effects,
                        contraindications=contraindications,
                        storage_conditions=storage_conditions,
                        is_prescription_required=is_prescription_required,
                        main_image=None,
                        updated_at=updated_at,
                    )
                    medicines_to_create.append(medicine)

            # Use bulk_create to avoid post_save signals
            if medicines_to_create:
                Medicine.objects.bulk_create(medicines_to_create, batch_size=100)
                created_products = len(medicines_to_create)

            print(f"Created {created_products} medicines")

        print(f"Seed finished: created {len(created_categories)} categories, {created_products} products")

    finally:
        # Reconnect signals after seed
        reconnect_signals()
