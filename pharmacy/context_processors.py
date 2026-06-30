import os
from django.conf import settings

def social_links(request):
    return {
        'SOCIAL_LINKS': [
            {
                'name': 'Telegram',
                'url': os.getenv('SOCIAL_TELEGRAM_URL', 'https://t.me/firdavsy2011'),
                'icon': os.getenv('SOCIAL_TELEGRAM_ICON', '/static/images/icons/telegram.png')
            },
            {
                'name': 'Instagram',
                'url': os.getenv('SOCIAL_INSTAGRAM_URL', 'https://instagram.com/'),
                'icon': os.getenv('SOCIAL_INSTAGRAM_ICON', '/static/images/icons/instagram.png')
            },
            {
                'name': 'Facebook',
                'url': os.getenv('SOCIAL_FACEBOOK_URL', 'https://facebook.com/'),
                'icon': os.getenv('SOCIAL_FACEBOOK_ICON', '/static/images/icons/facebook.png')
            },
        ],
        'SOCIAL_TELEGRAM': os.getenv('SOCIAL_TELEGRAM_URL', 'https://t.me/firdavsy2011'),
        'SOCIAL_INSTAGRAM': os.getenv('SOCIAL_INSTAGRAM_URL', 'https://instagram.com/'),
        'SOCIAL_FACEBOOK': os.getenv('SOCIAL_FACEBOOK_URL', 'https://facebook.com/'),
    }

def footer_links(request):
    return {
        'FOOTER_LINKS': [
            {
                'group': 'Sayt',
                'links': [
                    {'title': 'Bosh sahifa', 'url': '/'},
                    {'title': 'Shop', 'url': '/shop/'},
                    {'title': 'Mahsulotlar', 'url': '/shop/'},
                ]
            },
            {
                'group': 'Kompaniya',
                'links': [
                    {'title': 'Biz haqimizda', 'url': '/about/'},
                    {'title': 'Aloqa', 'url': '/contact/'},
                    {'title': 'Vakansiyalar', 'url': '/about/'},
                ]
            },
            {
                'group': 'Yordam',
                'links': [
                    {'title': 'Maxfiylik siyosati', 'url': '/privacy/'},
                    {'title': 'Foydalanish shartlari', 'url': '/terms/'},
                    {'title': 'FAQ', 'url': '/about/'},
                ]
            },
        ]
    }