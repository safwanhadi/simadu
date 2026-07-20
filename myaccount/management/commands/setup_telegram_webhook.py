from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from myaccount.telegram_service import call_bot_api


class Command(BaseCommand):
    help = 'Daftarkan webhook dan daftar command Bot Telegram SIMADU.'

    def handle(self, *args, **options):
        required = {
            'TELEGRAM_BOT_TOKEN': settings.TELEGRAM_BOT_TOKEN,
            'TELEGRAM_BOT_USERNAME': settings.TELEGRAM_BOT_USERNAME,
            'TELEGRAM_WEBHOOK_SECRET': settings.TELEGRAM_WEBHOOK_SECRET,
            'TELEGRAM_PUBLIC_BASE_URL': settings.TELEGRAM_PUBLIC_BASE_URL,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise CommandError(f'Konfigurasi belum lengkap: {", ".join(missing)}')
        if not settings.TELEGRAM_PUBLIC_BASE_URL.startswith('https://'):
            raise CommandError(
                'TELEGRAM_PUBLIC_BASE_URL harus menggunakan HTTPS untuk webhook Telegram.'
            )

        webhook_url = f'{settings.TELEGRAM_PUBLIC_BASE_URL}/accounts/telegram/webhook/'
        call_bot_api('setWebhook', {'url': webhook_url, 'secret_token': settings.TELEGRAM_WEBHOOK_SECRET, 'allowed_updates': ['message'], 'drop_pending_updates': True})
        call_bot_api('setMyCommands', {'commands': [
            {'command': 'start', 'description': 'Memulai layanan SIMADU'},
            {'command': 'reset', 'description': 'Meminta tautan reset password'},
            {'command': 'help', 'description': 'Menampilkan bantuan'},
            {'command': 'cancel', 'description': 'Membatalkan proses'},
        ]})
        self.stdout.write(self.style.SUCCESS(f'Webhook Telegram aktif: {webhook_url}'))
