from django.db import models
from django.db.models import Q

class MedicineManager(models.Manager):
    def search(self, query):
        return self.filter(
            Q(name__icontains=query) | Q(short_description__icontains=query)
        ).distinct()

class MedicineAvailableManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True, stock__gt=0)
    
    def search(self, query):
        return self.get_queryset().filter(
            Q(name__icontains=query) | Q(short_description__icontains=query)
        ).distinct()

class Medicine(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(unique=True, db_index=True)
    category = models.ForeignKey('Category', on_delete=models.PROTECT, related_name='medicines')

    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    reviews_count = models.PositiveIntegerField(default=0)

    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    seller = models.ForeignKey('users.Seller', on_delete=models.CASCADE, related_name='seller', null=True, blank=True)

    short_description = models.CharField(max_length=500)
    instruction = models.TextField()
    side_effects = models.TextField(blank=True)
    contraindications = models.TextField(blank=True)
    storage_conditions = models.CharField(max_length=255, blank=True)
    is_prescription_required = models.BooleanField(default=False)
    main_image = models.ImageField(upload_to='medicines/main/', null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    
    objects = MedicineManager()
    available = MedicineAvailableManager()

    def __str__(self):
        return self.name

    def reduce_stock(self, quantity):
        if quantity <= self.stock:
            self.stock -= quantity
            self.save()
            return True
        return False

class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name