from django.core.management.base import BaseCommand
from django.utils.text import slugify

from pharmacy.models.medicine import Category


class Command(BaseCommand):
    help = "Seeds the database with initial categories."

    def handle(self, *args, **options):
        categories = [
            "Ukol",
            "Balzam",
            "Qo'lqop",
            "Mebel",
            "Elektronika",
            "Kiyim",
            "Poyabzal",
            "Go'zallik",
            "Salomatlik",
            "Oziq-ovqat",
        ]

        self.stdout.write(self.style.SUCCESS("Seeding categories..."))

        for cat_name in categories:
            slug = slugify(cat_name)
            category, created = Category.objects.get_or_create(
                name=cat_name, defaults={"slug": slug, "is_default": True}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Successfully added category: {cat_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Category already exists: {cat_name}"))

        self.stdout.write(self.style.SUCCESS("Category seeding complete."))
