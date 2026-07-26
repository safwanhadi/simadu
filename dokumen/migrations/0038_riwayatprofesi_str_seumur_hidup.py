from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0037_riwayatprofesi_berlaku_sd_str'),
    ]

    operations = [
        migrations.AddField(
            model_name='riwayatprofesi',
            name='str_seumur_hidup',
            field=models.BooleanField(
                default=False,
                verbose_name='STR berlaku seumur hidup',
            ),
        ),
    ]
