from datetime import date, datetime, time, timedelta
from io import BytesIO

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from myaccount.models import AdminScopeAssignment, ProfilSDM, Users
from myaccount.roles import ADMIN_DISIPLIN
from strukturorg.models import (
    Bidang,
    InstansiDaerah,
    SatuanKerjaInduk,
    SubBidang,
    UnitInstalasi,
    UnitOrganisasi,
)

from .models import (
    AbsensiHarian,
    LogAktivitasAbsen,
    LogKehadiran,
    MappingMesinAbsensi,
)


class RawPresensiDatabaseViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        group, _ = Group.objects.get_or_create(name=ADMIN_DISIPLIN)
        cls.admin = Users.objects.create_user(
            email='admin-data-mentah@example.com',
            first_name='Admin',
            last_name='Presensi',
            password='Password-123!',
        )
        cls.admin.groups.add(group)
        AdminScopeAssignment.objects.create(
            user=cls.admin,
            group=group,
            scope_type=AdminScopeAssignment.GLOBAL,
        )
        cls.non_admin = Users.objects.create_user(
            email='non-admin-data-mentah@example.com',
            first_name='Non',
            last_name='Admin',
            password='Password-123!',
        )
        cls.pegawai = Users.objects.create_user(
            email='pegawai-data-mentah@example.com',
            first_name='Pegawai',
            last_name='Mentah',
            password='Password-123!',
        )
        ProfilSDM.objects.create(
            user=cls.pegawai,
            nip='199900001111',
            no_hp='081200000001',
            email_pribadi=cls.pegawai.email,
        )
        cls.mapping = MappingMesinAbsensi.objects.create(
            mesin_id='MESIN-001',
            pegawai=cls.pegawai,
        )

        instansi = InstansiDaerah.objects.create(instansi='Instansi Raw')
        satker = SatuanKerjaInduk.objects.create(
            instansi_daerah=instansi,
            satuan_kerja='Satker Raw',
        )
        unor = UnitOrganisasi.objects.create(
            satker_induk=satker,
            unor='Unor Raw',
        )
        bidang = Bidang.objects.create(unor=unor, bidang='Bidang Raw')
        sub_bidang = SubBidang.objects.create(
            bidang=bidang,
            sub_bidang='Subbidang Raw',
        )
        instalasi = UnitInstalasi.objects.create(
            sub_bidang=sub_bidang,
            instalasi='Instalasi Raw',
        )

        today = date.today()
        cls.raw_time = datetime.combine(today, time(7, 15))
        cls.raw_log = LogKehadiran.objects.create(
            mapping=cls.mapping,
            datetime=cls.raw_time,
            direction='IN',
            devicename='DEVICE-A',
            personname='NAMA MENTAH MESIN',
        )
        absensi = AbsensiHarian.objects.create(
            pegawai=cls.pegawai,
            tanggal=today,
            unor=unor,
            bidang=bidang,
            sub_bidang=sub_bidang,
            instalasi=instalasi,
            status_final='HADIR',
        )
        LogAktivitasAbsen.objects.create(
            absensi_harian=absensi,
            tipe='DATANG',
            waktu=cls.raw_time,
        )
        LogKehadiran.objects.create(
            mapping=cls.mapping,
            datetime=cls.raw_time + timedelta(hours=9),
            direction='OUT',
            devicename='DEVICE-B',
            personname='NAMA MENTAH MESIN',
        )

    def test_admin_dapat_melihat_field_data_mentah(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('disiplinsdm_urls:raw_presensi_database')
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NAMA MENTAH MESIN')
        self.assertContains(response, 'MESIN-001')
        self.assertContains(response, 'DEVICE-A')
        self.assertContains(response, '199900001111')
        self.assertContains(response, 'Sudah diolah')

    def test_filter_perangkat_arah_dan_status_pengolahan(self):
        self.client.force_login(self.admin)
        today = date.today().isoformat()

        response = self.client.get(
            reverse('disiplinsdm_urls:raw_presensi_database'),
            {
                'date_from': today,
                'date_to': today,
                'device': 'DEVICE-B',
                'direction': 'OUT',
                'evaluation': 'belum',
            },
        )

        self.assertEqual(response.status_code, 200)
        rows = list(response.context['raw_logs'])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].devicename, 'DEVICE-B')
        self.assertFalse(rows[0].is_evaluated)

    def test_non_admin_disiplin_ditolak(self):
        self.client.force_login(self.non_admin)

        response = self.client.get(
            reverse('disiplinsdm_urls:raw_presensi_database')
        )

        self.assertEqual(response.status_code, 403)

    def test_export_excel_mengikuti_filter_aktif(self):
        self.client.force_login(self.admin)
        today = date.today().isoformat()

        response = self.client.get(
            reverse('disiplinsdm_urls:raw_presensi_database'),
            {
                'date_from': today,
                'date_to': today,
                'device': 'DEVICE-B',
                'direction': 'OUT',
                'evaluation': 'belum',
                'export': 'excel',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        workbook = load_workbook(BytesIO(b''.join(response.streaming_content)))
        worksheet = workbook['Data Mentah Presensi']
        self.assertEqual(worksheet['I5'].value, 'DEVICE-B')
        self.assertEqual(worksheet['H5'].value, 'OUT')
        self.assertEqual(worksheet['J5'].value, 'Belum diolah')
        self.assertIsNone(worksheet['A6'].value)
