from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0036_remove_legacy_cuti_tertunda'),
    ]

    operations = [
        migrations.AddField(
            model_name='riwayatprofesi',
            name='berlaku_sd_str',
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name='STR berlaku s/d',
            ),
        ),
    ]
