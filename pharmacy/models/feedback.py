from django.db import models

class Feedback(models.Model):
    SUBJECT_CHOICES = [
        ('order', 'Buyurtma haqida'),
        ('product', 'Mahsulot haqida'),
        ('complaint', 'Shikoyat'),
        ('suggestion', 'Taklif'),
        ('other', 'Boshqa'),
    ]

    full_name = models.CharField(max_length=255, verbose_name="Foydalanuvchi ismi")
    phone_number = models.CharField(max_length=20, verbose_name="Telefon raqami")
    email = models.EmailField(blank=True, null=True, verbose_name="Email manzili")
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, default='other', verbose_name="Mavzu")
    message = models.TextField(verbose_name="Xabar matni")
    
    is_replied = models.BooleanField(default=False, verbose_name="Javob berildi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuborilgan vaqt")

    class Meta:
        verbose_name = "Fikr-mulohaza"
        verbose_name_plural = "Fikr-mulohazalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.get_subject_display()}"
