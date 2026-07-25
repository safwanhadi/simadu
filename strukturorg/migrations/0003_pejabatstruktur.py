import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


STRUCTURE_MODELS = (
    ('InstansiDaerah', 'instansi_daerah'),
    ('SatuanKerjaInduk', 'satuan_kerja_induk'),
    ('UnitOrganisasi', 'unit_organisasi'),
    ('Bidang', 'bidang'),
    ('SubBidang', 'sub_bidang'),
    ('UnitInstalasi', 'unit_instalasi'),
)


def copy_current_officials(apps, schema_editor):
    PejabatStruktur = apps.get_model('strukturorg', 'PejabatStruktur')
    today = datetime.date.today()
    rows = []
    for model_name, field_name in STRUCTURE_MODELS:
        Structure = apps.get_model('strukturorg', model_name)
        for structure in Structure.objects.exclude(nama_pimpinan_id=None).iterator():
            rows.append(PejabatStruktur(
                **{f'{field_name}_id': structure.pk},
                pejabat_id=structure.nama_pimpinan_id,
                nama_jabatan=structure.pimpinan,
                tanggal_mulai=today,
                is_active=True,
                active_slot=True,
            ))
    PejabatStruktur.objects.bulk_create(rows)


def restore_legacy_only(apps, schema_editor):
    apps.get_model('strukturorg', 'PejabatStruktur').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('strukturorg', '0002_standarinstalasi_kompetensi_wajib_parsial_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PejabatStruktur',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_jabatan', models.CharField(blank=True, max_length=100)),
                ('tanggal_mulai', models.DateField(default=datetime.date.today)),
                ('tanggal_selesai', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('active_slot', models.BooleanField(editable=False, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bidang', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='riwayat_pejabat', to='strukturorg.bidang')),
                ('instansi_daerah', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='riwayat_pejabat', to='strukturorg.instansidaerah')),
                ('pejabat', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='riwayat_jabatan_struktur', to=settings.AUTH_USER_MODEL)),
                ('satuan_kerja_induk', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='riwayat_pejabat', to='strukturorg.satuankerjainduk')),
                ('sub_bidang', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='riwayat_pejabat', to='strukturorg.subbidang')),
                ('unit_instalasi', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='riwayat_pejabat', to='strukturorg.unitinstalasi')),
                ('unit_organisasi', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='riwayat_pejabat', to='strukturorg.unitorganisasi')),
            ],
            options={
                'verbose_name': 'Riwayat pejabat struktur',
                'verbose_name_plural': 'Riwayat pejabat struktur',
                'ordering': ('-is_active', '-tanggal_mulai', '-id'),
            },
        ),
        migrations.AddConstraint(
            model_name='pejabatstruktur',
            constraint=models.UniqueConstraint(fields=('instansi_daerah', 'active_slot'), name='uniq_pejabat_aktif_instansi'),
        ),
        migrations.AddConstraint(
            model_name='pejabatstruktur',
            constraint=models.UniqueConstraint(fields=('satuan_kerja_induk', 'active_slot'), name='uniq_pejabat_aktif_satker'),
        ),
        migrations.AddConstraint(
            model_name='pejabatstruktur',
            constraint=models.UniqueConstraint(fields=('unit_organisasi', 'active_slot'), name='uniq_pejabat_aktif_unor'),
        ),
        migrations.AddConstraint(
            model_name='pejabatstruktur',
            constraint=models.UniqueConstraint(fields=('bidang', 'active_slot'), name='uniq_pejabat_aktif_bidang'),
        ),
        migrations.AddConstraint(
            model_name='pejabatstruktur',
            constraint=models.UniqueConstraint(fields=('sub_bidang', 'active_slot'), name='uniq_pejabat_aktif_subbidang'),
        ),
        migrations.AddConstraint(
            model_name='pejabatstruktur',
            constraint=models.UniqueConstraint(fields=('unit_instalasi', 'active_slot'), name='uniq_pejabat_aktif_instalasi'),
        ),
        migrations.RunPython(copy_current_officials, restore_legacy_only),
    ]
