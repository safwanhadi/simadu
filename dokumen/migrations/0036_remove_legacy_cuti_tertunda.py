from django.db import migrations, models


def map_cuti_tertunda_ke_tahunan(apps, schema_editor):
    RiwayatCuti = apps.get_model('dokumen', 'RiwayatCuti')
    RiwayatCuti.objects.filter(jenis_cuti='Cuti Tertunda').update(
        jenis_cuti='Cuti Tahunan',
    )


def reverse_map_cuti_tertunda(apps, schema_editor):
    # Tidak mungkin membedakan cuti tahunan asli dengan data hasil migrasi
    # tanpa menambah penanda baru. Reverse sengaja tidak mengubah data.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0035_map_legacy_status_cuti'),
    ]

    operations = [
        migrations.RunPython(
            map_cuti_tertunda_ke_tahunan,
            reverse_map_cuti_tertunda,
        ),
        migrations.AlterField(
            model_name='riwayatcuti',
            name='jenis_cuti',
            field=models.CharField(
                choices=[
                    ('Cuti Tahunan', 'Cuti Tahunan'),
                    ('Cuti Alasan Penting', 'Cuti Alasan Penting'),
                    ('Cuti melahirkan', 'Cuti Melahirkan'),
                    ('Cuti Sakit', 'Cuti Sakit'),
                    ('Cuti Besar', 'Cuti Besar'),
                    (
                        'Cuti Diluar Tanggungan Negara',
                        'Cuti Diluar Tanggungan Negara',
                    ),
                ],
                max_length=50,
            ),
        ),
    ]
