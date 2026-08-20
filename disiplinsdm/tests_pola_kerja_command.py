from datetime import date, time
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from myaccount.models import Users

from .models import (
    ApprovedJadwalDinasSDM,
    DetailKategoriJadwalDinas,
    JenisSDMPerinstalasi,
    KategoriJadwalDinas,
    PolaKerjaPegawai,
)


class InisialisasiPolaKerjaCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pegawai = Users.objects.create_user(
            email='inisialisasi-pola@example.com',
            first_name='Inisialisasi',
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
        juni = JenisSDMPerinstalasi.objects.create(
            pegawai=cls.pegawai,
            bulan=6,
            tahun=2026,
            status='disetujui',
        )
        juli = JenisSDMPerinstalasi.objects.create(
            pegawai=cls.pegawai,
            bulan=7,
            tahun=2026,
            status='disetujui',
        )
        ApprovedJadwalDinasSDM.objects.create(
            pegawai=juni,
            tanggal=date(2026, 6, 20),
            kategori_jadwal=cls.reguler,
            is_approved=True,
        )
        ApprovedJadwalDinasSDM.objects.create(
            pegawai=juli,
            tanggal=date(2026, 7, 20),
            kategori_jadwal=cls.piket,
            is_approved=True,
        )

    def test_dry_run_tidak_menyimpan_data(self):
        output = StringIO()
        call_command('inisialisasi_pola_kerja', stdout=output)

        self.assertFalse(PolaKerjaPegawai.objects.exists())
        self.assertIn('Shift=1', output.getvalue())
        self.assertIn('Tidak ada data yang disimpan', output.getvalue())

    def test_apply_memakai_bulan_jadwal_disetujui_terakhir(self):
        call_command('inisialisasi_pola_kerja', '--apply', stdout=StringIO())

        pola = PolaKerjaPegawai.objects.get(pegawai=self.pegawai)
        self.assertEqual(pola.pola_kerja, PolaKerjaPegawai.SHIFT)
        self.assertEqual(pola.berlaku_mulai, date(2026, 7, 1))

    def test_apply_tidak_menimpa_pola_yang_sudah_ada(self):
        existing = PolaKerjaPegawai.objects.create(
            pegawai=self.pegawai,
            pola_kerja=PolaKerjaPegawai.REGULER,
            berlaku_mulai=date(2026, 1, 1),
        )

        call_command('inisialisasi_pola_kerja', '--apply', stdout=StringIO())

        self.assertEqual(PolaKerjaPegawai.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.pola_kerja, PolaKerjaPegawai.REGULER)

    def test_apply_mengabaikan_pegawai_nonaktif(self):
        self.pegawai.is_active = False
        self.pegawai.save(update_fields=['is_active'])

        call_command('inisialisasi_pola_kerja', '--apply', stdout=StringIO())

        self.assertFalse(PolaKerjaPegawai.objects.exists())

    def test_bersihkan_nonaktif_dry_run_tidak_menghapus(self):
        self.pegawai.is_active = False
        self.pegawai.save(update_fields=['is_active'])
        pola = PolaKerjaPegawai.objects.create(
            pegawai=self.pegawai,
            pola_kerja=PolaKerjaPegawai.SHIFT,
            berlaku_mulai=date(2026, 7, 1),
            keterangan=(
                'Inisialisasi otomatis dari jadwal dinas disetujui terakhir.'
            ),
        )

        output = StringIO()
        call_command(
            'inisialisasi_pola_kerja',
            '--bersihkan-nonaktif',
            stdout=output,
        )

        self.assertTrue(PolaKerjaPegawai.objects.filter(pk=pola.pk).exists())
        self.assertIn('pegawai nonaktif=1', output.getvalue())

    def test_bersihkan_nonaktif_hanya_menghapus_hasil_inisialisasi(self):
        self.pegawai.is_active = False
        self.pegawai.save(update_fields=['is_active'])
        hasil_inisialisasi = PolaKerjaPegawai.objects.create(
            pegawai=self.pegawai,
            pola_kerja=PolaKerjaPegawai.SHIFT,
            berlaku_mulai=date(2026, 7, 1),
            keterangan=(
                'Inisialisasi otomatis dari jadwal dinas disetujui terakhir.'
            ),
        )
        pegawai_lain = Users.objects.create_user(
            email='pola-manual-nonaktif@example.com',
            is_active=False,
        )
        pola_manual = PolaKerjaPegawai.objects.create(
            pegawai=pegawai_lain,
            pola_kerja=PolaKerjaPegawai.REGULER,
            berlaku_mulai=date(2026, 1, 1),
            keterangan='Input manual admin cuti.',
        )

        call_command(
            'inisialisasi_pola_kerja',
            '--bersihkan-nonaktif',
            '--apply',
            stdout=StringIO(),
        )

        self.assertFalse(
            PolaKerjaPegawai.objects.filter(pk=hasil_inisialisasi.pk).exists()
        )
        self.assertTrue(
            PolaKerjaPegawai.objects.filter(pk=pola_manual.pk).exists()
        )
