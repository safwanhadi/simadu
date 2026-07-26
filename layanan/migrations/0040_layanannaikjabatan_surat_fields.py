from django.db import migrations, models


def fill_legacy_period(apps, schema_editor):
    LayananNaikJabatan = apps.get_model('layanan', 'LayananNaikJabatan')
    for usulan in LayananNaikJabatan.objects.filter(periode__isnull=True).iterator():
        if usulan.created_at:
            usulan.periode = usulan.created_at.date().replace(day=1)
            usulan.save(update_fields=['periode'])


class Migration(migrations.Migration):

    dependencies = [
        ('layanan', '0039_add_cuti_pemutihan_audit'),
    ]

    operations = [
        migrations.AddField(
            model_name='layanannaikjabatan',
            name='formasi_tersedia',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='layanannaikjabatan',
            name='jabatan_diusulkan',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='layanannaikjabatan',
            name='kategori_pengelolaan',
            field=models.CharField(
                choices=[
                    ('kenaikan', 'Kenaikan Jabatan'),
                    ('pengangkatan_kembali', 'Pengangkatan Kembali'),
                    ('perpindahan', 'Perpindahan dari Jabatan Lain'),
                    ('penyesuaian', 'Inpassing/Penyesuaian'),
                ],
                default='kenaikan',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='layanannaikjabatan',
            name='periode',
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text='Bulan pengusulan yang digunakan untuk surat kolektif.',
                null=True,
            ),
        ),
        migrations.RunPython(fill_legacy_period, migrations.RunPython.noop),
    ]
