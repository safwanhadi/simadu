from django.db import migrations


STATUS_CUTI_LAMA_KE_BARU = {
    'Belum': 'Belum',
    'Selesai': 'Selesai',
    'Tunda': 'Tunda',
    'Proses': 'Berlangsung',
}


def map_status_cuti_lama(apps, schema_editor):
    RiwayatCuti = apps.get_model('dokumen', 'RiwayatCuti')
    for status_lama, status_baru in STATUS_CUTI_LAMA_KE_BARU.items():
        if status_lama != status_baru:
            RiwayatCuti.objects.filter(status_cuti=status_lama).update(
                status_cuti=status_baru,
            )


def kembalikan_status_cuti_lama(apps, schema_editor):
    RiwayatCuti = apps.get_model('dokumen', 'RiwayatCuti')
    RiwayatCuti.objects.filter(status_cuti='Berlangsung').update(
        status_cuti='Proses',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0034_normalize_status_pelaksanaan_cuti'),
    ]

    operations = [
        migrations.RunPython(
            map_status_cuti_lama,
            kembalikan_status_cuti_lama,
        ),
    ]
