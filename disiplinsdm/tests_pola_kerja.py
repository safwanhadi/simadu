from datetime import date, time

from django.test import TestCase

from myaccount.models import Users

from .models import (
    ApprovedJadwalDinasSDM,
    DetailKategoriJadwalDinas,
    JenisSDMPerinstalasi,
    KategoriJadwalDinas,
    PolaKerjaPegawai,
)
from .pola_kerja import sinkronkan_pola_kerja_dari_jadwal


class SinkronisasiPolaKerjaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pegawai = Users.objects.create_user(
            email='sinkron-pola@example.com',
            first_name='Sinkron',
            last_name='Pola',
        )
        reguler = KategoriJadwalDinas.objects.create(kategori_dinas='Reguler')
        piket = KategoriJadwalDinas.objects.create(kategori_dinas='Piket')
        cls.reguler = DetailKategoriJadwalDinas.objects.create(
            kategori_dinas=reguler,
            hari='Senin s/d kamis',
            kategori_jadwal='Pagi',
            waktu_datang=time(7),
            waktu_pulang=time(14),
        )
        cls.piket = DetailKategoriJadwalDinas.objects.create(
            kategori_dinas=piket,
            hari='Senin s/d kamis',
            kategori_jadwal='Malam',
            waktu_datang=time(20),
            waktu_pulang=time(8),
        )

    def buat_jadwal(self, bulan, kategori):
        metadata = JenisSDMPerinstalasi.objects.create(
            pegawai=self.pegawai,
            bulan=bulan,
            tahun=2026,
            status='disetujui',
        )
        ApprovedJadwalDinasSDM.objects.create(
            pegawai=metadata,
            tanggal=date(2026, bulan, 2),
            kategori_jadwal=kategori,
            is_approved=True,
        )
        return metadata

    def test_perubahan_shift_ke_reguler_membentuk_riwayat(self):
        juni = self.buat_jadwal(6, self.piket)
        sinkronkan_pola_kerja_dari_jadwal(juni)
        juli = self.buat_jadwal(7, self.reguler)
        sinkronkan_pola_kerja_dari_jadwal(juli)

        riwayat = list(PolaKerjaPegawai.objects.filter(
            pegawai=self.pegawai,
        ).order_by('berlaku_mulai'))
        self.assertEqual(len(riwayat), 2)
        self.assertEqual(riwayat[0].pola_kerja, PolaKerjaPegawai.SHIFT)
        self.assertEqual(riwayat[0].berlaku_mulai, date(2026, 6, 1))
        self.assertEqual(riwayat[0].berlaku_sampai, date(2026, 6, 30))
        self.assertEqual(riwayat[1].pola_kerja, PolaKerjaPegawai.REGULER)
        self.assertEqual(riwayat[1].berlaku_mulai, date(2026, 7, 1))
        self.assertIsNone(riwayat[1].berlaku_sampai)

    def test_persetujuan_ulang_pola_sama_tidak_membuat_duplikat(self):
        juni = self.buat_jadwal(6, self.piket)
        sinkronkan_pola_kerja_dari_jadwal(juni)
        sinkronkan_pola_kerja_dari_jadwal(juni)

        self.assertEqual(
            PolaKerjaPegawai.objects.filter(pegawai=self.pegawai).count(),
            1,
        )
