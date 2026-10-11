import base64
from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from oauth2_provider.models import Application

from jenissdm.models import JenisSDM, ProfesiSDM
from myaccount.models import ProfilSDM, Users
from strukturorg.models import Bidang, InstansiDaerah, SatuanKerjaInduk, SubBidang, UnitInstalasi, UnitOrganisasi

from .models import (
    ApprovedJadwalDinasSDM,
    DetailKategoriJadwalDinas,
    JenisSDMPerinstalasi,
    KategoriJadwalDinas,
)


class JadwalDokterAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Users.objects.create_user(
            email='integrasi-mandacare@example.com', first_name='Petugas', last_name='Integrasi',
        )
        cls.dokter = Users.objects.create_user(
            email='dokter-igd@example.com', first_name='Dokter', last_name='IGD',
        )
        ProfilSDM.objects.create(
            user=cls.dokter, no_hp='08123456789', email_pribadi='dokter.pribadi@example.com',
            no_ktp='5201010101010001', nip='198001012010011001',
        )
        non_dokter = Users.objects.create_user(
            email='perawat-igd@example.com', first_name='Perawat', last_name='IGD',
        )
        ProfilSDM.objects.create(
            user=non_dokter, no_hp='08123456780', email_pribadi='perawat.pribadi@example.com',
            no_ktp='5201010101010002', nip='198001012010011002',
        )

        instansi = InstansiDaerah.objects.create(instansi='Instansi Uji')
        satker = SatuanKerjaInduk.objects.create(instansi_daerah=instansi, satuan_kerja='Satker Uji')
        unor = UnitOrganisasi.objects.create(satker_induk=satker, unor='Unor Uji')
        bidang = Bidang.objects.create(unor=unor, bidang='Bidang Uji')
        sub_bidang = SubBidang.objects.create(bidang=bidang, sub_bidang='Subbidang Uji')
        instalasi = UnitInstalasi.objects.create(sub_bidang=sub_bidang, instalasi='IGD')
        profesi = ProfesiSDM.objects.create(profesi='Dokter Umum')
        jenis_dokter = JenisSDM.objects.create(profesi=profesi, jenis_sdm='Dokter Umum')
        jenis_perawat = JenisSDM.objects.create(jenis_sdm='Perawat')
        metadata = dict(
            unor=unor, bidang=bidang, sub_bidang=sub_bidang, instalasi=instalasi,
            bulan=9, tahun=2026, status='disetujui',
        )
        jadwal_dokter = JenisSDMPerinstalasi.objects.create(pegawai=cls.dokter, jenis_sdm=jenis_dokter, **metadata)
        jadwal_perawat = JenisSDMPerinstalasi.objects.create(pegawai=non_dokter, jenis_sdm=jenis_perawat, **metadata)
        kategori = KategoriJadwalDinas.objects.create(kategori_dinas='Piket')
        detail = DetailKategoriJadwalDinas.objects.create(
            kategori_dinas=kategori, kategori_jadwal='Malam',
            waktu_datang=time(20, 0), waktu_pulang=time(8, 0),
        )
        cls.tanggal = date(2026, 9, 18)
        ApprovedJadwalDinasSDM.objects.create(
            pegawai=jadwal_dokter, tanggal=cls.tanggal, kategori_jadwal=detail, is_approved=True,
        )
        ApprovedJadwalDinasSDM.objects.create(
            pegawai=jadwal_perawat, tanggal=cls.tanggal, kategori_jadwal=detail, is_approved=True,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_mengembalikan_jadwal_dokter_dengan_nama_lengkap(self):
        response = self.client.get(reverse('disiplinsdm_urls:api_jadwal_dokter'), {'tanggal': self.tanggal})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        jadwal = response.json()[0]
        self.assertEqual(jadwal['nama_dokter'], 'Dokter IGD')
        self.assertEqual(jadwal['nama_lengkap_dokter'], 'Dokter IGD')
        self.assertEqual(jadwal['nik'], '5201010101010001')
        self.assertEqual(jadwal['nip'], '198001012010011001')
        self.assertTrue(jadwal['identitas_valid'])
        self.assertEqual(jadwal['instalasi'], 'IGD')
        self.assertEqual(jadwal['kategori_jadwal'], 'Malam')
        self.assertEqual(jadwal['waktu_mulai'], '20:00:00')
        self.assertEqual(jadwal['waktu_selesai'], '08:00:00')

    def test_menolak_format_tanggal_tidak_valid(self):
        response = self.client.get(reverse('disiplinsdm_urls:api_jadwal_dokter'), {'tanggal': '18-09-2026'})

        self.assertEqual(response.status_code, 400)

    def test_dapat_memfilter_jadwal_berdasarkan_dokter_dan_instalasi(self):
        response = self.client.get(
            reverse('disiplinsdm_urls:api_jadwal_dokter'),
            {
                'tanggal': self.tanggal,
                'dokter_id': self.dokter.pk,
                'nik': '5201010101010001',
                'nip': '198001012010011001',
                'instalasi': 'igd',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_filter_instalasi_yang_tidak_cocok_mengembalikan_daftar_kosong(self):
        response = self.client.get(
            reverse('disiplinsdm_urls:api_jadwal_dokter'),
            {'tanggal': self.tanggal, 'instalasi': 'Rawat Jalan'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_menolak_dokter_id_bukan_angka(self):
        response = self.client.get(
            reverse('disiplinsdm_urls:api_jadwal_dokter'),
            {'tanggal': self.tanggal, 'dokter_id': 'dokter-igd'},
        )

        self.assertEqual(response.status_code, 400)

    def test_client_credentials_dengan_scope_listpegawai_dapat_mengakses_jadwal(self):
        access_token = self._buat_client_credentials_token('read:listpegawai')
        self.client.logout()

        response = self.client.get(
            reverse('disiplinsdm_urls:api_jadwal_dokter'),
            {'tanggal': self.tanggal},
            HTTP_AUTHORIZATION=f'Bearer {access_token}',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['nama_lengkap_dokter'], 'Dokter IGD')

    def test_client_credentials_tanpa_scope_listpegawai_ditolak(self):
        access_token = self._buat_client_credentials_token('read:dash')
        self.client.logout()

        response = self.client.get(
            reverse('disiplinsdm_urls:api_jadwal_dokter'),
            {'tanggal': self.tanggal},
            HTTP_AUTHORIZATION=f'Bearer {access_token}',
        )

        self.assertEqual(response.status_code, 403)

    def _buat_client_credentials_token(self, scope):
        client_secret = 'secret-integrasi-jadwal-dokter'
        application = Application.objects.create(
            name=f'Integrasi Jadwal Dokter {scope}',
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            client_secret=client_secret,
        )
        credentials = base64.b64encode(
            f'{application.client_id}:{client_secret}'.encode('utf-8')
        ).decode('ascii')
        response = self.client.post(
            reverse('oauth2_provider:token'),
            {'grant_type': 'client_credentials', 'scope': scope},
            HTTP_AUTHORIZATION=f'Basic {credentials}',
        )
        self.assertEqual(response.status_code, 200)
        return response.json()['access_token']
