from datetime import date
from tempfile import TemporaryDirectory

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from dashboard.context_processors import notifikasi_layanan
from dokumen.models import (
    DokumenSDM,
    PangkatGolongan,
    PredikatKinerja,
    RiwayatKinerja,
    RiwayatPanggol,
    RiwayatPendidikan,
    RiwayatPengangkatan,
    RiwayatJabatan,
    RiwayatPAK,
    UjiKompetensi,
)
from jenissdm.models import JenisSDM, ListKompetensi
from myaccount.models import Users
from myaccount.roles import ADMIN_LAYANAN_JABATAN, ADMIN_LAYANAN_PANGKAT

from .models import JenisLayanan, LayananNaikJabatan, LayananNaikPangkat


class LayananNaikPangkatWorkflowTests(TestCase):
    def setUp(self):
        self.temp_media = TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.media_override.enable()

        self.pegawai = Users.objects.create_user(
            email='pegawai-pangkat@example.com',
            first_name='Pegawai',
            last_name='Pangkat',
            password='test-password',
        )
        self.admin = Users.objects.create_user(
            email='admin-pangkat@example.com',
            first_name='Admin',
            last_name='Pangkat',
            password='test-password',
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_LAYANAN_PANGKAT)
        self.admin.groups.add(group)

        self.jenis_layanan = JenisLayanan.objects.update_or_create(
            url='yanpangkat',
            defaults={
                'nama': 'Kenaikan Pangkat',
                'status': True,
                'icon': 'fa-level-up-alt',
            },
        )[0]
        self.dokumen_pangkat = DokumenSDM.objects.create(
            nama='Pangkat/Golongan', url='panggol', view=True
        )
        self.pangkat_lama = PangkatGolongan.objects.create(
            pangkat='Penata', golongan='III', ruang='c'
        )
        self.pangkat_baru = PangkatGolongan.objects.create(
            pangkat='Penata Tingkat I', golongan='III', ruang='d'
        )
        self.riwayat_lama = RiwayatPanggol.objects.create(
            pegawai=self.pegawai,
            dokumen=self.dokumen_pangkat,
            panggol=self.pangkat_lama,
            masa_kerja_tahun=8,
            masa_kerja_bulan=0,
            no_sk='SK-LAMA',
        )
        predikat = PredikatKinerja.objects.create(
            predikat='Sesuai', prosentase=100
        )
        self.predikat = predikat
        self.kinerja_1 = RiwayatKinerja.objects.create(
            pegawai=self.pegawai,
            dokumen=self.dokumen_pangkat,
            periode_kinerja_awal=date(2024, 1, 1),
            periode_kinerja_akhir=date(2024, 12, 31),
            kuadran_kinerja=predikat,
        )
        self.kinerja_2 = RiwayatKinerja.objects.create(
            pegawai=self.pegawai,
            dokumen=self.dokumen_pangkat,
            periode_kinerja_awal=date(2025, 1, 1),
            periode_kinerja_akhir=date(2025, 12, 31),
            kuadran_kinerja=predikat,
        )
        self.pendidikan = RiwayatPendidikan.objects.create(
            pegawai=self.pegawai,
            dokumen=self.dokumen_pangkat,
            level_pend='S1',
            pendidikan='Administrasi Negara',
            nama_sek='Universitas Uji',
            no_ijazah='IJZ-001',
        )
        self.pengangkatan = RiwayatPengangkatan.objects.create(
            pegawai=self.pegawai,
            dokumen=self.dokumen_pangkat,
            status_pegawai='PNS',
            no_srt_putusan='SK-PNS-001',
            tgl_srt_putusan=date(2020, 1, 1),
        )

    def tearDown(self):
        self.media_override.disable()
        self.temp_media.cleanup()

    def test_pengajuan_diproses_menjadi_riwayat_panggol(self):
        self.client.force_login(self.pegawai)
        response = self.client.post(
            reverse('layanan_urls:layanan_pangkat_create'),
            {
                'sk_kp_terakhir': self.riwayat_lama.pk,
                'kinerja_dua_thn': [self.kinerja_1.pk, self.kinerja_2.pk],
                'pendidikan': self.pendidikan.pk,
                'pengangkatan': self.pengangkatan.pk,
                'sk_jabfung': '',
                'mutasi': '',
            },
        )
        self.assertEqual(response.status_code, 302)

        usulan = LayananNaikPangkat.objects.get(pegawai=self.pegawai)
        self.assertEqual(usulan.status, 'pengajuan')
        self.assertEqual(usulan.kinerja_dua_thn.count(), 2)

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('layanan_urls:layanan_pangkat_process', kwargs={'pk': usulan.pk}),
            {
                'panggol': self.pangkat_baru.pk,
                'masa_kerja_tahun': 10,
                'masa_kerja_bulan': 2,
                'tmt_gol': '2026-10-01',
                'no_sk': 'SK-BARU-001',
                'tgl_sk': '2026-10-01',
                'no_pertek_bkn': 'PERTEK-001',
                'tgl_pertek_bkn': '2026-09-15',
                'file': SimpleUploadedFile('sk-baru.pdf', b'%PDF-1.4 test', 'application/pdf'),
            },
        )
        self.assertEqual(response.status_code, 302)

        usulan.refresh_from_db()
        hasil = RiwayatPanggol.objects.get(usulan=usulan)
        self.assertEqual(usulan.status, 'selesai')
        self.assertFalse(usulan.is_read)
        self.assertEqual(hasil.pegawai, self.pegawai)
        self.assertEqual(hasil.panggol, self.pangkat_baru)

        request = type('Request', (), {'user': self.pegawai})()
        notifications = notifikasi_layanan(request)
        self.assertEqual(len(notifications['notif_pangkat']), 1)


