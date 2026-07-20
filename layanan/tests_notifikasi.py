from django.test import TestCase
from django.urls import reverse

from myaccount.models import Users


class NotifikasiViewSafetyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Users.objects.create_user(
            email='notifikasi-safety@example.com',
            first_name='Pegawai',
            last_name='Notifikasi',
            password='Password-Notif-123!',
        )

    def test_post_dengan_parameter_layanan_kosong_tetap_merespons(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('layanan_urls:notifikasi_update_view', kwargs={'id': 209}),
            query_params={'case': 'detail', 'layanan': ''},
        )

        self.assertRedirects(
            response,
            reverse('layanan_urls:notifikasi_view'),
            fetch_redirect_response=False,
        )

    def test_post_dengan_jenis_layanan_tidak_dikenal_tetap_merespons(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('layanan_urls:notifikasi_update_view', kwargs={'id': 209}),
            query_params={'case': 'detail', 'layanan': 'tidak-valid'},
        )

        self.assertEqual(response.status_code, 302)
