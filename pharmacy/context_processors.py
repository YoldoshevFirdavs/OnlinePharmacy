import os

from .models.misc import SiteConfiguration


def site_configuration(request):
    config = SiteConfiguration.objects.first()
    if not config:
        config = {
            "about_us_text": "Bizning aptekamiz 2026-yildan beri sizning xizmatingizda. Bizning maqsadimiz - aholiga sifatli va arzon dori-darmonlarni yetkazib berish.",
            "clients_count": 1000,
            "experience_years": 1,
        }

    # Add dynamic URLs from environment
    site_url = os.getenv("SITE_URL", "http://localhost:8000")
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    return {
        "site_config": config,
        "SITE_URL": site_url,
        "API_BASE_URL": api_base_url,
    }


def social_links(request):
    """Social media links for templates"""
    return {
        "social_telegram": "https://t.me/onlinepharmacy_uz",
        "social_instagram": "https://instagram.com/onlinepharmacy_uz",
        "social_facebook": "https://facebook.com/onlinepharmacy_uz",
    }


def footer_links(request):
    """Footer navigation links for templates"""
    return {
        "about_url": "/about/",
        "contact_url": "/contact/",
        "terms_url": "/terms/",
        "privacy_url": "/privacy/",
    }
