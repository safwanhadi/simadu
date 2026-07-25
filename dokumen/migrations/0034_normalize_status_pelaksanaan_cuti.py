from django.db import migrations, models


def normalize_status_pelaksanaan(apps, schema_editor):
    RiwayatCuti = apps.get_model('dokumen', 'RiwayatCuti')
    RiwayatCuti.objects.filter(status_cuti='Ditolak').update(status_cuti='Batal')
    RiwayatCuti.objects.filter(status_cuti='Proses').update(
        status_cuti='Berlangsung',
    )


def reverse_status_pelaksanaan(apps, schema_editor):
    RiwayatCuti = apps.get_model('dokumen', 'RiwayatCuti')
    RiwayatCuti.objects.filter(status_cuti='Belum').update(status_cuti='Proses')
    RiwayatCuti.objects.filter(status_cuti='Berlangsung').update(status_cuti='Proses')
    RiwayatCuti.objects.filter(status_cuti='Batal').update(status_cuti='Ditolak')


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0033_alter_riwayatcuti_status_cuti'),
        ('layanan', '0035_normalize_status_pengajuan_cuti'),
    ]

    operations = [
        migrations.RunPython(normalize_status_pelaksanaan, reverse_status_pelaksanaan),
        migrations.RemoveField(
            model_name='riwayatcuti',
            name='status_persetujuan',
        ),
        migrations.AlterField(
            model_name='riwayatcuti',
            name='status_cuti',
            field=models.CharField(
                choices=[
                    ('Belum', 'Belum dilaksanakan'),
                    ('Berlangsung', 'Sedang berlangsung'),
                    ('Selesai', 'Selesai'),
                    ('Tunda', 'Ditunda'),
                    ('Batal', 'Tidak dilaksanakan'),
                ],
                default='Belum',
                max_length=12,
                verbose_name='Status Pelaksanaan Cuti',
            ),
        ),
    ]
