from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disiplinsdm', '0027_alter_absensiharian_status_final'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PolaKerjaPegawai',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pola_kerja', models.CharField(choices=[('reguler', 'Reguler'), ('shift', 'Shift')], max_length=10)),
                ('berlaku_mulai', models.DateField()),
                ('berlaku_sampai', models.DateField(blank=True, null=True)),
                ('keterangan', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('pegawai', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='riwayat_pola_kerja', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pola kerja pegawai',
                'verbose_name_plural': 'Riwayat pola kerja pegawai',
                'ordering': ('-berlaku_mulai', '-pk'),
            },
        ),
    ]
