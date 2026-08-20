from django.test import RequestFactory, SimpleTestCase

from .access import get_safe_return_url, preserve_return_url


class SafeReturnUrlTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_accepts_internal_relative_url(self):
        request = self.factory.get(
            '/riwayat/panggol/',
            {'return_to': '/layanan/yanpangkat/tambah/'},
        )
        self.assertEqual(
            get_safe_return_url(request),
            '/layanan/yanpangkat/tambah/',
        )

    def test_rejects_external_url(self):
        request = self.factory.get(
            '/riwayat/panggol/',
            {'return_to': 'https://example.com/phishing'},
        )
        self.assertIsNone(get_safe_return_url(request))

    def test_accepts_redirect_to_alias(self):
        request = self.factory.get(
            '/riwayat/panggol/',
            {'redirect_to': '/layanan/yanjabatan/tambah/'},
        )
        self.assertEqual(
            get_safe_return_url(request),
            '/layanan/yanjabatan/tambah/',
        )

    def test_preserves_return_url_on_success_redirect(self):
        request = self.factory.get(
            '/riwayat/panggol/',
            {'return_to': '/layanan/yanpangkat/tambah/'},
        )
        self.assertEqual(
            preserve_return_url(request, '/riwayat/panggol/'),
            (
                '/riwayat/panggol/'
                '?return_to=%2Flayanan%2Fyanpangkat%2Ftambah%2F'
            ),
        )
