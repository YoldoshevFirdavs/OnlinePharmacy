from django.db import migrations

def create_default_site_configuration(apps, schema_editor):
    SiteConfiguration = apps.get_model('pharmacy', 'SiteConfiguration')
    # get_or_create to prevent error if it already exists
    SiteConfiguration.objects.get_or_create(
        pk=1,
        defaults={
            'about_us_text': 'Bizning aptekamiz 2026-yildan beri sizning xizmatingizda. Bizning maqsadimiz - aholiga sifatli va arzon dori-darmonlarni yetkazib berish.',
            'clients_count': 1000,
            'experience_years': 1
        }
    )

class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0009_site_configuration_data'),
    ]

    operations = [
        migrations.RunPython(create_default_site_configuration),
    ]
