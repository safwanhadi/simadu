from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0038_riwayatprofesi_str_seumur_hidup'),
    ]

    operations = [
        migrations.AddField(
            model_name='riwayatcuti',
            name='menggunakan_pola_shift',
            field=models.BooleanField(blank=True, help_text='Snapshot pola kerja ketika cuti diajukan; kosong untuk data lama.', null=True),
        ),
    ]
