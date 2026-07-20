from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from dateutil.relativedelta import relativedelta

from myaccount.models import ProfilSDM, Users
from myaccount.roles import ADMIN_DOKUMEN
from jenissdm.models import JenisSDM
from strukturorg.models import InstansiDaerah, SatuanKerjaInduk, UnitOrganisasi

from .forms import RiwayatPendidikanForm
from .models import (
    DokumenSDM,
    PangkatGolongan,
    PredikatKinerja,
    RiwayatJabatan,
    RiwayatGajiBerkala,
    RiwayatKinerja,
    RiwayatPanggol,
    RiwayatPendidikan,
    RiwayatPengangkatan,
    RiwayatPenempatan,
)


class DocumentAccessSecurityTests(TestCase):
    password = 'Password-Dokumen-123!'

    @classmethod
    def setUpTestData(cls):
        cls.employee = Users.objects.create_user(
            email='pegawai-dokumen@example.com',
            first_name='Pegawai',
            last_name='Dokumen',
            password=cls.password,
        )
        ProfilSDM.objects.create(
            user=cls.employee,
            nip='19870001',
            no_hp='081200000001',
            email_pribadi=cls.employee.email,
        )
        cls.other_employee = Users.objects.create_user(
            email='pegawai-lain@example.com',
            first_name='Pegawai',
            last_name='Lain',
            password=cls.password,
        )
        ProfilSDM.objects.create(
            user=cls.other_employee,
            nip='19870002',
            no_hp='081200000002',
            email_pribadi=cls.other_employee.email,
        )
        cls.document_admin = Users.objects.create_user(
            email='admin-dokumen@example.com',
            first_name='Admin',
            last_name='Dokumen',
            password=cls.password,
        )
        ProfilSDM.objects.create(
            user=cls.document_admin,
            nip='19870003',
            no_hp='081200000003',
            email_pribadi=cls.document_admin.email,
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_DOKUMEN)
        cls.document_admin.groups.add(group)

        cls.document_type = DokumenSDM.objects.create(
            nama='Riwayat Pendidikan',
            url='pendidikan',
        )
        cls.own_document = RiwayatPendidikan.objects.create(
            pegawai=cls.employee,
            dokumen=cls.document_type,
            level_pend='S1',
            pendidikan='Pendidikan Milik Sendiri',
            nama_sek='Universitas Sendiri',
            no_ijazah='IJAZAH-SENDIRI',
        )
        cls.other_document = RiwayatPendidikan.objects.create(
            pegawai=cls.other_employee,
            dokumen=cls.document_type,
            level_pend='S1',
            pendidikan='Pendidikan Milik Pegawai Lain',
            nama_sek='Universitas Lain',
            no_ijazah='IJAZAH-LAIN',
        )
        cls.panggol_document_type = DokumenSDM.objects.create(
            nama='Riwayat Pangkat/Golongan',
            url='panggol',
            periode_min=48,
            periode_max=48,
        )
        cls.panggol = PangkatGolongan.objects.create(
            golongan='III',
            ruang='a',
            pangkat='Penata Muda',
        )
        cls.jabatan_document_type = DokumenSDM.objects.create(
            nama='Riwayat Jabatan',
            url='jabatan',
        )
        cls.nama_jabatan = JenisSDM.objects.create(
            jenis_sdm='Pengelola Kepegawaian',
        )
        cls.pengangkatan_document_type = DokumenSDM.objects.create(
            nama='Riwayat Pengangkatan',
            url='pengangkatan',
        )
        cls.penempatan_document_type = DokumenSDM.objects.create(
            nama='Riwayat Penempatan',
            url='penempatan',
        )
        cls.berkala_document_type = DokumenSDM.objects.create(
            nama='Riwayat Gaji Berkala',
            url='berkala',
        )
        cls.kinerja_document_type = DokumenSDM.objects.create(
            nama='Riwayat Kinerja',
            url='kinerja',
        )
        cls.predikat_kinerja = PredikatKinerja.objects.create(
            predikat='Baik',
            prosentase=100,
        )
        instansi = InstansiDaerah.objects.create(instansi='RS Mandalika')
        satker = SatuanKerjaInduk.objects.create(
            instansi_daerah=instansi,
            satuan_kerja='Rumah Sakit',
        )
        cls.unit_organisasi = UnitOrganisasi.objects.create(
            satker_induk=satker,
            unor='Direktorat Administrasi',
        )

    def test_parameter_nip_tidak_membuka_dokumen_pegawai_lain(self):
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse('riwayat_urls:riwayat_pendidikan'),
            {'nip': self.other_employee.profil_user.nip},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.own_document.pendidikan)
        self.assertNotContains(response, self.other_document.pendidikan)

    def test_menu_riwayat_menandai_dokumen_kosong(self):
        RiwayatPengangkatan.objects.create(
            pegawai=self.employee,
            dokumen=self.pengangkatan_document_type,
            status_pegawai='PNS',
            no_srt_putusan='SK-STATUS-PNS',
            tgl_srt_putusan=date.today(),
            tmt_pegawai=date.today(),
        )
        self.client.force_login(self.employee)

        response = self.client.get(reverse('riwayat_urls:riwayat_view'))

        documents = {
            document.url: document
            for document in response.context['jenis_dok']
        }
        self.assertFalse(documents['pendidikan'].is_empty)
        self.assertTrue(documents['panggol'].is_empty)
        self.assertContains(response, 'Dokumen masih kosong')

    def test_dokumen_opsional_tetap_terlihat_tanpa_ditandai_kosong(self):
        optional_document = DokumenSDM.objects.create(
            nama='Riwayat Hukuman',
            url='hukuman',
        )
        RiwayatPengangkatan.objects.create(
            pegawai=self.employee,
            dokumen=self.pengangkatan_document_type,
            status_pegawai='PNS',
            no_srt_putusan='SK-STATUS-OPSIONAL',
            tgl_srt_putusan=date.today(),
            tmt_pegawai=date.today(),
        )
        self.client.force_login(self.employee)

        response = self.client.get(reverse('riwayat_urls:riwayat_view'))

        document = next(
            item for item in response.context['jenis_dok']
            if item.pk == optional_document.pk
        )
        self.assertFalse(document.is_required)
        self.assertFalse(document.is_empty)
        self.assertContains(response, 'Opsional')

    def test_status_kosong_admin_mengikuti_pegawai_yang_dipilih(self):
        self.create_panggol_document(employee=self.employee)
        RiwayatPengangkatan.objects.create(
            pegawai=self.other_employee,
            dokumen=self.pengangkatan_document_type,
            status_pegawai='Kontrak',
            no_srt_putusan='SK-STATUS-KONTRAK',
            tgl_srt_putusan=date.today(),
            tmt_pegawai=date.today(),
        )
        self.client.force_login(self.document_admin)

        response = self.client.get(
            reverse('riwayat_urls:riwayat_view'),
            {'nip': self.other_employee.profil_user.nip},
        )

        document_urls = {
            document.url for document in response.context['jenis_dok']
        }
        self.assertNotIn('panggol', document_urls)
        self.assertNotIn(
            'panggol',
            {document.url for document in response.context['data_dokumen']},
        )
        self.assertNotIn(
            'panggol',
            {link[2] for link in response.context['document_quick_links']},
        )
        self.assertEqual(response.context['employment_status'], 'Kontrak')

    def test_pegawai_tanpa_status_hanya_melihat_pengangkatan(self):
        self.client.force_login(self.employee)

        response = self.client.get(reverse('riwayat_urls:riwayat_view'))

        self.assertEqual(
            [document.url for document in response.context['jenis_dok']],
            ['pengangkatan'],
        )
        self.assertTrue(response.context['employment_record_missing'])

    def test_update_dokumen_pegawai_lain_menghasilkan_404(self):
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse(
                'riwayat_urls:riwayat_update_pendidikan',
                args=[self.other_document.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_dokumen_pegawai_lain_menghasilkan_404(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse(
                'riwayat_urls:riwayat_delete_pendidikan',
                args=[self.other_document.pk],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            RiwayatPendidikan.objects.filter(pk=self.other_document.pk).exists()
        )

    def test_delete_dokumen_mewajibkan_login(self):
        response = self.client.post(
            reverse(
                'riwayat_urls:riwayat_delete_pendidikan',
                args=[self.own_document.pk],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_pegawai_tidak_dapat_mengatur_verifikasi_ijazah(self):
        form = RiwayatPendidikanForm(request=type(
            'Request',
            (),
            {'user': self.employee},
        )())

        self.assertNotIn('is_verifikasi', form.fields)
        self.assertNotIn('file_verifikasi', form.fields)

    def test_post_pegawai_lain_dipaksa_kembali_ke_akun_sendiri(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_pendidikan'),
            {
                'pegawai': self.other_employee.pk,
                'dokumen': self.document_type.pk,
                'level_pend': 'S1',
                'pendidikan': 'Pendidikan Baru Aman',
                'nama_sek': 'Universitas Aman',
                'no_ijazah': 'IJAZAH-AMAN',
                'is_verifikasi': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        created = RiwayatPendidikan.objects.get(pendidikan='Pendidikan Baru Aman')
        self.assertEqual(created.pegawai, self.employee)
        self.assertFalse(created.is_verifikasi)

    def panggol_payload(self, **overrides):
        payload = {
            'pegawai': self.other_employee.pk,
            'dokumen': self.panggol_document_type.pk,
            'panggol': self.panggol.pk,
            'masa_kerja_tahun': 4,
            'masa_kerja_bulan': 0,
            'tmt_gol': date.today().isoformat(),
            'no_sk': 'SK-PANGGOL-BARU',
            'tgl_sk': date.today().isoformat(),
            'no_pertek_bkn': '',
            'tgl_pertek_bkn': '',
        }
        payload.update(overrides)
        return payload

    def create_panggol_document(self, employee=None, **overrides):
        values = {
            'pegawai': employee or self.employee,
            'dokumen': self.panggol_document_type,
            'panggol': self.panggol,
            'masa_kerja_tahun': 1,
            'masa_kerja_bulan': 0,
            'tmt_gol': date.today(),
            'no_sk': 'SK-PANGGOL-AWAL',
        }
        values.update(overrides)
        return RiwayatPanggol.objects.create(**values)

    def test_reusable_panggol_mengizinkan_riwayat_pertama(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_panggol'),
            self.panggol_payload(),
        )

        self.assertEqual(response.status_code, 302)
        created = RiwayatPanggol.objects.get(no_sk='SK-PANGGOL-BARU')
        self.assertEqual(created.pegawai, self.employee)

    def test_reusable_panggol_menolak_kenaikan_sebelum_periodenya(self):
        self.create_panggol_document()
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_panggol'),
            self.panggol_payload(no_sk='SK-PANGGOL-DITOLAK'),
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            RiwayatPanggol.objects.filter(no_sk='SK-PANGGOL-DITOLAK').exists()
        )

    def test_reusable_update_panggol_mempertahankan_pemilik(self):
        document = self.create_panggol_document()
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_update_panggol', args=[document.pk]),
            self.panggol_payload(no_sk='SK-PANGGOL-DIUBAH'),
        )

        self.assertEqual(response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.no_sk, 'SK-PANGGOL-DIUBAH')
        self.assertEqual(document.pegawai, self.employee)

    def test_reusable_update_panggol_pegawai_lain_menghasilkan_404(self):
        document = self.create_panggol_document(employee=self.other_employee)
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse('riwayat_urls:riwayat_update_panggol', args=[document.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_reusable_delete_panggol_pegawai_lain_menghasilkan_404(self):
        document = self.create_panggol_document(employee=self.other_employee)
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_delete_panggol', args=[document.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(RiwayatPanggol.objects.filter(pk=document.pk).exists())

    def test_reusable_update_panggol_mewajibkan_login(self):
        document = self.create_panggol_document()

        response = self.client.get(
            reverse('riwayat_urls:riwayat_update_panggol', args=[document.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_pengurutan_panggol_hanya_admin_dan_mengikuti_nip(self):
        own_document = self.create_panggol_document()
        other_document = self.create_panggol_document(
            employee=self.other_employee,
            no_sk='SK-PANGGOL-LAIN',
        )
        url = reverse(
            'riwayat_urls:riwayat_panggol_urutkan',
            args=[self.panggol_document_type.pk],
        )

        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.document_admin)
        response = self.client.get(
            url,
            {'nip': self.other_employee.profil_user.nip},
        )

        self.assertEqual(response.status_code, 200)
        queryset_ids = set(
            response.context['urutkan_dokumen_form'].queryset.values_list(
                'pk',
                flat=True,
            )
        )
        self.assertEqual(queryset_ids, {other_document.pk})
        self.assertNotIn(own_document.pk, queryset_ids)

    def jabatan_payload(self, **overrides):
        payload = {
            'no_urut_dokumen': 0,
            'pegawai': self.other_employee.pk,
            'dokumen': self.jabatan_document_type.pk,
            'usulan': '',
            'unor': '',
            'bidang': '',
            'sub_bidang': '',
            'instalasi': '',
            'jns_jabatan': 'Pelaksana',
            'jenjang_jabatan': '',
            'nama_jabatan': self.nama_jabatan.pk,
            'detail_nama_jabatan': 'Pengelola Data',
            'tmt_jabatan': date.today().isoformat(),
            'tmt_pelantikan': '',
            'no_sk': 'SK-JABATAN-BARU',
            'tgl_sk': date.today().isoformat(),
            'no_srt_pemberhentian': '',
            'tgl_srt_pemberhentian': '',
        }
        payload.update(overrides)
        return payload

    def create_jabatan_document(self, employee=None, **overrides):
        values = {
            'pegawai': employee or self.employee,
            'dokumen': self.jabatan_document_type,
            'jns_jabatan': 'Pelaksana',
            'nama_jabatan': self.nama_jabatan,
            'detail_nama_jabatan': 'Pengelola Data',
            'tmt_jabatan': date.today(),
            'no_sk': 'SK-JABATAN-AWAL',
        }
        values.update(overrides)
        return RiwayatJabatan.objects.create(**values)

    def test_reusable_jabatan_membuat_data_untuk_pemilik(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_jabatan'),
            self.jabatan_payload(),
        )

        self.assertEqual(response.status_code, 302)
        created = RiwayatJabatan.objects.get(no_sk='SK-JABATAN-BARU')
        self.assertEqual(created.pegawai, self.employee)

    def test_filter_jabatan_admin_tidak_membuka_scope_pegawai_biasa(self):
        own_document = self.create_jabatan_document()
        other_document = self.create_jabatan_document(
            employee=self.other_employee,
            jns_jabatan='Fungsional',
            no_sk='SK-JABATAN-LAIN',
        )

        self.client.force_login(self.employee)
        employee_response = self.client.get(
            reverse('riwayat_urls:riwayat_jabatan'),
            {'jabatan': 'fungsional'},
        )
        employee_ids = set(
            employee_response.context['data'].values_list('pk', flat=True)
        )
        self.assertEqual(employee_ids, {own_document.pk})
        self.assertNotIn(other_document.pk, employee_ids)

        self.client.force_login(self.document_admin)
        admin_response = self.client.get(
            reverse('riwayat_urls:riwayat_jabatan'),
            {'jabatan': 'fungsional'},
        )
        admin_ids = set(
            admin_response.context['data'].values_list('pk', flat=True)
        )
        self.assertEqual(admin_ids, {other_document.pk})
        self.assertNotIn(own_document.pk, admin_ids)

    def test_reusable_update_delete_jabatan_membatasi_pemilik(self):
        other_document = self.create_jabatan_document(
            employee=self.other_employee,
        )
        self.client.force_login(self.employee)

        update_response = self.client.get(reverse(
            'riwayat_urls:riwayat_update_jabatan',
            args=[other_document.pk],
        ))
        delete_response = self.client.post(reverse(
            'riwayat_urls:riwayat_delete_jabatan',
            args=[other_document.pk],
        ))

        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(
            RiwayatJabatan.objects.filter(pk=other_document.pk).exists()
        )

    def test_pengurutan_jabatan_hanya_admin_dan_mengikuti_nip(self):
        own_document = self.create_jabatan_document()
        other_document = self.create_jabatan_document(
            employee=self.other_employee,
            no_sk='SK-JABATAN-LAIN',
        )
        url = reverse(
            'riwayat_urls:riwayat_jabatan_urutkan',
            args=[self.jabatan_document_type.pk],
        )

        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.document_admin)
        response = self.client.get(
            url,
            {'nip': self.other_employee.profil_user.nip},
        )
        queryset_ids = set(
            response.context['urutkan_dokumen_form'].queryset.values_list(
                'pk',
                flat=True,
            )
        )
        self.assertEqual(queryset_ids, {other_document.pk})
        self.assertNotIn(own_document.pk, queryset_ids)

    def pengangkatan_payload(self, **overrides):
        payload = {
            'pegawai': self.other_employee.pk,
            'dokumen': self.pengangkatan_document_type.pk,
            'status_pegawai': 'PNS',
            'no_srt_putusan': 'SK-PENGANGKATAN-BARU',
            'tgl_srt_putusan': date.today().isoformat(),
            'tmt_pegawai': date.today().isoformat(),
            'pejabat_pelantik': 'Direktur',
            'no_srt_spmt': '',
            'tgl_srt_spmt': '',
            'no_srt_latsar': '',
            'tgl_srt_latsar': '',
            'karpeg': '',
        }
        payload.update(overrides)
        return payload

    def create_pengangkatan_document(self, employee=None, **overrides):
        values = {
            'pegawai': employee or self.employee,
            'dokumen': self.pengangkatan_document_type,
            'status_pegawai': 'PNS',
            'no_srt_putusan': 'SK-PENGANGKATAN-AWAL',
            'tgl_srt_putusan': date.today(),
            'tmt_pegawai': date.today(),
        }
        values.update(overrides)
        return RiwayatPengangkatan.objects.create(**values)

    def test_reusable_pengangkatan_membuat_data_untuk_pemilik(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_pengangkatan'),
            self.pengangkatan_payload(),
        )

        self.assertEqual(response.status_code, 302)
        created = RiwayatPengangkatan.objects.get(
            no_srt_putusan='SK-PENGANGKATAN-BARU'
        )
        self.assertEqual(created.pegawai, self.employee)

    def test_reusable_update_delete_pengangkatan_membatasi_pemilik(self):
        other_document = self.create_pengangkatan_document(
            employee=self.other_employee,
        )
        self.client.force_login(self.employee)

        update_response = self.client.get(reverse(
            'riwayat_urls:riwayat_update_pengangkatan',
            args=[other_document.pk],
        ))
        delete_response = self.client.post(reverse(
            'riwayat_urls:riwayat_delete_pengangkatan',
            args=[other_document.pk],
        ))

        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(
            RiwayatPengangkatan.objects.filter(pk=other_document.pk).exists()
        )

    def test_pengurutan_pengangkatan_hanya_admin_dan_mengikuti_nip(self):
        own_document = self.create_pengangkatan_document()
        other_document = self.create_pengangkatan_document(
            employee=self.other_employee,
            no_srt_putusan='SK-PENGANGKATAN-LAIN',
        )
        url = reverse(
            'riwayat_urls:riwayat_pengangkatan_urutkan',
            args=[self.pengangkatan_document_type.pk],
        )

        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.document_admin)
        response = self.client.get(
            url,
            {'nip': self.other_employee.profil_user.nip},
        )
        queryset_ids = set(
            response.context['urutkan_dokumen_form'].queryset.values_list(
                'pk',
                flat=True,
            )
        )
        self.assertEqual(queryset_ids, {other_document.pk})
        self.assertNotIn(own_document.pk, queryset_ids)

    def penempatan_payload(self, **overrides):
        payload = {
            'pegawai': self.other_employee.pk,
            'dokumen': self.penempatan_document_type.pk,
            'penempatan_level1': self.unit_organisasi.pk,
            'penempatan_level2': '',
            'penempatan_level3': '',
            'penempatan_level4': '',
            'no_sk': 'SK-PENEMPATAN-BARU',
            'tgl_sk': date.today().isoformat(),
            'status': 'on',
        }
        payload.update(overrides)
        return payload

    def create_penempatan_document(self, employee=None, **overrides):
        values = {
            'pegawai': employee or self.employee,
            'dokumen': self.penempatan_document_type,
            'penempatan_level1': self.unit_organisasi,
            'no_sk': 'SK-PENEMPATAN-AWAL',
            'tgl_sk': date.today(),
            'status': True,
        }
        values.update(overrides)
        return RiwayatPenempatan.objects.create(**values)

    def test_reusable_penempatan_hanya_menyisakan_satu_status_aktif(self):
        old_document = self.create_penempatan_document()
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_penempatan'),
            self.penempatan_payload(),
        )

        self.assertEqual(response.status_code, 302)
        old_document.refresh_from_db()
        new_document = RiwayatPenempatan.objects.get(
            no_sk='SK-PENEMPATAN-BARU'
        )
        self.assertFalse(old_document.status)
        self.assertTrue(new_document.status)
        self.assertEqual(new_document.pegawai, self.employee)

    def test_penempatan_instansi_luar_reusable_nonaktif_dan_milik_user(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_penempatan_lainnya'),
            {
                'pegawai': self.other_employee.pk,
                'dokumen': self.penempatan_document_type.pk,
                'instansi_sebelumnya': 'Rumah Sakit Sebelumnya',
                'bidang_sebelumnya': 'Administrasi',
                'seksi_sebelumnya': '',
                'unit_sebelumnya': '',
                'no_sk': 'SK-PENEMPATAN-LUAR',
                'tgl_sk': date.today().isoformat(),
            },
        )

        self.assertEqual(response.status_code, 302)
        document = RiwayatPenempatan.objects.get(
            no_sk='SK-PENEMPATAN-LUAR'
        )
        self.assertEqual(document.pegawai, self.employee)
        self.assertFalse(document.status)

    def test_dua_update_penempatan_membatasi_pemilik(self):
        internal = self.create_penempatan_document(
            employee=self.other_employee,
        )
        external = self.create_penempatan_document(
            employee=self.other_employee,
            penempatan_level1=None,
            instansi_sebelumnya='Instansi Luar',
            no_sk='SK-PENEMPATAN-LUAR',
            status=False,
        )
        self.client.force_login(self.employee)

        internal_response = self.client.get(reverse(
            'riwayat_urls:riwayat_update_penempatan',
            args=[internal.pk],
        ))
        external_response = self.client.get(reverse(
            'riwayat_urls:riwayat_update_penempatan_lainnya',
            args=[external.pk],
        ))

        self.assertEqual(internal_response.status_code, 404)
        self.assertEqual(external_response.status_code, 404)

    def test_pengurutan_penempatan_hanya_admin_dan_mengikuti_nip(self):
        own_document = self.create_penempatan_document()
        other_document = self.create_penempatan_document(
            employee=self.other_employee,
            no_sk='SK-PENEMPATAN-LAIN',
        )
        url = reverse(
            'riwayat_urls:riwayat_penempatan_urutkan',
            args=[self.penempatan_document_type.pk],
        )

        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.document_admin)
        response = self.client.get(
            url,
            {'nip': self.other_employee.profil_user.nip},
        )
        queryset_ids = set(
            response.context['urutkan_dokumen_form'].queryset.values_list(
                'pk',
                flat=True,
            )
        )
        self.assertEqual(queryset_ids, {other_document.pk})
        self.assertNotIn(own_document.pk, queryset_ids)

    def berkala_payload(self, pangkat, penempatan, **overrides):
        payload = {
            'pegawai': self.other_employee.pk,
            'dokumen': self.berkala_document_type.pk,
            'no_srt_gaji': 'SK-BERKALA-BARU',
            'tgl_srt_gaji': date.today().isoformat(),
            'gaji_pkk': 5000000,
            'tmt_gaji': date.today().isoformat(),
            'pangkat': pangkat.pk,
            'tempat_kerja': penempatan.pk,
            'masa_kerja_tahun': 4,
            'masa_kerja_bulan': 0,
            'pertek': '',
            'ket': '',
        }
        payload.update(overrides)
        return payload

    def create_berkala_document(self, employee=None, **overrides):
        values = {
            'pegawai': employee or self.employee,
            'dokumen': self.berkala_document_type,
            'no_srt_gaji': 'SK-BERKALA-AWAL',
            'tgl_srt_gaji': date.today(),
            'gaji_pkk': 4500000,
            'tmt_gaji': date.today(),
            'masa_kerja_tahun': 2,
            'masa_kerja_bulan': 0,
        }
        values.update(overrides)
        return RiwayatGajiBerkala.objects.create(**values)

    def test_reusable_berkala_membuat_data_untuk_pemilik(self):
        pangkat = self.create_panggol_document()
        penempatan = self.create_penempatan_document()
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_berkala'),
            self.berkala_payload(pangkat, penempatan),
        )

        self.assertEqual(response.status_code, 302)
        document = RiwayatGajiBerkala.objects.get(
            no_srt_gaji='SK-BERKALA-BARU'
        )
        self.assertEqual(document.pegawai, self.employee)
        self.assertEqual(document.pangkat, pangkat)
        self.assertEqual(document.tempat_kerja, penempatan)

    def test_indikator_berkala_memakai_tmt_gaji_terbaru(self):
        latest_tmt = date.today() - relativedelta(months=22)
        self.create_berkala_document(tmt_gaji=latest_tmt)
        self.client.force_login(self.employee)

        response = self.client.get(reverse('riwayat_urls:riwayat_berkala'))

        self.assertTrue(response.context['status_berkala'])
        self.assertEqual(
            response.context['next_berkala'],
            latest_tmt + relativedelta(months=24),
        )

    def test_reusable_update_delete_berkala_membatasi_pemilik(self):
        other_document = self.create_berkala_document(
            employee=self.other_employee,
        )
        self.client.force_login(self.employee)

        update_response = self.client.get(reverse(
            'riwayat_urls:riwayat_update_berkala',
            args=[other_document.pk],
        ))
        delete_response = self.client.post(reverse(
            'riwayat_urls:riwayat_delete_berkala',
            args=[other_document.pk],
        ))

        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(
            RiwayatGajiBerkala.objects.filter(pk=other_document.pk).exists()
        )

    def test_pengurutan_berkala_hanya_admin_dan_mengikuti_nip(self):
        own_document = self.create_berkala_document()
        other_document = self.create_berkala_document(
            employee=self.other_employee,
            no_srt_gaji='SK-BERKALA-LAIN',
        )
        url = reverse(
            'riwayat_urls:riwayat_berkala_urutkan',
            args=[self.berkala_document_type.pk],
        )

        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.document_admin)
        response = self.client.get(
            url,
            {'nip': self.other_employee.profil_user.nip},
        )
        queryset_ids = set(
            response.context['urutkan_dokumen_form'].queryset.values_list(
                'pk',
                flat=True,
            )
        )
        self.assertEqual(queryset_ids, {other_document.pk})
        self.assertNotIn(own_document.pk, queryset_ids)

    def kinerja_payload(self, **overrides):
        payload = {
            'pegawai': self.other_employee.pk,
            'hasil_kinerja': 'sesuai',
            'prilaku_kinerja': 'sesuai',
            'kuadran_kinerja': self.predikat_kinerja.pk,
            'periode_kinerja_awal': '2025-01-01',
            'periode_kinerja_akhir': '2025-12-31',
            'nama_penilai': self.document_admin.pk,
        }
        payload.update(overrides)
        return payload

    def create_kinerja_document(self, employee=None, **overrides):
        values = {
            'pegawai': employee or self.employee,
            'dokumen': self.kinerja_document_type,
            'hasil_kinerja': 'sesuai',
            'prilaku_kinerja': 'sesuai',
            'kuadran_kinerja': self.predikat_kinerja,
            'periode_kinerja_awal': date(2025, 1, 1),
            'periode_kinerja_akhir': date(2025, 12, 31),
            'nama_penilai': self.document_admin,
        }
        values.update(overrides)
        return RiwayatKinerja.objects.create(**values)

    def test_reusable_kinerja_create_memaksa_pemilik_dan_dokumen(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_kinerja_create'),
            self.kinerja_payload(),
        )

        self.assertEqual(response.status_code, 302)
        document = RiwayatKinerja.objects.get(pegawai=self.employee)
        self.assertEqual(document.dokumen.url, 'kinerja')

    def test_reusable_kinerja_menolak_periode_terbalik(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_kinerja_create'),
            self.kinerja_payload(
                periode_kinerja_awal='2025-12-31',
                periode_kinerja_akhir='2025-01-01',
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(RiwayatKinerja.objects.filter(
            pegawai=self.employee,
        ).exists())

    def test_list_dan_mutasi_kinerja_membatasi_pemilik(self):
        own_document = self.create_kinerja_document()
        other_document = self.create_kinerja_document(
            employee=self.other_employee,
            periode_kinerja_awal=date(2024, 1, 1),
            periode_kinerja_akhir=date(2024, 12, 31),
        )
        self.client.force_login(self.employee)

        list_response = self.client.get(
            reverse('riwayat_urls:riwayat_kinerja')
        )
        list_ids = {item.pk for item in list_response.context['data']}
        update_response = self.client.get(reverse(
            'riwayat_urls:riwayat_update_kinerja',
            args=[other_document.pk],
        ))
        delete_response = self.client.post(reverse(
            'riwayat_urls:riwayat_delete_kinerja',
            args=[other_document.pk],
        ))

        self.assertEqual(list_ids, {own_document.pk})
        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)

    def test_popup_create_kinerja_tetap_didukung(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('riwayat_urls:riwayat_kinerja_create')
            + '?popup=1&field=id_kinerja_dua_thn',
            self.kinerja_payload(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            'riwayat_pendukung/popup_success.html',
        )
        self.assertTrue(RiwayatKinerja.objects.filter(
            pegawai=self.employee,
        ).exists())

    def test_pengurutan_kinerja_hanya_admin_dan_mengikuti_nip(self):
        own_document = self.create_kinerja_document()
        other_document = self.create_kinerja_document(
            employee=self.other_employee,
            periode_kinerja_awal=date(2024, 1, 1),
            periode_kinerja_akhir=date(2024, 12, 31),
        )
        url = reverse(
            'riwayat_urls:riwayat_kinerja_urutkan',
            args=[self.kinerja_document_type.pk],
        )

        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.document_admin)
        response = self.client.get(
            url,
            {'nip': self.other_employee.profil_user.nip},
        )
        queryset_ids = set(
            response.context['urutkan_dokumen_form'].queryset.values_list(
                'pk',
                flat=True,
            )
        )
        self.assertEqual(queryset_ids, {other_document.pk})
        self.assertNotIn(own_document.pk, queryset_ids)

    def test_admin_dokumen_dapat_melihat_dan_mengubah_dokumen_semua_pegawai(self):
        self.client.force_login(self.document_admin)

        list_response = self.client.get(
            reverse('riwayat_urls:riwayat_pendidikan')
        )
        update_response = self.client.get(
            reverse(
                'riwayat_urls:riwayat_update_pendidikan',
                args=[self.other_document.pk],
            )
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, self.own_document.pendidikan)
        self.assertContains(list_response, self.other_document.pendidikan)
        self.assertEqual(update_response.status_code, 200)
        self.assertIn('is_verifikasi', update_response.context['form'].fields)

    def test_dashboard_admin_dokumen_dibatasi_berdasarkan_peran(self):
        self.client.force_login(self.employee)
        forbidden = self.client.get(
            reverse('riwayat_urls:document_admin_dashboard')
        )
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_login(self.document_admin)
        allowed = self.client.get(
            reverse('riwayat_urls:document_admin_dashboard')
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, self.other_employee.email)

    def test_pengurutan_dokumen_hanya_untuk_admin_dokumen(self):
        url = reverse(
            'riwayat_urls:riwayat_pendidikan_urutkan',
            args=[self.document_type.pk],
        )
        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.document_admin)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_api_dokumen_mewajibkan_login(self):
        response = self.client.get(reverse('riwayat_urls:api_pendidikan'))

        self.assertIn(response.status_code, (401, 403))

    def test_api_pegawai_hanya_mengembalikan_dokumen_sendiri(self):
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse('riwayat_urls:api_pendidikan'),
            {'nip': self.other_employee.profil_user.nip},
        )

        self.assertEqual(response.status_code, 200)
        employee_ids = {item['pegawai'] for item in response.json()}
        self.assertEqual(employee_ids, {self.employee.pk})

    def test_api_admin_dokumen_dapat_memfilter_nip(self):
        self.client.force_login(self.document_admin)

        response = self.client.get(
            reverse('riwayat_urls:api_pendidikan'),
            {'nip': self.other_employee.profil_user.nip},
        )

        self.assertEqual(response.status_code, 200)
        employee_ids = {item['pegawai'] for item in response.json()}
        self.assertEqual(employee_ids, {self.other_employee.pk})

    def test_card_data_pegawai_tampil_pada_halaman_dokumen_sendiri(self):
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse('riwayat_urls:riwayat_pendidikan')
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Data Pegawai')
        self.assertContains(response, self.employee.full_name)
        self.assertContains(response, self.employee.profil_user.nip)
        self.assertNotContains(response, 'Kembali ke Dashboard Admin')

    def test_card_data_pegawai_admin_mengikuti_nip_yang_dipilih(self):
        self.client.force_login(self.document_admin)

        response = self.client.get(
            reverse('riwayat_urls:riwayat_pendidikan'),
            {'nip': self.other_employee.profil_user.nip},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Data Pegawai')
        self.assertContains(response, self.other_employee.full_name)
        self.assertContains(response, self.other_employee.profil_user.nip)
        self.assertContains(response, 'Kembali ke Dashboard Admin')
