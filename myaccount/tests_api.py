from django.test import TestCase
from django.urls import reverse
from oauth2_provider.models import Application

from disiplinsdm.models import JenisSDMPerinstalasi
from jenissdm.models import JenisSDM, ProfesiSDM

from .models import ProfilSDM, Users


class TenagaPerawatAktifAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pengguna_integrasi = Users.objects.create_user(
            email='integrasi@example.test', first_name='Petugas', last_name='Integrasi',
        )
        profesi = ProfesiSDM.objects.create(profesi='Perawat')
        jenis_perawat = JenisSDM.objects.create(profesi=profesi, jenis_sdm='Perawat Klinis')
        jenis_dokter = JenisSDM.objects.create(jenis_sdm='Dokter Umum')

        cls.perawat_aktif = Users.objects.create_user(
            email='perawat.aktif@example.test', first_name='Siti', last_name='Perawat',
        )
        ProfilSDM.objects.create(
            user=cls.perawat_aktif, no_hp='08123456789',
            email_pribadi='siti.pribadi@example.test', nip='198001012010011001',
        )
        JenisSDMPerinstalasi.objects.create(
            pegawai=cls.perawat_aktif, jenis_sdm=jenis_perawat,
        )

        perawat_nonaktif = Users.objects.create_user(
            email='perawat.nonaktif@example.test', first_name='Tidak', last_name='Aktif',
            is_active=False,
        )
        JenisSDMPerinstalasi.objects.create(pegawai=perawat_nonaktif, jenis_sdm=jenis_perawat)

        dokter_aktif = Users.objects.create_user(
            email='dokter.aktif@example.test', first_name='Dokter', last_name='Aktif',
        )
        JenisSDMPerinstalasi.objects.create(pegawai=dokter_aktif, jenis_sdm=jenis_dokter)

    def setUp(self):
        self.client.force_login(self.pengguna_integrasi)

    def test_hanya_mengembalikan_tenaga_perawat_aktif_dengan_data_minimum(self):
        response = self.client.get(reverse('myaccount_urls:pegawai_perawat_aktif_api_view'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{
            'nip': '198001012010011001',
            'email': 'perawat.aktif@example.test',
            'first_name': 'Siti',
            'last_name': 'Perawat',
            'full_name': 'Siti Perawat',
        }])

    def test_client_credentials_dengan_scope_pegawai_dapat_mengakses_endpoint(self):
        client_secret = 'secret-integrasi-yang-aman'
        application = Application.objects.create(
            name='Integrasi Perawat',
            user=self.pengguna_integrasi,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            client_secret=client_secret,
        )

        token_response = self.client.post(
            reverse('oauth2_provider:token'),
            {
                'grant_type': 'client_credentials',
                'scope': 'read:pegawai',
            },
            HTTP_AUTHORIZATION=self._basic_auth(application.client_id, client_secret),
        )

        self.assertEqual(token_response.status_code, 200)
        access_token = token_response.json()['access_token']
        self.client.logout()

        response = self.client.get(
            reverse('myaccount_urls:pegawai_perawat_aktif_api_view'),
            HTTP_AUTHORIZATION=f'Bearer {access_token}',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['nip'], '198001012010011001')

    def test_client_credentials_tanpa_scope_pegawai_ditolak(self):
        client_secret = 'secret-integrasi-yang-aman'
        application = Application.objects.create(
            name='Integrasi Tanpa Scope Pegawai',
            user=self.pengguna_integrasi,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            client_secret=client_secret,
        )

        token_response = self.client.post(
            reverse('oauth2_provider:token'),
            {
                'grant_type': 'client_credentials',
                'scope': 'read:dash',
            },
            HTTP_AUTHORIZATION=self._basic_auth(application.client_id, client_secret),
        )

        self.assertEqual(token_response.status_code, 200)
        self.client.logout()
        response = self.client.get(
            reverse('myaccount_urls:pegawai_perawat_aktif_api_view'),
            HTTP_AUTHORIZATION=f"Bearer {token_response.json()['access_token']}",
        )

        self.assertEqual(response.status_code, 403)

    @staticmethod
    def _basic_auth(client_id, client_secret):
        import base64

        credentials = base64.b64encode(
            f'{client_id}:{client_secret}'.encode('utf-8')
        ).decode('ascii')
        return f'Basic {credentials}'
