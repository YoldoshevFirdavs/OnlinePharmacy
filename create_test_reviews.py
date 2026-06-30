import os
import django
import random

# Django muhitini sozlash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pharmacy.models.medicine import Medicine, Category
from pharmacy.models.misc import Review
from users.models import CustomUser

# Ranglar uchun (faqat terminalda chiroyli ko'rinishi uchun)
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"

def create_dummy_reviews(num_reviews=20):
    print(f"\n{BOLD}{CYAN}--- TESTNI TAYYORLASH BOSHLANDI ---{RESET}")
    
    # 1. Tozalash
    Review.objects.all().delete()
    print("🗑️ Eski sharhlar o'chirildi.")

    # 2. Test foydalanuvchisi
    test_phone = "+998901234567"
    user, _ = CustomUser.objects.get_or_create(
        phone_number=test_phone,
        defaults={'full_name': "Test User"}
    )
    user.bad_comments_count = 0
    user.save()

    # 3. Test dorisi va kategoriyasi
    category, _ = Category.objects.get_or_create(name="Test Category", defaults={'slug': 'test-cat'})
    medicine = Medicine.objects.first()
    if not medicine:
        medicine = Medicine.objects.create(
            name='Test Medicine', 
            slug='test-med', 
            category=category, 
            price=1000, 
            stock=100, 
            short_description='Test', 
            instruction='Test'
        )

    # 🛠️ Test ma'lumotlari
    bad_contents = [
        "Bu dorini har 4 soatda 2 tabletkadan iching, tez tuzalasiz.",
        "Menga shifokor kuniga 3 mahal 500mg dan ichishni buyurdi.",
        "Homilador bo'lsangiz, dozani ikki baravar kamaytiring.",
        "Bu dorini analgin bilan aralashtirib iching, zo'r yordam beradi.",
        "Bolalarga 1/4 qismini bering, men o'z o'g'limga shunday qildim."
    ]
    
    good_contents = [
        "Juda yaxshi dori ekan, rahmat!",
        "Yetkazib berish juda tez bo'ldi.",
        "Dorixona xodimlariga kattakon rahmat.",
        "Qadoqlanishi juda xavfsiz ekan, menga yoqdi.",
        "Sifati a'lo, narxi ham hamyonbop."
    ]

    print(f"\n{BOLD}Yaratilayotgan sharhlar:{RESET}")

    for i in range(num_reviews):
        # 50% ehtimol bilan yomon yoki yaxshi sharh
        is_bad = random.choice([True, False])
        content = random.choice(bad_contents if is_bad else good_contents)
        color = RED if is_bad else GREEN
        label = "YOMON" if is_bad else "YAXSHI"

        Review.objects.create(
            user=user,
            medicine=medicine,
            rating=random.randint(4, 5),
            content=content
        )
        
        print(f" {i+1}. {color}[{label}]{RESET} {content[:60]}...")

    print(f"\n{GREEN}{BOLD}✅ Jami {num_reviews} ta sharh yaratildi!{RESET}")
    print(f"{CYAN}Endi Celery worker terminalini kuzating.{RESET}\n")

if __name__ == '__main__':
    create_dummy_reviews(20)
