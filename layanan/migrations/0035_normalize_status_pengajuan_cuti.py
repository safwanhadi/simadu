from django.db import migrations, models


def normalize_status_pengajuan(apps, schema_editor):
    LayananCuti = apps.get_model('layanan', 'LayananCuti')
    RiwayatCuti = apps.get_model('dokumen', 'RiwayatCuti')

    for layanan in LayananCuti.objects.all().iterator():
        riwayat = RiwayatCuti.objects.filter(usulan_id=layanan.pk).first()
        status_persetujuan = getattr(riwayat, 'status_persetujuan', None)

        if status_persetujuan == 'disetujui':
            status_baru = 'disetujui'
        elif status_persetujuan == 'ditolak':
            status_baru = 'ditolak'
        elif layanan.status == 'selesai':
            status_baru = 'disetujui'
        elif layanan.status == 'tidak ditindaklanjut':
            status_baru = 'ditolak'
        elif layanan.status in ('draft', 'pengajuan', 'tindaklanjut'):
            status_baru = layanan.status
        else:
            status_baru = 'pengajuan'

        if layanan.status != status_baru:
            layanan.status = status_baru
            layanan.save(update_fields=('status',))


def reverse_status_pengajuan(apps, schema_editor):
    LayananCuti = apps.get_model('layanan', 'LayananCuti')
    LayananCuti.objects.filter(status='disetujui').update(status='selesai')
    LayananCuti.objects.filter(status='ditolak').update(status='tidak ditindaklanjut')


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0033_alter_riwayatcuti_status_cuti'),
        ('layanan', '0034_perubahanjadwalcuti'),
    ]

    operations = [
        migrations.RunPython(normalize_status_pengajuan, reverse_status_pengajuan),
        migrations.AlterField(
            model_name='layanancuti',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('pengajuan', 'Diajukan'),
                    ('tindaklanjut', 'Sedang diverifikasi'),
                    ('disetujui', 'Disetujui'),
                    ('ditolak', 'Ditolak'),
                ],
                default='draft',
                max_length=20,
                verbose_name='Status Pengajuan Cuti',
            ),
        ),
    ]
