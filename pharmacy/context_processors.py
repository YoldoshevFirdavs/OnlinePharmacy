from .models.misc import SiteConfiguration

def site_configuration(request):
    config = SiteConfiguration.objects.first()
    if not config:
        config = {
            'about_us_text': 'Bizning aptekamiz 2026-yildan beri sizning xizmatingizda. Bizning maqsadimiz - aholiga sifatli va arzon dori-darmonlarni yetkazib berish.',
            'clients_count': 1000,
            'experience_years': 1,
        }
    return {
        'site_config': config
    }