from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('myaccount', '0015_telegramaccount'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Menunggu Verifikasi'), ('approved', 'Disetujui'), ('rejected', 'Ditolak')], db_index=True, default='pending', max_length=10)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_account_registrations', to=settings.AUTH_USER_MODEL)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='registration_request', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-submitted_at',)},
        ),
    ]
