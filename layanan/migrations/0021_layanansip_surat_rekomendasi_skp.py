from django.db import migrations, models
import layanan.models


class Migration(migrations.Migration):
    dependencies = [
        ("layanan", "0020_delete_pengajuansip"),
    ]

    operations = [
        migrations.AddField(
            model_name="layanansip",
            name="surat_rekomendasi_skp",
            field=models.FileField(
                blank=True,
                help_text="Ukuran maksimal file 2.5MB",
                upload_to="layanan/sip/rekomendasi_skp/",
                validators=[layanan.models.validate_file_size],
                verbose_name="Surat Rekomendasi SKP yang Ditandatangani Pimpinan",
            ),
        ),
    ]
