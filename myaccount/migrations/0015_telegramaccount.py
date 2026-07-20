from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('myaccount', '0014_create_admin_layanan_jabatan_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='TelegramAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telegram_user_id', models.BigIntegerField(unique=True)),
                ('chat_id', models.BigIntegerField(unique=True)),
                ('phone_number', models.CharField(max_length=20)),
                ('telegram_username', models.CharField(blank=True, max_length=64)),
                ('verified_at', models.DateTimeField(auto_now_add=True)),
                ('last_reset_requested_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='telegram_account', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-updated_at',)},
        ),
    ]
