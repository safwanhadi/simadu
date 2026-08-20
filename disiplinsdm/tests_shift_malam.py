from datetime import date, datetime, time

from django.test import TestCase
from django.utils import timezone

from myaccount.models import Users
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
    ApprovedJadwalDinasSDM,
    DetailKategoriJadwalDinas,
    JenisSDMPerinstalasi,
    KategoriJadwalDinas,
    LogAktivitasAbsen,
    LogKehadiran,
    MappingMesinAbsensi,
)
from .services import NewAttendanceMappingService, NewAttendanceOrchestrator


class OvernightShiftAttendanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.employee = Users.objects.create_user(
            email='pegawai-shift-malam@example.com',
            first_name='Pegawai',
            last_name='Shift Malam',
        )
        cls.mapping = MappingMesinAbsensi.objects.create(
            mesin_id='SHIFT-MALAM-001',
            pegawai=cls.employee,
        )
        instansi = InstansiDaerah.objects.create(instansi='Instansi Shift')
        satker = SatuanKerjaInduk.objects.create(
            instansi_daerah=instansi,
            satuan_kerja='Satker Shift',
        )
        cls.unor = UnitOrganisasi.objects.create(
            satker_induk=satker,
            unor='Unor Shift',
        )
        cls.bidang = Bidang.objects.create(unor=cls.unor, bidang='Bidang Shift')
        cls.sub_bidang = SubBidang.objects.create(
            bidang=cls.bidang,
            sub_bidang='Subbidang Shift',
        )
        cls.instalasi = UnitInstalasi.objects.create(
            sub_bidang=cls.sub_bidang,
            instalasi='Instalasi Shift',
        )
        cls.metadata = JenisSDMPerinstalasi.objects.create(
            pegawai=cls.employee,
            unor=cls.unor,
            bidang=cls.bidang,
            sub_bidang=cls.sub_bidang,
            instalasi=cls.instalasi,
            bulan=7,
            tahun=2026,
            status='disetujui',
        )
        kategori_libur = KategoriJadwalDinas.objects.create(
            kategori_dinas='Libur',
        )
        lepas_piket = DetailKategoriJadwalDinas.objects.create(
            kategori_dinas=kategori_libur,
            hari='Senin s/d kamis',
            kategori_jadwal='Lepas Piket',
        )
        ApprovedJadwalDinasSDM.objects.create(
            pegawai=cls.metadata,
            tanggal=date(2026, 7, 6),
            kategori_jadwal=lepas_piket,
            is_approved=True,
        )

    def setUp(self):
        self.checkout_time = timezone.make_aware(datetime(2026, 7, 6, 10, 5))
        self.parent_malam = AbsensiHarian.objects.create(
            pegawai=self.employee,
            tanggal=date(2026, 7, 5),
            unor=self.unor,
            bidang=self.bidang,
            sub_bidang=self.sub_bidang,
            instalasi=self.instalasi,
            status_final='HADIR',
        )
        self.parent_lepas = AbsensiHarian.objects.create(
            pegawai=self.employee,
            tanggal=date(2026, 7, 6),
            unor=self.unor,
            bidang=self.bidang,
            sub_bidang=self.sub_bidang,
            instalasi=self.instalasi,
            status_final='',
        )
        LogKehadiran.objects.create(
            mapping=self.mapping,
            datetime=self.checkout_time,
            direction='OUT',
            devicename='Mesin Fingerprint',
            personname='Pegawai Shift Malam',
        )
        LogAktivitasAbsen.objects.create(
            absensi_harian=self.parent_malam,
            tipe='PULANG',
            waktu=self.checkout_time,
            status_ketepatan='Tepat Waktu',
            devicename='Mesin Fingerprint',
        )

    def test_log_pulang_yang_sudah_dipindah_tidak_dibuat_ulang(self):
        success, _message = NewAttendanceMappingService.process_logs_batch(
            date(2026, 7, 6),
            [self.employee.pk],
        )

        self.assertTrue(success)
        self.assertEqual(
            LogAktivitasAbsen.objects.filter(
                absensi_harian__pegawai=self.employee,
                waktu=self.checkout_time,
            ).count(),
            1,
        )
        self.assertFalse(self.parent_lepas.logs.exists())

    def test_lepas_piket_tetap_libur_setelah_penilaian(self):
        LogAktivitasAbsen.objects.create(
            absensi_harian=self.parent_lepas,
            tipe='PULANG',
            waktu=self.checkout_time,
            status_ketepatan='Luar Jadwal',
            devicename='Mesin Fingerprint',
        )
        self.parent_lepas.status_final = 'HADIR'
        self.parent_lepas.keterangan = (
            'Sistem: Hadir berdasarkan log presensi yang telah direkonsiliasi.'
        )
        self.parent_lepas.save(update_fields=('status_final', 'keterangan'))

        success, _message = NewAttendanceOrchestrator.execute_by_structure(
            date(2026, 7, 6),
            instalasi_id=self.instalasi.pk,
            is_final_stage=True,
        )

        self.assertTrue(success)
        self.parent_lepas.refresh_from_db()
        self.assertEqual(self.parent_lepas.status_final, 'LIBUR')
        self.assertFalse(self.parent_lepas.logs.exists())
