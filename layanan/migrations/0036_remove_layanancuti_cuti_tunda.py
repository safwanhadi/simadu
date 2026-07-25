from django.db import migrations, models


def submit_legacy_drafts(apps, schema_editor):
    LayananCuti = apps.get_model('layanan', 'LayananCuti')
    LayananCuti.objects.filter(status='draft').update(status='pengajuan')


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0034_normalize_status_pelaksanaan_cuti'),
        ('layanan', '0035_normalize_status_pengajuan_cuti'),
    ]

    operations = [
        migrations.RunPython(submit_legacy_drafts, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='layanancuti',
            name='cuti_tunda',
        ),
        migrations.AlterField(
            model_name='layanancuti',
            name='status',
            field=models.CharField(
                choices=[
                    ('pengajuan', 'Diajukan'),
                    ('tindaklanjut', 'Sedang diverifikasi'),
                    ('disetujui', 'Disetujui'),
                    ('ditolak', 'Ditolak'),
                ],
                default='pengajuan',
                max_length=20,
                verbose_name='Status Pengajuan Cuti',
            ),
        ),
    ]
