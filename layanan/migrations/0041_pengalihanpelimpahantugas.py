from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('layanan', '0040_layanannaikjabatan_surat_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PengalihanPelimpahanTugas',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alasan', models.TextField()),
                ('status', models.CharField(choices=[('menunggu', 'Menunggu persetujuan'), ('disetujui', 'Disetujui'), ('ditolak', 'Ditolak')], default='menunggu', max_length=15)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('dialihkan_oleh', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pengalihan_pelimpahan_dilakukan', to=settings.AUTH_USER_MODEL)),
                ('pelimpahan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='riwayat_pengalihan', to='layanan.pelimpahantugas')),
                ('penerima_baru', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pengalihan_pelimpahan_masuk', to=settings.AUTH_USER_MODEL)),
                ('penerima_lama', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pengalihan_pelimpahan_keluar', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
