import json
from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import ProfilSDM, TelegramAccount, Users
from .telegram_service import normalize_phone


TELEGRAM_TEST_SETTINGS = {
    'TELEGRAM_BOT_TOKEN': 'test-token',
    'TELEGRAM_BOT_USERNAME': 'simadu_test_bot',
    'TELEGRAM_WEBHOOK_SECRET': 'test-webhook-secret',
    'TELEGRAM_PUBLIC_BASE_URL': 'https://simadu.example.com',
    'TELEGRAM_RESET_COOLDOWN': 1,
    'CACHES': {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
}


@override_settings(**TELEGRAM_TEST_SETTINGS)
class TelegramPasswordResetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Users.objects.create_user(
            email='pegawai-telegram@example.com',
            first_name='Pegawai',
            last_name='Telegram',
            password='Password-Lama-123!',
        )
        ProfilSDM.objects.create(
            user=cls.user,
            no_hp='0812-3456-7890',
            email_pribadi='pribadi@example.com',
            nip='1987654321',
        )

    def _webhook(self, payload, secret='test-webhook-secret'):
        return self.client.post(
            reverse('myaccount_urls:telegram_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret,
        )

    def test_normalisasi_nomor_indonesia(self):
        self.assertEqual(normalize_phone('0812-3456-7890'), '+6281234567890')
        self.assertEqual(normalize_phone('6281234567890'), '+6281234567890')
        self.assertEqual(normalize_phone('+62 812 3456 7890'), '+6281234567890')

    def test_webhook_menolak_secret_yang_salah(self):
        response = self._webhook({'update_id': 1}, secret='salah')

        self.assertEqual(response.status_code, 403)

    @patch('myaccount.telegram_views.request_contact')
    def test_start_meminta_pengguna_membagikan_kontak(self, mocked_request_contact):
        response = self._webhook({
            'update_id': 2,
            'message': {
                'message_id': 1,
                'text': '/start reset',
                'chat': {'id': 9001, 'type': 'private'},
                'from': {'id': 9001, 'username': 'pegawai_test'},
            },
        })

        self.assertEqual(response.status_code, 200)
        mocked_request_contact.assert_called_once_with(9001)

    @patch('myaccount.telegram_views.send_message')
    def test_kontak_sendiri_ditautkan_dan_menerima_reset_url(self, mocked_send):
        response = self._webhook({
            'update_id': 3,
            'message': {
                'message_id': 2,
                'chat': {'id': 9002, 'type': 'private'},
                'from': {'id': 9002, 'username': 'pegawai_test'},
                'contact': {
                    'user_id': 9002,
                    'phone_number': '+62 812-3456-7890',
                },
            },
        })

        self.assertEqual(response.status_code, 200)
        link = TelegramAccount.objects.get(user=self.user)
        self.assertEqual(link.telegram_user_id, 9002)
        self.assertEqual(link.phone_number, '+6281234567890')
        reply_markup = mocked_send.call_args.args[2]
        reset_url = reply_markup['inline_keyboard'][0][0]['url']
        self.assertTrue(reset_url.startswith('https://simadu.example.com/accounts/telegram/reset/'))

    @patch('myaccount.telegram_views.cache.add', side_effect=ConnectionError('Redis mati'))
    @patch('myaccount.telegram_views.send_message')
    def test_reset_tetap_dikirim_saat_cache_tidak_tersedia(
        self,
        mocked_send,
        mocked_cache_add,
    ):
        response = self._webhook({
            'update_id': 31,
            'message': {
                'message_id': 21,
                'chat': {'id': 9031, 'type': 'private'},
                'from': {'id': 9031, 'username': 'pegawai_test'},
                'contact': {
                    'user_id': 9031,
                    'phone_number': '+62 812-3456-7890',
                },
            },
        })

        self.assertEqual(response.status_code, 200)
        mocked_cache_add.assert_called_once()
        self.assertIn(
            'inline_keyboard',
            mocked_send.call_args.args[2],
        )

    @patch('myaccount.telegram_views.send_message')
    def test_kontak_orang_lain_ditolak(self, mocked_send):
        response = self._webhook({
            'update_id': 4,
            'message': {
                'message_id': 3,
                'chat': {'id': 9003, 'type': 'private'},
                'from': {'id': 9003},
                'contact': {'user_id': 1111, 'phone_number': '081234567890'},
            },
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TelegramAccount.objects.filter(telegram_user_id=9003).exists())
        self.assertIn('Kontak ditolak', mocked_send.call_args.args[1])

    def test_token_reset_django_dapat_dibuka(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse(
            'myaccount_urls:telegram_password_reset_confirm',
            kwargs={'uidb64': uid, 'token': token},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/set-password/', response['Location'])

    def test_halaman_bantuan_membentuk_deep_link_bot(self):
        response = self.client.get(reverse('myaccount_urls:telegram_reset_help'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'https://t.me/simadu_test_bot?start=reset')