class LayananNaikJabatanWorkflowTests(TestCase):
    def setUp(self):
        self.temp_media = TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.media_override.enable()

        self.pegawai = Users.objects.create_user(
            email='pegawai-jabatan@example.com',
            first_name='Pegawai',
            last_name='Jabatan',
            password='test-password',
        )
        self.admin = Users.objects.create_user(
            email='admin-jabatan@example.com',
            first_name='Admin',
            last_name='Jabatan',
            password='test-password',
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_LAYANAN_JABATAN)
        self.admin.groups.add(group)

        JenisLayanan.objects.update_or_create(
            url='yanjabatan',
            defaults={
                'nama': 'Kenaikan Jabatan',
                'status': True,
                'icon': 'fa-user-tie',
            },
        )
        self.dokumen_jabatan = DokumenSDM.objects.create(
            nama='Riwayat Jabatan', url='jabatan', view=True
        )
        predikat = PredikatKinerja.objects.create(
            predikat='Sesuai', prosentase=100
        )
        self.predikat = predikat
        self.kinerja_1 = RiwayatKinerja.objects.create(
            pegawai=self.pegawai,
            dokumen=self.dokumen_jabatan,
            periode_kinerja_awal=date(2024, 1, 1),
            periode_kinerja_akhir=date(2024, 12, 31),
            kuadran_kinerja=predikat,
        )
        self.kinerja_2 = RiwayatKinerja.objects.create(
            pegawai=self.pegawai,
            dokumen=self.dokumen_jabatan,
            periode_kinerja_awal=date(2025, 1, 1),
            periode_kinerja_akhir=date(2025, 12, 31),
            kuadran_kinerja=predikat,
        )
        jenis_sdm = JenisSDM.objects.create(jenis_sdm='Perawat')
        kompetensi = ListKompetensi.objects.create(
            jenis_sdm=jenis_sdm,
            kompetensi='Uji Kompetensi Perawat',
        )
        self.list_kompetensi = kompetensi
        self.uji_kompetensi = UjiKompetensi.objects.create(
            pegawai=self.pegawai,
            kompetensi=kompetensi,
            no_sert_ujikomp='UKOM-001',
            tgl_sert_ujikomp=date(2026, 1, 1),
        )
        self.pak = RiwayatPAK.objects.create(
            pegawai=self.pegawai,
            dokumen=self.dokumen_jabatan,
            no_srt='PAK-001',
            tgl_srt=date(2026, 1, 1),
            ak=100,
        )
        self.nama_jabatan = jenis_sdm

    def tearDown(self):
        self.media_override.disable()
        self.temp_media.cleanup()

    def test_pintasan_dapat_menambah_pak_dan_riwayat_uji_kompetensi(self):
        self.client.force_login(self.pegawai)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_pak_create') + '?popup=1&field=id_pak',
            {
                'no_srt': 'PAK-QUICK-001',
                'tgl_srt': '2026-02-01',
                'ak': 125,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            RiwayatPAK.objects.filter(
                pegawai=self.pegawai, no_srt='PAK-QUICK-001'
            ).exists()
        )
        self.assertContains(response, 'id_pak')

        response = self.client.post(
            reverse('riwayat_urls:riwayat_kinerja_create') + '?popup=1&field=id_kinerja_dua_thn',
            {
                'hasil_kinerja': 'sesuai',
                'prilaku_kinerja': 'sesuai',
                'kuadran_kinerja': self.predikat.pk,
                'periode_kinerja_awal': '2026-01-01',
                'periode_kinerja_akhir': '2026-12-31',
                'nama_penilai': self.admin.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            RiwayatKinerja.objects.filter(
                pegawai=self.pegawai,
                periode_kinerja_awal=date(2026, 1, 1),
            ).exists()
        )
        self.assertContains(response, 'id_kinerja_dua_thn')

        response = self.client.post(
            reverse('riwayat_urls:riwayat_ujikom_create') + '?popup=1&field=id_kompetensi',
            {
                'kompetensi': self.list_kompetensi.pk,
                'no_sert_ujikomp': 'UKOM-QUICK-001',
                'tgl_sert_ujikomp': '2026-02-01',
                'masa_berlaku': 5,
                'kategori_kompetensi': 'on',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            UjiKompetensi.objects.filter(
                pegawai=self.pegawai, no_sert_ujikomp='UKOM-QUICK-001'
            ).exists()
        )
        self.assertContains(response, 'id_kompetensi')

    def test_pengajuan_diproses_menjadi_riwayat_jabatan(self):
        self.client.force_login(self.pegawai)
        response = self.client.post(
            reverse('layanan_urls:layanan_jabatan_create'),
            {
                'kinerja_dua_thn': [self.kinerja_1.pk, self.kinerja_2.pk],
                'kompetensi': self.uji_kompetensi.pk,
                'pendidikan': '',
                'str_profesi': '',
                'pak': self.pak.pk,
            },
        )
        self.assertEqual(response.status_code, 302)

        usulan = LayananNaikJabatan.objects.get(pegawai=self.pegawai)
        self.assertEqual(usulan.status, 'pengajuan')
        self.assertEqual(usulan.kinerja_dua_thn.count(), 2)

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('layanan_urls:layanan_jabatan_process', kwargs={'pk': usulan.pk}),
            {
                'unor': '',
                'bidang': '',
                'sub_bidang': '',
                'instalasi': '',
                'jns_jabatan': 'Fungsional',
                'jenjang_jabatan': '',
                'nama_jabatan': self.nama_jabatan.pk,
                'detail_nama_jabatan': 'Perawat Ahli Pertama',
                'tmt_jabatan': '2026-10-01',
                'tmt_pelantikan': '',
                'no_sk': 'SK-JABATAN-001',
                'tgl_sk': '2026-10-01',
                'file': SimpleUploadedFile(
                    'sk-jabatan.pdf', b'%PDF-1.4 test', 'application/pdf'
                ),
            },
        )
        self.assertEqual(response.status_code, 302, response.context['form'].errors if response.context else '')

        usulan.refresh_from_db()
        hasil = RiwayatJabatan.objects.get(usulan=usulan)
        self.assertEqual(usulan.status, 'selesai')
        self.assertFalse(usulan.is_read)
        self.assertEqual(hasil.pegawai, self.pegawai)
        self.assertEqual(hasil.nama_jabatan, self.nama_jabatan)

        request = type('Request', (), {'user': self.pegawai})()
        notifications = notifikasi_layanan(request)
        self.assertEqual(len(notifications['notif_jabatan']), 1)
