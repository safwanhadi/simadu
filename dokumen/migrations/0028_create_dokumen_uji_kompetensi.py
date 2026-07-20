from django.db import migrations


def create_dokumen(apps, schema_editor):
    DokumenSDM = apps.get_model('dokumen', 'DokumenSDM')
    DokumenSDM.objects.update_or_create(
        url='ujikomp',
        defaults={
            'nama': 'Uji Kompetensi',
            'icon': 'fa-certificate',
            'view': True,
        },
    )


def delete_dokumen(apps, schema_editor):
    DokumenSDM = apps.get_model('dokumen', 'DokumenSDM')
    DokumenSDM.objects.filter(url='ujikomp').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0027_riwayatjabatan_usulan_riwayatpanggol_usulan'),
    ]

    operations = [
        migrations.RunPython(create_dokumen, delete_dokumen),
    ]
