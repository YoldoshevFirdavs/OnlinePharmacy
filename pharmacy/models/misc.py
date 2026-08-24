from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .medicine import Medicine


class SiteConfiguration(models.Model):
    about_us_text = models.TextField(verbose_name="Biz haqimizda matni")
    clients_count = models.PositiveIntegerField(default=0, verbose_name="Mijozlar soni")
    experience_years = models.PositiveIntegerField(default=0, verbose_name="Tajriba yillari")

    def __str__(self):
        return "Sayt Konfiguratsiyasi"

    class Meta:
        verbose_name = "Sayt Konfiguratsiyasi"
        verbose_name_plural = "Sayt Konfiguratsiyasi"

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SiteConfiguration, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class ReviewApprovedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(Q(is_ai_checked=True) & Q(is_approved=True))


class Review(models.Model):
    user = models.ForeignKey("users.CustomUser", on_delete=models.CASCADE, related_name="reviews")
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 dan 5 gacha baho bering",
    )
    content = models.TextField(verbose_name="Fikr-mulohaza")
    date_posted = models.DateTimeField(auto_now_add=True)

    is_approved = models.BooleanField(default=True)
    is_ai_checked = models.BooleanField(default=False)

    objects = models.Manager()
    approved = ReviewApprovedManager()

    class Meta:
        ordering = ["-date_posted"]

    def __str__(self):
        return f"{self.user.full_name or self.user.phone_number} - {self.medicine.name} ({self.rating} ⭐)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        count = Review.objects.filter(is_ai_checked=False).count()

        if count > 0 and count % 10 == 0:
            from ..tasks import moderate_reviews_task

            moderate_reviews_task.delay()


class FlashSale(models.Model):
    product = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    discount_percentage = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def is_active(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    class Meta:
        unique_together = ("product", "start_time", "end_time")


class ProductViewHistory(models.Model):
    user = models.ForeignKey("users.CustomUser", on_delete=models.CASCADE)
    product = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)


class MedicineImage(models.Model):
    medicine = models.ForeignKey(Medicine, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="medicines/gallery/")
    is_primary = models.BooleanField(default=False)


class StockLog(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    user = models.ForeignKey("users.CustomUser", on_delete=models.SET_NULL, null=True)
    change_amount = models.IntegerField()
    reason = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)


class BotMenuStep(models.Model):
    status_key = models.CharField(max_length=100, unique=True, db_index=True)
    text_uz = models.TextField(verbose_name="Matn (UZ)")
    text_ru = models.TextField(verbose_name="Matn (RU)", blank=True, null=True)
    text_eng = models.TextField(verbose_name="Matn (EN)", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Step: {self.status_key}"


class BotInlineButton(models.Model):
    menu_step = models.ForeignKey(BotMenuStep, on_delete=models.CASCADE, related_name="buttons")
    title_uz = models.CharField(max_length=255, verbose_name="Tugma nomi (UZ)")
    title_ru = models.CharField(max_length=255, verbose_name="Tugma nomi (RU)", blank=True, null=True)
    title_eng = models.CharField(max_length=255, verbose_name="Tugma nomi (EN)", blank=True, null=True)
    callback_id = models.IntegerField()
    row_number = models.PositiveIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["row_number", "sort_order"]

    def __str__(self):
        return f"Button: {self.title_uz} -> Callback ID: {self.callback_id}"
