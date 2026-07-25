from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layanan', '0036_remove_layanancuti_cuti_tunda'),
    ]

    operations = [
        migrations.AlterField(
            model_name='layanancuti',
            name='status',
            field=models.CharField(
                choices=[
                    ('pengajuan', 'Diajukan'),
                    ('tindaklanjut', 'Sedang diverifikasi'),
                    ('disetujui', 'Disetujui'),
                    ('selesai', 'Selesai'),
                    ('ditolak', 'Ditolak'),
                ],
                default='pengajuan',
                max_length=20,
                verbose_name='Status Pengajuan Cuti',
            ),
        ),
    ]
