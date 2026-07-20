from django.db import migrations, models
import django.db.models.deletion


STATUS_PEGAWAI = ('Magang', 'Kontrak', 'Mitra', 'PPPK', 'CPNS', 'PNS')


def create_initial_requirements(apps, schema_editor):
    DokumenSDM = apps.get_model('dokumen', 'DokumenSDM')
    KewajibanDokumen = apps.get_model('dokumen', 'KewajibanDokumen')
    requirements = []
    for document in DokumenSDM.objects.all().iterator():
        statuses = ('PNS',) if document.url == 'panggol' else STATUS_PEGAWAI
        requirements.extend(
            KewajibanDokumen(
                dokumen_id=document.pk,
                status_pegawai=status,
            )
            for status in statuses
        )
    KewajibanDokumen.objects.bulk_create(requirements, ignore_conflicts=True)


def remove_initial_requirements(apps, schema_editor):
    apps.get_model('dokumen', 'KewajibanDokumen').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0030_normalize_riwayat_kinerja_choices'),
    ]

    operations = [
        migrations.CreateModel(
            name='KewajibanDokumen',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'status_pegawai',
                    models.CharField(
                        choices=[
                            ('Magang', 'Magang'),
                            ('Kontrak', 'Kontrak'),
                            ('Mitra', 'Mitra'),
                            ('PPPK', 'PPPK'),
                            ('CPNS', 'CPNS'),
                            ('PNS', 'PNS'),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    'dokumen',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='kewajiban_status',
                        to='dokumen.dokumensdm',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Kewajiban Dokumen',
                'verbose_name_plural': 'Kewajiban Dokumen',
                'ordering': ('dokumen__nama', 'status_pegawai'),
            },
        ),
        migrations.AddConstraint(
            model_name='kewajibandokumen',
            constraint=models.UniqueConstraint(
                fields=('dokumen', 'status_pegawai'),
                name='unique_kewajiban_dokumen_status',
            ),
        ),
        migrations.RunPython(
            create_initial_requirements,
            remove_initial_requirements,
        ),
    ]
