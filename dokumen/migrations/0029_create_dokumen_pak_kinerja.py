from django.db import migrations


DOCUMENTS = (
    ('pak', 'Penetapan Angka Kredit (PAK)', 'fa-chart-line'),
    ('kinerja', 'Kinerja', 'fa-chart-bar'),
)


def create_documents(apps, schema_editor):
    DokumenSDM = apps.get_model('dokumen', 'DokumenSDM')
    for url, nama, icon in DOCUMENTS:
        DokumenSDM.objects.update_or_create(
            url=url,
            defaults={'nama': nama, 'icon': icon, 'view': True},
        )


def delete_documents(apps, schema_editor):
    DokumenSDM = apps.get_model('dokumen', 'DokumenSDM')
    DokumenSDM.objects.filter(url__in=[item[0] for item in DOCUMENTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0028_create_dokumen_uji_kompetensi'),
    ]

    operations = [
        migrations.RunPython(create_documents, delete_documents),
    ]
