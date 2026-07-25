from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layanan', '0037_add_selesai_status_pengajuan_cuti'),
    ]

    operations = [
        migrations.AddField(
            model_name='layanancuti',
            name='snapshot_saldo_cuti',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Saldo cuti pada saat pengajuan disimpan.',
                verbose_name='Snapshot Saldo Cuti',
            ),
        ),
    ]
