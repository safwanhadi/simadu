import json
import logging
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import ProfilSDM

logger = logging.getLogger(__name__)


def normalize_phone(value):
    digits = re.sub(r'\D', '', value or '')
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith('0'):
        digits = f'62{digits[1:]}'
    elif digits.startswith('8'):
        digits = f'62{digits}'
    if not digits.startswith('62') or len(digits) < 10:
        return ''
    return f'+{digits}'


def find_active_users_by_phone(phone_number):
    normalized = normalize_phone(phone_number)
    if not normalized:
        return []
    matches = []
    profiles = ProfilSDM.objects.select_related('user').filter(user__is_active=True)
    for profile in profiles.iterator():
        if normalize_phone(profile.no_hp) == normalized:
            matches.append(profile.user)
            if len(matches) > 1:
                break
    return matches


def call_bot_api(method, payload):
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ImproperlyConfigured('TELEGRAM_BOT_TOKEN belum dikonfigurasi.')
    request = Request(
        f'https://api.telegram.org/bot{token}/{method}',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        description = ''
        try:
            error_result = json.loads(exc.read().decode('utf-8'))
            description = error_result.get('description', '')
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        logger.exception(
            'Telegram API gagal: method=%s status=%s description=%s',
            method,
            exc.code,
            description,
        )
        raise
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.exception(
            'Telegram API gagal: method=%s exception_type=%s',
            method,
            type(exc).__name__,
        )
        raise
    if not result.get('ok'):
        logger.error('Telegram API menolak request: method=%s', method)
        raise RuntimeError(f'Telegram API gagal menjalankan {method}.')
    return result.get('result')


def send_message(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup
    return call_bot_api('sendMessage', payload)


def request_contact(chat_id):
    return send_message(
        chat_id,
        '<b>Verifikasi nomor telepon</b>\n\n'
        'Tekan tombol di bawah untuk membagikan nomor Telegram Anda. '
        'Nomor harus sama dengan nomor pada profil SIMADU.\n\n'
        'Jika tombol belum terlihat, tekan ikon keyboard ⌨️ di samping kolom pesan. '
        'Gunakan aplikasi Telegram di ponsel jika tombol tetap tidak muncul.',
        {
            'keyboard': [[{'text': 'Bagikan Nomor Telepon', 'request_contact': True}]],
            'resize_keyboard': True,
            'is_persistent': True,
            'input_field_placeholder': 'Bagikan nomor untuk melanjutkan',
        },
    )


def build_password_reset_url(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse(
        'myaccount_urls:telegram_password_reset_confirm',
        kwargs={'uidb64': uid, 'token': token},
    )
    base_url = settings.TELEGRAM_PUBLIC_BASE_URL or request.build_absolute_uri('/').rstrip('/')
    return f'{base_url}{path}'
