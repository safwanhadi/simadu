from django.db import migrations, models


FORWARD_MAPPING = {
    'Diatas Ekspektasi': 'diatas',
    'Sesuai Ekspektasi': 'sesuai',
    'Dibawah Ekspektasi': 'dibawah',
}
REVERSE_MAPPING = {value: key for key, value in FORWARD_MAPPING.items()}


def normalize_values(apps, schema_editor):
    RiwayatKinerja = apps.get_model('dokumen', 'RiwayatKinerja')
    for old_value, new_value in FORWARD_MAPPING.items():
        RiwayatKinerja.objects.filter(hasil_kinerja=old_value).update(hasil_kinerja=new_value)
        RiwayatKinerja.objects.filter(prilaku_kinerja=old_value).update(prilaku_kinerja=new_value)


def restore_values(apps, schema_editor):
    RiwayatKinerja = apps.get_model('dokumen', 'RiwayatKinerja')
    for new_value, old_value in REVERSE_MAPPING.items():
        RiwayatKinerja.objects.filter(hasil_kinerja=new_value).update(hasil_kinerja=old_value)
        RiwayatKinerja.objects.filter(prilaku_kinerja=new_value).update(prilaku_kinerja=old_value)


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0029_create_dokumen_pak_kinerja'),
    ]

    operations = [
        migrations.RunPython(normalize_values, restore_values),
        migrations.AlterField(
            model_name='riwayatkinerja',
            name='hasil_kinerja',
            field=models.CharField(
                blank=True,
                choices=[
                    ('diatas', 'Diatas Ekspektasi'),
                    ('sesuai', 'Sesuai Ekspektasi'),
                    ('dibawah', 'Dibawah Ekspektasi'),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name='riwayatkinerja',
            name='prilaku_kinerja',
            field=models.CharField(
                blank=True,
                choices=[
                    ('diatas', 'Diatas Ekspektasi'),
                    ('sesuai', 'Sesuai Ekspektasi'),
                    ('dibawah', 'Dibawah Ekspektasi'),
                ],
                max_length=30,
            ),
        ),
    ]
