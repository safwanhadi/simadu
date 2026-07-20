import json
import logging
import secrets
from html import escape

from django.conf import settings
from django.contrib.auth.views import PasswordResetConfirmView
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from .models import TelegramAccount
from .telegram_service import (
    build_password_reset_url,
    find_active_users_by_phone,
    normalize_phone,
    request_contact,
    send_message,
)

logger = logging.getLogger(__name__)


class TelegramResetHelpView(TemplateView):
    template_name = 'telegram/reset_help.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        username = settings.TELEGRAM_BOT_USERNAME.lstrip('@')
        context['telegram_bot_username'] = username
        context['telegram_reset_url'] = (
            f'https://t.me/{username}?start=reset' if username else ''
        )
        return context


class TelegramPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'telegram/password_reset_confirm.html'
    success_url = reverse_lazy('myaccount_urls:telegram_password_reset_complete')


class TelegramPasswordResetCompleteView(TemplateView):
    template_name = 'telegram/password_reset_complete.html'


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        expected_secret = settings.TELEGRAM_WEBHOOK_SECRET
        provided_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if not expected_secret or not secrets.compare_digest(provided_secret, expected_secret):
            return HttpResponse(status=403)

        try:
            update = json.loads(request.body.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JsonResponse({'ok': False, 'error': 'invalid_json'}, status=400)

        message = update.get('message')
        if not message:
            return JsonResponse({'ok': True})

        chat = message.get('chat') or {}
        sender = message.get('from') or {}
        if chat.get('type') != 'private' or not chat.get('id') or not sender.get('id'):
            return JsonResponse({'ok': True})

        chat_id = int(chat['id'])
        telegram_user_id = int(sender['id'])
        text = (message.get('text') or '').strip()
        command = text.split()[0].split('@')[0].lower() if text.startswith('/') else ''

        try:
            if message.get('contact'):
                self._handle_contact(request, message, chat_id, telegram_user_id, sender)
            elif command in ('/start', '/reset'):
                self._handle_reset_request(request, chat_id, telegram_user_id)
            elif command == '/cancel':
                send_message(
                    chat_id,
                    'Proses dibatalkan. Gunakan /reset jika Anda ingin memulai kembali.',
                    {'remove_keyboard': True},
                )
            else:
                self._send_help(chat_id)
        except Exception as exc:
            logger.exception(
                'Pemrosesan webhook Telegram gagal: update_id=%s exception_type=%s',
                update.get('update_id'),
                type(exc).__name__,
            )
            return JsonResponse({'ok': False}, status=502)
        return JsonResponse({'ok': True})

    def _handle_reset_request(self, request, chat_id, telegram_user_id):
        link = (
            TelegramAccount.objects
            .select_related('user')
            .filter(telegram_user_id=telegram_user_id, user__is_active=True)
            .first()
        )
        if link:
            if link.chat_id != chat_id:
                link.chat_id = chat_id
                link.save(update_fields=['chat_id', 'updated_at'])
            self._send_reset_link(request, link)
            return
        request_contact(chat_id)

    def _handle_contact(self, request, message, chat_id, telegram_user_id, sender):
        contact = message['contact']
        if int(contact.get('user_id') or 0) != telegram_user_id:
            send_message(
                chat_id,
                'Kontak ditolak. Gunakan tombol <b>Bagikan Nomor Telepon</b> dan kirim nomor Telegram Anda sendiri.',
            )
            return

        phone_number = normalize_phone(contact.get('phone_number'))
        users = find_active_users_by_phone(phone_number)
        if not users:
            send_message(
                chat_id,
                'Nomor ini belum ditemukan pada profil SIMADU. Periksa nomor pada profil atau hubungi Tim IT Rumah Sakit Mandalika.',
                {'remove_keyboard': True},
            )
            return
        if len(users) > 1:
            send_message(
                chat_id,
                'Nomor ini digunakan oleh lebih dari satu akun SIMADU. Demi keamanan, reset ditolak. Silakan hubungi Tim IT.',
                {'remove_keyboard': True},
            )
            return

        user = users[0]
        user_link = TelegramAccount.objects.filter(user=user).first()
        telegram_link = TelegramAccount.objects.filter(
            telegram_user_id=telegram_user_id
        ).first()
        if (user_link and user_link.telegram_user_id != telegram_user_id) or (
            telegram_link and telegram_link.user_id != user.pk
        ):
            send_message(
                chat_id,
                'Akun SIMADU atau Telegram ini telah terhubung dengan identitas lain. Silakan hubungi Tim IT untuk verifikasi.',
                {'remove_keyboard': True},
            )
            return

        try:
            with transaction.atomic():
                link, _ = TelegramAccount.objects.update_or_create(
                    user=user,
                    defaults={
                        'telegram_user_id': telegram_user_id,
                        'chat_id': chat_id,
                        'phone_number': phone_number,
                        'telegram_username': sender.get('username', ''),
                    },
                )
        except IntegrityError:
            send_message(
                chat_id,
                'Identitas Telegram tidak dapat ditautkan. Silakan hubungi Tim IT untuk verifikasi.',
                {'remove_keyboard': True},
            )
            return
        self._send_reset_link(request, link)

    def _send_reset_link(self, request, link):
        cache_key = f'telegram-password-reset:{link.telegram_user_id}'
        now = timezone.now()
        cooldown = getattr(settings, 'TELEGRAM_RESET_COOLDOWN', 60)
        try:
            reset_allowed = cache.add(
                cache_key,
                True,
                cooldown,
            )
        except Exception:
            # Redis yang sementara tidak tersedia tidak boleh memutus alur reset.
            # Timestamp database tetap dipakai sebagai pembatas cadangan.
            logger.exception(
                'Cache cooldown Telegram gagal; menggunakan timestamp database: telegram_user_id=%s',
                link.telegram_user_id,
            )
            reset_allowed = not link.last_reset_requested_at or (
                now - link.last_reset_requested_at
            ).total_seconds() >= cooldown

        if not reset_allowed:
            send_message(
                link.chat_id,
                'Permintaan reset baru saja dikirim. Tunggu sebentar sebelum meminta tautan lain.',
                {'remove_keyboard': True},
            )
            return

        reset_url = build_password_reset_url(request, link.user)
        link.last_reset_requested_at = now
        link.save(update_fields=['last_reset_requested_at', 'updated_at'])
        name = escape(link.user.full_name or link.user.email)
        send_message(
            link.chat_id,
            f'<b>Reset password SIMADU</b>\n\nHalo {name}, tekan tombol berikut untuk membuat password baru. '
            'Tautan berlaku selama 30 menit dan hanya dapat digunakan sekali.',
            {
                'inline_keyboard': [[{
                    'text': 'Buat Password Baru',
                    'url': reset_url,
                }]],
            },
        )

    @staticmethod
    def _send_help(chat_id):
        send_message(
            chat_id,
            '<b>Bot Pemulihan Akun SIMADU</b>\n\n'
            '/reset - Meminta tautan reset password\n'
            '/help - Menampilkan bantuan\n'
            '/cancel - Membatalkan proses\n\n'
            'Bot tidak pernah meminta password Anda melalui chat.',
        )
