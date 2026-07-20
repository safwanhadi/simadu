from datetime import date, timedelta
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from dokumen.models import (
    Kompetensi,
    RiwayatJabatan,
    RiwayatPenempatan,
    RiwayatProfesi,
)
from jenissdm.models import JenisSDM, ListKompetensi
from myaccount.models import Users
from strukturorg.models import (
    Bidang,
    InstansiDaerah,
    SatuanKerjaInduk,
    StandarInstalasi,
    SubBidang,
    UnitInstalasi,
    UnitOrganisasi,
)

from .services import (
    STATUS_DIATAS,
    STATUS_SESUAI,
    STATUS_TIDAK_MEMENUHI,
    employees_for_jabatan,
    installation_groups,
    installation_standard_data,
    jabatan_cards,
    workforce_summary,
)


class DashboardWorkforceServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        instansi = InstansiDaerah.objects.create(instansi='RS Uji')
        satker = SatuanKerjaInduk.objects.create(
            instansi_daerah=instansi,
            satuan_kerja='Satker Uji',
        )
        unor = UnitOrganisasi.objects.create(
            satker_induk=satker,
            unor='Unit Organisasi Uji',
        )
        bidang = Bidang.objects.create(unor=unor, bidang='Bidang Uji')
        sub_bidang = SubBidang.objects.create(
            bidang=bidang,
            sub_bidang='Subbidang Uji',
        )
        cls.installation = UnitInstalasi.objects.create(
            sub_bidang=sub_bidang,
            instalasi='Instalasi Uji',
        )
        cls.other_installation = UnitInstalasi.objects.create(
            sub_bidang=sub_bidang,
            instalasi='Instalasi Uji Lain',
        )
        cls.profession = JenisSDM.objects.create(jenis_sdm='Profesi Uji')

    @classmethod
    def create_user(
        cls,
        email,
        *,
        active=True,
        placement=True,
        profession=True,
        jabatan=True,
    ):
        user = Users.objects.create_user(
            email=email,
            first_name='Pegawai',
            last_name=email.split('@')[0],
            password='Dashboard-Test-123!',
            is_active=active,
        )
        if placement:
            RiwayatPenempatan.objects.create(
                pegawai=user,
                penempatan_level4=cls.installation,
                status=True,
            )
        if profession:
            RiwayatProfesi.objects.create(
                pegawai=user,
                profesi=cls.profession,
            )
        if jabatan:
            RiwayatJabatan.objects.create(
                pegawai=user,
                nama_jabatan=cls.profession,
                tmt_jabatan=date(2024, 1, 1),
            )
        return user

    def test_card_dan_detail_memakai_filter_pegawai_yang_sama(self):
        eligible = self.create_user('eligible@example.com')
        # Riwayat profesi ganda tidak memengaruhi card jabatan.
        RiwayatProfesi.objects.create(
            pegawai=eligible,
            profesi=self.profession,
        )
        self.create_user('inactive@example.com', active=False)
        without_placement = self.create_user(
            'no-placement@example.com',
            placement=False,
        )
        self.create_user(
            'no-profession@example.com',
            profession=False,
            jabatan=False,
        )

        card = jabatan_cards().get(pk=self.profession.pk)
        detail_ids = list(
            employees_for_jabatan(self.profession.pk)
            .values_list('pk', flat=True)
        )

        self.assertEqual(card.jumlah, 2)
        self.assertEqual(detail_ids, [eligible.pk, without_placement.pk])

        summary = workforce_summary()
        self.assertEqual(summary['total_active'], 3)
        self.assertEqual(summary['without_active_placement'], 1)
        self.assertEqual(summary['without_jabatan'], 1)

        self.client.force_login(eligible)
        response = self.client.get(
            reverse(
                'dashboard_urls:dashboard_sdm_view',
                kwargs={'sdm': self.profession.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, eligible.full_name)
        self.assertContains(response, without_placement.full_name)
        self.assertNotContains(response, 'Pegawai inactive')

    def test_card_dan_detail_hanya_memakai_jabatan_dengan_tmt_terakhir(self):
        employee = self.create_user('latest-position@example.com')
        latest_jabatan = JenisSDM.objects.create(jenis_sdm='Jabatan Terbaru')
        RiwayatJabatan.objects.create(
            pegawai=employee,
            nama_jabatan=latest_jabatan,
            tmt_jabatan=date(2025, 1, 1),
        )
        future_jabatan = JenisSDM.objects.create(jenis_sdm='Jabatan Mendatang')
        RiwayatJabatan.objects.create(
            pegawai=employee,
            nama_jabatan=future_jabatan,
            tmt_jabatan=date.today() + timedelta(days=365),
        )

        cards = jabatan_cards()
        self.assertFalse(cards.filter(pk=self.profession.pk).exists())
        self.assertEqual(cards.get(pk=latest_jabatan.pk).jumlah, 1)
        self.assertFalse(cards.filter(pk=future_jabatan.pk).exists())
        self.assertNotIn(
            employee.pk,
            employees_for_jabatan(self.profession.pk).values_list(
                'pk', flat=True,
            ),
        )
        self.assertIn(
            employee.pk,
            employees_for_jabatan(latest_jabatan.pk).values_list(
                'pk', flat=True,
            ),
        )

    def test_export_excel_memuat_ringkasan_dan_daftar_profesi(self):
        admin = self.create_user('dashboard-admin@example.com')
        admin.is_staff = True
        admin.save(update_fields=['is_staff'])
        self.client.force_login(admin)

        response = self.client.get(
            reverse('dashboard_urls:export_workforce_profession')
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        workbook = load_workbook(BytesIO(response.content), read_only=True)
        worksheet = workbook['Ringkasan SDM']
        self.assertEqual(worksheet['A3'].value, 'Total SDM aktif')
        self.assertEqual(worksheet['B3'].value, 1)
        self.assertEqual(worksheet['B8'].value, self.profession.jenis_sdm)
        self.assertEqual(worksheet['D8'].value, 1)
        self.assertEqual(worksheet['A9'].value, 'TOTAL TERHITUNG')
        self.assertEqual(worksheet['D9'].value, 1)

    def test_kompetensi_dengan_masa_berlaku_harus_belum_kedaluwarsa(self):
        user = self.create_user('competency@example.com')
        competency_type = ListKompetensi.objects.create(
            jenis_sdm=self.profession,
            kompetensi='Kompetensi Wajib Uji',
        )
        standard = StandarInstalasi.objects.create(
            instalasi=self.installation,
            jenis_sdm=self.profession,
        )
        standard.kompetensi_wajib.add(competency_type)
        competency = Kompetensi.objects.create(
            pegawai=user,
            kompetensi=competency_type,
            no_sert_komp='KOMP-001',
            masa_berlaku=12,
            berlaku_sd=date.today() + timedelta(days=30),
        )

        result = installation_standard_data(self.installation)
        self.assertEqual(result['status'], STATUS_SESUAI)
        self.assertEqual(result['users'][0].status_kompetensi, STATUS_SESUAI)

        competency.berlaku_sd = date.today() - timedelta(days=1)
        competency.save(update_fields=['berlaku_sd'])

        expired_result = installation_standard_data(self.installation)
        self.assertEqual(expired_result['status'], STATUS_TIDAK_MEMENUHI)
        self.assertEqual(
            expired_result['users'][0].status_kompetensi,
            STATUS_TIDAK_MEMENUHI,
        )
        self.assertEqual(expired_result['users'][0].kompetensi_display, [])

    def test_kompetensi_tanpa_masa_berlaku_tetap_diakui(self):
        user = self.create_user('unlimited@example.com')
        competency_type = ListKompetensi.objects.create(
            jenis_sdm=self.profession,
            kompetensi='Kompetensi Tanpa Batas Uji',
        )
        standard = StandarInstalasi.objects.create(
            instalasi=self.installation,
            jenis_sdm=self.profession,
        )
        standard.kompetensi_wajib.add(competency_type)
        Kompetensi.objects.create(
            pegawai=user,
            kompetensi=competency_type,
            no_sert_komp='KOMP-002',
            masa_berlaku=None,
            # Tanggal lama diabaikan karena kompetensi ditandai tanpa masa berlaku.
            berlaku_sd=date.today() - timedelta(days=365),
        )

        result = installation_standard_data(self.installation)

        self.assertEqual(result['status'], STATUS_SESUAI)
        self.assertEqual(result['users'][0].status_kompetensi, STATUS_SESUAI)

    def test_standar_memakai_penempatan_aktif_paling_baru(self):
        user = self.create_user('multiple-placement@example.com')
        StandarInstalasi.objects.create(
            instalasi=self.installation,
            jenis_sdm=self.profession,
        )
        StandarInstalasi.objects.create(
            instalasi=self.other_installation,
            jenis_sdm=self.profession,
        )
        RiwayatPenempatan.objects.create(
            pegawai=user,
            penempatan_level4=self.other_installation,
            status=True,
        )

        old_result = installation_standard_data(self.installation)
        current_result = installation_standard_data(self.other_installation)

        self.assertEqual(old_result['users'], [])
        self.assertEqual([item.pk for item in current_result['users']], [user.pk])
        self.assertEqual(current_result['status'], STATUS_SESUAI)

    def test_unit_dengan_slug_sama_dinilai_sebagai_satu_instalasi(self):
        duplicate_installation = UnitInstalasi.objects.create(
            sub_bidang=self.installation.sub_bidang,
            instalasi=self.installation.instalasi,
        )
        user = self.create_user('grouped-installation@example.com')
        RiwayatPenempatan.objects.create(
            pegawai=user,
            penempatan_level4=duplicate_installation,
            status=True,
        )
        StandarInstalasi.objects.create(
            instalasi=self.installation,
            jenis_sdm=self.profession,
        )

        group = next(
            item
            for item in installation_groups()
            if item['slug'] == self.installation.slug
        )
        result = installation_standard_data(group)

        self.assertEqual(
            set(group['installation_ids']),
            {self.installation.pk, duplicate_installation.pk},
        )
        self.assertEqual([item.pk for item in result['users']], [user.pk])
        self.assertEqual(result['status'], STATUS_SESUAI)

    def test_standar_instalasi_mencocokkan_kompetensi_per_profesi(self):
        other_profession = JenisSDM.objects.create(jenis_sdm='Profesi Uji Lain')
        competency_a = ListKompetensi.objects.create(
            jenis_sdm=self.profession,
            kompetensi='Kompetensi Profesi A',
        )
        competency_b = ListKompetensi.objects.create(
            jenis_sdm=other_profession,
            kompetensi='Kompetensi Profesi B',
        )
        standard_a = StandarInstalasi.objects.create(
            instalasi=self.installation,
            jenis_sdm=self.profession,
        )
        standard_b = StandarInstalasi.objects.create(
            instalasi=self.installation,
            jenis_sdm=other_profession,
        )
        standard_a.kompetensi_wajib.add(competency_a)
        standard_b.kompetensi_wajib.add(competency_b)

        user_a = self.create_user('profession-a@example.com')
        user_b = self.create_user('profession-b@example.com', profession=False)
        RiwayatProfesi.objects.create(pegawai=user_b, profesi=other_profession)
        Kompetensi.objects.create(
            pegawai=user_a,
            kompetensi=competency_a,
            no_sert_komp='PROF-A',
            masa_berlaku=None,
            berlaku_sd=date.today(),
        )
        Kompetensi.objects.create(
            pegawai=user_b,
            kompetensi=competency_b,
            no_sert_komp='PROF-B',
            masa_berlaku=None,
            berlaku_sd=date.today(),
        )

        result = installation_standard_data(self.installation)

        self.assertEqual(result['status'], STATUS_SESUAI)
        self.assertEqual(
            {user.status_kompetensi for user in result['users']},
            {STATUS_SESUAI},
        )

    def test_satu_kompetensi_pendukung_membuat_instalasi_diatas_standar(self):
        required = ListKompetensi.objects.create(
            jenis_sdm=self.profession,
            kompetensi='Kompetensi Wajib Agregasi',
        )
        supporting = ListKompetensi.objects.create(
            jenis_sdm=self.profession,
            kompetensi='Kompetensi Pendukung Agregasi',
        )
        standard = StandarInstalasi.objects.create(
            instalasi=self.installation,
            jenis_sdm=self.profession,
        )
        standard.kompetensi_wajib.add(required)
        standard.kompetensi_pendukung.add(supporting)

        user_regular = self.create_user('standard-regular@example.com')
        user_supporting = self.create_user('standard-supporting@example.com')
        for user, competency_type, certificate in (
            (user_regular, required, 'WAJIB-1'),
            (user_supporting, required, 'WAJIB-2'),
            (user_supporting, supporting, 'PENDUKUNG-1'),
        ):
            Kompetensi.objects.create(
                pegawai=user,
                kompetensi=competency_type,
                no_sert_komp=certificate,
                masa_berlaku=None,
                berlaku_sd=date.today(),
            )

        result = installation_standard_data(self.installation)

        self.assertEqual(result['status'], STATUS_DIATAS)
        statuses = {
            user.email: user.status_kompetensi
            for user in result['users']
        }
        self.assertEqual(statuses[user_regular.email], STATUS_SESUAI)
        self.assertEqual(statuses[user_supporting.email], STATUS_DIATAS)
