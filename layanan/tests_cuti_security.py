from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from dokumen.models import KlaimCutiTunda, RiwayatCuti
from myaccount.models import AdminScopeAssignment, Users
from myaccount.roles import ADMIN_LAYANAN_CUTI

from .forms import Verifikator2CutiForm, Verifikator3CutiForm
from .models import (
    JenisLayanan, LayananCuti, PelimpahanTugas, PengalihanPelimpahanTugas,
    PerubahanJadwalCuti,
    PemutihanCutiLog, VerifikasiCuti,
)
from .services import CheckCuti
from .views import PelimpahanKepalaListView, PelimpahanTugasPenerimaListView
from .cuti_schedule import (
    apply_nonfinal_change,
    approve_final_change,
    cancel_schedule_change,
    determine_change_type,
    finalize_pending_schedule_change,
    reject_pending_schedule_change,
)


class CutiSecurityTests(TestCase):
    def setUp(self):
        self.pemilik = Users.objects.create_user(
            email='pemilik-cuti@example.com', first_name='Pemilik', last_name='Cuti',
            password='password-test',
        )
        self.orang_lain = Users.objects.create_user(
            email='lain-cuti@example.com', first_name='Orang', last_name='Lain',
            password='password-test',
        )
        self.admin_cuti = Users.objects.create_user(
            email='admin-pemutihan-cuti@example.com',
            first_name='Admin',
            last_name='Pemutihan',
            password='password-test',
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_LAYANAN_CUTI)
        self.admin_cuti.groups.add(group)
        AdminScopeAssignment.objects.create(
            user=self.admin_cuti,
            group=group,
            scope_type=AdminScopeAssignment.GLOBAL,
        )
        self.layanan_jenis = JenisLayanan.objects.create(
            nama='Cuti', url='cuti-test', status=True
        )
        self.layanan = LayananCuti.objects.create(
            pegawai=self.pemilik,
            layanan=self.layanan_jenis,
            status='pengajuan',
            tahun=date.today().year,
        )
        self.riwayat = RiwayatCuti.objects.create(
            pegawai=self.pemilik,
            usulan=self.layanan,
            jenis_cuti='Cuti Tahunan',
            tgl_mulai_cuti=date(date.today().year, 11, 1),
            tgl_akhir_cuti=date(date.today().year, 11, 2),
            lama_cuti=2,
            tahun_cuti=date.today().year,
            status_cuti='Belum',
        )

    def test_url_lama_tidak_dapat_mengubah_pengajuan_pegawai_lain(self):
        self.client.force_login(self.orang_lain)
        response = self.client.post(
            reverse(
                'layanan_urls:layanan_cuti_update_view',
                kwargs={'status': 'riwayat', 'id': self.layanan.pk},
            ),
            {'aksi': 'aksi'},
        )
        self.assertEqual(response.status_code, 403)

    def test_pemutihan_hanya_dapat_diakses_admin_cuti(self):
        url = reverse('layanan_urls:cuti_pemutihan_admin')
        self.client.force_login(self.orang_lain)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.admin_cuti)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_kepala_melihat_pelimpahan_yang_masih_menunggu_penerima(self):
        pelimpahan = PelimpahanTugas.objects.create(
            riwayat_cuti=self.riwayat,
            pemberi_tugas=self.pemilik,
            penerima_tugas=self.admin_cuti,
            atasan_penyetuju=self.orang_lain,
            deskripsi_tugas='Menjalankan tugas selama cuti',
            tgl_mulai=self.riwayat.tgl_mulai_cuti,
            tgl_selesai=self.riwayat.tgl_akhir_cuti,
            status='menunggu_penerima',
            butuh_persetujuan_atasan=True,
        )
        self.client.force_login(self.orang_lain)

        response = self.client.get(
            reverse('layanan_urls:pelimpahan_atasan_list')
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pemilik.full_name)
        self.assertContains(response, 'Menunggu persetujuan penerima tugas')
        self.assertContains(response, 'Belum dapat diparaf')
        self.assertNotContains(
            response,
            reverse(
                'layanan_urls:pelimpahan_atasan_update',
                kwargs={'pk': pelimpahan.pk},
            ),
        )

    def test_tombol_paraf_kepala_muncul_setelah_penerima_setuju(self):
        pelimpahan = PelimpahanTugas.objects.create(
            riwayat_cuti=self.riwayat,
            pemberi_tugas=self.pemilik,
            penerima_tugas=self.admin_cuti,
            atasan_penyetuju=self.orang_lain,
            deskripsi_tugas='Menjalankan tugas selama cuti',
            tgl_mulai=self.riwayat.tgl_mulai_cuti,
            tgl_selesai=self.riwayat.tgl_akhir_cuti,
            status='menunggu_atasan',
            persetujuan_penerima='disetujui',
            butuh_persetujuan_atasan=True,
        )
        self.client.force_login(self.orang_lain)

        response = self.client.get(
            reverse('layanan_urls:pelimpahan_atasan_list')
        )

        self.assertContains(response, 'Menunggu persetujuan Anda')
        self.assertContains(
            response,
            reverse(
                'layanan_urls:pelimpahan_atasan_update',
                kwargs={'pk': pelimpahan.pk},
            ),
        )

    def test_admin_cuti_dapat_monitor_tanpa_mengambil_keputusan_kepala(self):
        pelimpahan = PelimpahanTugas.objects.create(
            riwayat_cuti=self.riwayat,
            pemberi_tugas=self.pemilik,
            penerima_tugas=self.admin_cuti,
            atasan_penyetuju=self.orang_lain,
            deskripsi_tugas='Menjalankan tugas selama cuti',
            tgl_mulai=self.riwayat.tgl_mulai_cuti,
            tgl_selesai=self.riwayat.tgl_akhir_cuti,
            status='menunggu_atasan',
            persetujuan_penerima='disetujui',
            butuh_persetujuan_atasan=True,
        )
        self.client.force_login(self.admin_cuti)

        response = self.client.get(
            reverse('layanan_urls:pelimpahan_atasan_list')
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pemilik.full_name)
        self.assertContains(response, self.orang_lain.full_name)
        self.assertContains(response, 'Monitoring')
        decision_url = reverse(
            'layanan_urls:pelimpahan_atasan_update',
            kwargs={'pk': pelimpahan.pk},
        )
        self.assertNotContains(response, decision_url)
        self.assertEqual(self.client.get(decision_url).status_code, 404)

    def test_admin_cuti_dapat_monitor_persetujuan_penerima_tanpa_mengambil_alih(self):
        pelimpahan = PelimpahanTugas.objects.create(
            riwayat_cuti=self.riwayat,
            pemberi_tugas=self.pemilik,
            penerima_tugas=self.orang_lain,
            deskripsi_tugas='Menjalankan tugas selama cuti',
            tgl_mulai=self.riwayat.tgl_mulai_cuti,
            tgl_selesai=self.riwayat.tgl_akhir_cuti,
            status='menunggu_penerima',
            butuh_persetujuan_atasan=False,
        )
        self.client.force_login(self.admin_cuti)

        response = self.client.get(
            reverse('layanan_urls:pelimpahan_penerima_list')
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Monitoring Persetujuan Penerima Tugas')
        self.assertContains(response, self.pemilik.full_name)
        self.assertContains(response, self.orang_lain.full_name)
        self.assertContains(response, 'Belum memberikan keputusan')
        self.assertContains(response, 'Monitoring')
        decision_url = reverse(
            'layanan_urls:pelimpahan_penerima_update',
            kwargs={'pk': pelimpahan.pk},
        )
        self.assertNotContains(response, decision_url)
        self.assertEqual(self.client.get(decision_url).status_code, 404)

    def test_admin_dapat_mencari_pegawai_pada_daftar_pelimpahan(self):
        pelimpahan = PelimpahanTugas.objects.create(
            riwayat_cuti=self.riwayat,
            pemberi_tugas=self.pemilik,
            penerima_tugas=self.orang_lain,
            atasan_penyetuju=self.admin_cuti,
            deskripsi_tugas='Menjalankan tugas selama cuti',
            tgl_mulai=self.riwayat.tgl_mulai_cuti,
            tgl_selesai=self.riwayat.tgl_akhir_cuti,
            status='menunggu_penerima',
            butuh_persetujuan_atasan=True,
        )
        self.client.force_login(self.admin_cuti)

        for url_name in (
            'layanan_urls:pelimpahan_penerima_list',
            'layanan_urls:pelimpahan_atasan_list',
        ):
            response = self.client.get(
                reverse(url_name), {'q': self.orang_lain.email}
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, pelimpahan.penerima_tugas.full_name)
            self.assertEqual(response.context['q'], self.orang_lain.email)

            response_kosong = self.client.get(
                reverse(url_name), {'q': 'pegawai-tidak-ditemukan'}
            )
            self.assertNotContains(
                response_kosong, pelimpahan.penerima_tugas.full_name
            )

    def test_daftar_pelimpahan_memakai_pagination_dua_puluh_baris(self):
        self.assertEqual(PelimpahanTugasPenerimaListView.paginate_by, 20)
        self.assertEqual(PelimpahanKepalaListView.paginate_by, 20)

    def test_penerima_lama_baru_bebas_setelah_pengalihan_disetujui(self):
        penerima_baru = Users.objects.create_user(
            email='penerima-baru@example.com',
            first_name='Penerima',
            last_name='Baru',
            password='password-test',
        )
        pelimpahan = PelimpahanTugas.objects.create(
            riwayat_cuti=self.riwayat,
            pemberi_tugas=self.pemilik,
            penerima_tugas=self.orang_lain,
            deskripsi_tugas='Menjalankan tugas selama cuti',
            tgl_mulai=self.riwayat.tgl_mulai_cuti,
            tgl_selesai=self.riwayat.tgl_akhir_cuti,
            status='disetujui',
            persetujuan_penerima='disetujui',
            persetujuan_atasan='disetujui',
            butuh_persetujuan_atasan=False,
        )
        self.client.force_login(self.admin_cuti)

        response = self.client.post(
            reverse('layanan_urls:pelimpahan_alihkan', kwargs={'pk': pelimpahan.pk}),
            {'penerima_baru': penerima_baru.pk, 'alasan': 'Keperluan keluarga mendesak.'},
        )

        self.assertRedirects(
            response,
            reverse('layanan_urls:pelimpahan_detail', kwargs={'pk': pelimpahan.pk}),
        )
        pelimpahan.refresh_from_db()
        self.assertEqual(pelimpahan.penerima_tugas, penerima_baru)
        self.assertEqual(pelimpahan.status, 'menunggu_penerima')
        self.assertEqual(pelimpahan.persetujuan_penerima, 'belum')
        self.assertTrue(CheckCuti().is_penerima_memiliki_pelimpahan_aktif(
            self.orang_lain, pelimpahan.tgl_mulai, pelimpahan.tgl_selesai
        ))
        log = PengalihanPelimpahanTugas.objects.get(pelimpahan=pelimpahan)
        self.assertEqual(log.penerima_lama, self.orang_lain)
        self.assertEqual(log.penerima_baru, penerima_baru)
        self.assertEqual(log.dialihkan_oleh, self.admin_cuti)
        self.assertEqual(log.status, 'menunggu')

        self.client.force_login(penerima_baru)
        response = self.client.post(
            reverse(
                'layanan_urls:pelimpahan_penerima_update',
                kwargs={'pk': pelimpahan.pk},
            ),
            {'aksi': 'setuju', 'catatan_penerima': 'Bersedia menerima tugas.'},
        )

        self.assertEqual(response.status_code, 302)
        log.refresh_from_db()
        self.assertEqual(log.status, 'disetujui')
        self.assertFalse(CheckCuti().is_penerima_memiliki_pelimpahan_aktif(
            self.orang_lain, pelimpahan.tgl_mulai, pelimpahan.tgl_selesai
        ))

    def test_penolakan_pengalihan_memulihkan_penerima_lama(self):
        penerima_baru = Users.objects.create_user(
            email='penerima-menolak@example.com', password='password-test'
        )
        pelimpahan = PelimpahanTugas.objects.create(
            riwayat_cuti=self.riwayat,
            pemberi_tugas=self.pemilik,
            penerima_tugas=self.orang_lain,
            deskripsi_tugas='Menjalankan tugas selama cuti',
            tgl_mulai=self.riwayat.tgl_mulai_cuti,
            tgl_selesai=self.riwayat.tgl_akhir_cuti,
            status='disetujui',
            persetujuan_penerima='disetujui',
            persetujuan_atasan='disetujui',
            butuh_persetujuan_atasan=False,
        )
        self.client.force_login(self.admin_cuti)
        self.client.post(
            reverse('layanan_urls:pelimpahan_alihkan', kwargs={'pk': pelimpahan.pk}),
            {'penerima_baru': penerima_baru.pk, 'alasan': 'Pengalihan darurat.'},
        )
        self.client.force_login(penerima_baru)

        self.client.post(
            reverse(
                'layanan_urls:pelimpahan_penerima_update',
                kwargs={'pk': pelimpahan.pk},
            ),
            {'aksi': 'tolak', 'catatan_penerima': 'Tidak dapat menerima.'},
        )

        pelimpahan.refresh_from_db()
        log = PengalihanPelimpahanTugas.objects.get(pelimpahan=pelimpahan)
        self.assertEqual(pelimpahan.penerima_tugas, self.orang_lain)
        self.assertEqual(pelimpahan.status, 'disetujui')
        self.assertEqual(log.status, 'ditolak')
        self.assertTrue(CheckCuti().is_penerima_memiliki_pelimpahan_aktif(
            self.orang_lain, pelimpahan.tgl_mulai, pelimpahan.tgl_selesai
        ))

    def test_penerima_aktif_tidak_dapat_mengalihkan_sendiri(self):
        penerima_baru = Users.objects.create_user(
            email='pengganti-mandiri@example.com', password='password-test'
        )
        pelimpahan = PelimpahanTugas.objects.create(
            riwayat_cuti=self.riwayat,
            pemberi_tugas=self.pemilik,
            penerima_tugas=self.orang_lain,
            deskripsi_tugas='Menjalankan tugas selama cuti',
            tgl_mulai=self.riwayat.tgl_mulai_cuti,
            tgl_selesai=self.riwayat.tgl_akhir_cuti,
            status='disetujui',
            persetujuan_penerima='disetujui',
            persetujuan_atasan='disetujui',
            butuh_persetujuan_atasan=False,
        )
        self.client.force_login(self.orang_lain)

        response = self.client.post(
            reverse('layanan_urls:pelimpahan_alihkan', kwargs={'pk': pelimpahan.pk}),
            {'penerima_baru': penerima_baru.pk, 'alasan': 'Keperluan mendesak.'},
        )

        self.assertEqual(response.status_code, 403)
        pelimpahan.refresh_from_db()
        self.assertEqual(pelimpahan.penerima_tugas, self.orang_lain)
        self.assertFalse(PengalihanPelimpahanTugas.objects.exists())

    def test_pegawai_di_luar_pelimpahan_tidak_dapat_mengalihkan(self):
        penerima_baru = Users.objects.create_user(
            email='calon-penerima@example.com', password='password-test'
        )
        pelimpahan = PelimpahanTugas.objects.create(
            riwayat_cuti=self.riwayat,
            pemberi_tugas=self.pemilik,
            penerima_tugas=self.admin_cuti,
            deskripsi_tugas='Menjalankan tugas selama cuti',
            tgl_mulai=self.riwayat.tgl_mulai_cuti,
            tgl_selesai=self.riwayat.tgl_akhir_cuti,
            status='disetujui',
            persetujuan_penerima='disetujui',
            persetujuan_atasan='disetujui',
            butuh_persetujuan_atasan=False,
        )
        self.client.force_login(self.orang_lain)

        response = self.client.post(
            reverse('layanan_urls:pelimpahan_alihkan', kwargs={'pk': pelimpahan.pk}),
            {'penerima_baru': penerima_baru.pk, 'alasan': 'Tidak berwenang.'},
        )

        self.assertEqual(response.status_code, 403)
        pelimpahan.refresh_from_db()
        self.assertEqual(pelimpahan.penerima_tugas, self.admin_cuti)
        self.assertFalse(PengalihanPelimpahanTugas.objects.exists())

    def test_admin_dapat_memutihkan_pengajuan_dengan_log_audit(self):
        self.client.force_login(self.admin_cuti)
        url = reverse('layanan_urls:cuti_pemutihan_admin')
        response = self.client.post(url, {
            'tanggal_mulai': date.today().replace(month=1, day=1).isoformat(),
            'tanggal_akhir': date.today().isoformat(),
            'status': 'proses',
            'pengajuan_ids': [str(self.layanan.pk)],
            'aksi': 'dibatalkan',
            'catatan': 'Pemulihan data akibat gangguan sistem.',
        })

        self.assertEqual(response.status_code, 302)
        self.layanan.refresh_from_db()
        self.riwayat.refresh_from_db()
        self.assertEqual(self.layanan.status, 'dibatalkan')
        self.assertEqual(self.riwayat.status_cuti, 'Batal')
        log = PemutihanCutiLog.objects.get(layanan_cuti=self.layanan)
        self.assertEqual(log.admin, self.admin_cuti)
        self.assertEqual(log.status_pengajuan_sebelum, 'pengajuan')
        self.assertEqual(log.status_pengajuan_sesudah, 'dibatalkan')

    def test_semua_keputusan_pemutihan_memperbarui_status_konsisten(self):
        self.client.force_login(self.admin_cuti)
        url = reverse('layanan_urls:cuti_pemutihan_admin')
        expected = {
            'disetujui': ('disetujui', 'Selesai'),
            'selesai': ('selesai', 'Selesai'),
            'ditolak': ('ditolak', 'Batal'),
        }

        for index, (aksi, hasil) in enumerate(expected.items(), start=1):
            layanan = LayananCuti.objects.create(
                pegawai=self.pemilik,
                layanan=self.layanan_jenis,
                status='pengajuan',
                tahun=date.today().year,
            )
            riwayat = RiwayatCuti.objects.create(
                pegawai=self.pemilik,
                usulan=layanan,
                jenis_cuti='Cuti Tahunan',
                lama_cuti=index,
                tahun_cuti=date.today().year,
                status_cuti='Belum',
                tgl_mulai_cuti=date.today() - timedelta(days=10),
                tgl_akhir_cuti=date.today() - timedelta(days=9),
            )
            response = self.client.post(url, {
                'tanggal_mulai': date.today().replace(
                    month=1,
                    day=1,
                ).isoformat(),
                'tanggal_akhir': date.today().isoformat(),
                'status': 'proses',
                'pengajuan_ids': [str(layanan.pk)],
                'aksi': aksi,
                'catatan': f'Pemutihan pengujian {aksi}.',
            })
            self.assertEqual(response.status_code, 302)
            layanan.refresh_from_db()
            riwayat.refresh_from_db()
            self.assertEqual(layanan.status, hasil[0])
            self.assertEqual(riwayat.status_cuti, hasil[1])

    def test_pemilik_url_lama_diarahkan_ke_detail_baru(self):
        self.client.force_login(self.pemilik)
        response = self.client.get(
            reverse(
                'layanan_urls:layanan_cuti_update_view',
                kwargs={'status': 'riwayat', 'id': self.layanan.pk},
            )
        )
        self.assertRedirects(
            response,
            reverse('layanan_urls:layanan_cuti_detail', kwargs={'pk': self.layanan.pk}),
            fetch_redirect_response=False,
        )

    def test_url_cuti_tunda_lama_diarahkan_ke_alur_baru(self):
        self.client.force_login(self.pemilik)
        create_url = reverse('layanan_urls:layanan_cuti_create_view')
        list_url = reverse('layanan_urls:layanan_cuti_listview')

        self.assertRedirects(
            self.client.get(reverse('layanan_urls:layanan_cuti_tunda_view')),
            create_url,
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            self.client.get(reverse(
                'layanan_urls:layanan_ambil_cuti_tunda_view',
                kwargs={'pk': self.riwayat.pk},
            )),
            create_url,
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            self.client.get(reverse(
                'layanan_urls:layanan_update_cuti_tunda_view',
                kwargs={'pk': self.riwayat.pk},
            )),
            list_url,
            fetch_redirect_response=False,
        )

    def test_status_default_layanan_langsung_diajukan(self):
        layanan = LayananCuti(
            pegawai=self.orang_lain,
            layanan=self.layanan_jenis,
        )
        self.assertEqual(layanan.status, 'pengajuan')

    def test_verifikator_snapshot_tetap_dapat_melihat_detail_dan_hasil(self):
        VerifikasiCuti.objects.create(
            layanan_cuti=self.layanan,
            verifikator1=self.orang_lain,
            keputusan1='setuju',
            catatan1='Disetujui oleh atasan.',
        )
        self.layanan.status = 'tindaklanjut'
        self.layanan.save(update_fields=['status'])
        self.client.force_login(self.orang_lain)

        daftar = self.client.get(
            reverse('layanan_urls:layanan_cuti_bawahan_listview'),
        )
        detail = self.client.get(
            reverse(
                'layanan_urls:layanan_cuti_detail',
                kwargs={'pk': self.layanan.pk},
            ),
        )
        hasil = self.client.get(
            reverse(
                'layanan_urls:layanan_cuti_verifikasi',
                kwargs={'id': self.layanan.pk},
            ),
        )

        self.assertEqual(daftar.status_code, 200)
        self.assertContains(daftar, self.pemilik.full_name)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(hasil.status_code, 200)
        self.assertTrue(hasil.context['view_only'])
        self.assertFalse(hasil.context['can_submit_verification'])
        self.assertContains(hasil, 'Disetujui oleh atasan.')
        self.assertNotContains(hasil, 'Simpan Verifikasi')
        self.assertTrue(all(field.disabled for field in hasil.context['form'].fields.values()))

    def test_pencarian_riwayat_cuti_saya_memfilter_data(self):
        self.client.force_login(self.pemilik)
        url = reverse('layanan_urls:layanan_cuti_listview')

        ditemukan = self.client.get(url, {'q': 'Tahunan'})
        tidak_ditemukan = self.client.get(url, {'q': 'kata-kunci-tidak-ada'})

        self.assertEqual(ditemukan.status_code, 200)
        self.assertQuerySetEqual(ditemukan.context['data'], [self.riwayat])
        self.assertEqual(ditemukan.context['search_query'], 'Tahunan')
        self.assertQuerySetEqual(tidak_ditemukan.context['data'], [])

    def test_pencarian_riwayat_cuti_bawahan_memfilter_data_dalam_scope(self):
        self.client.force_login(self.admin_cuti)
        url = reverse('layanan_urls:layanan_cuti_bawahan_listview')

        ditemukan = self.client.get(url, {'q': 'Pemilik'})
        tidak_ditemukan = self.client.get(url, {'q': 'kata-kunci-tidak-ada'})

        self.assertEqual(ditemukan.status_code, 200)
        self.assertQuerySetEqual(ditemukan.context['data'], [self.riwayat])
        self.assertEqual(ditemukan.context['search_query'], 'Pemilik')
        self.assertQuerySetEqual(tidak_ditemukan.context['data'], [])

    def test_atasan_dalam_lingkup_bawahan_dapat_membuka_detail_dan_monitoring(self):
        VerifikasiCuti.objects.create(layanan_cuti=self.layanan)
        self.client.force_login(self.orang_lain)

        with patch(
            'layanan.access.cuti.can_supervise_employee',
            return_value=True,
        ):
            detail = self.client.get(
                reverse(
                    'layanan_urls:layanan_cuti_detail',
                    kwargs={'pk': self.layanan.pk},
                ),
            )
        with patch(
            'layanan.views.can_supervise_employee',
            return_value=True,
        ):
            hasil = self.client.get(
                reverse(
                    'layanan_urls:layanan_cuti_verifikasi',
                    kwargs={'id': self.layanan.pk},
                ),
            )

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(hasil.status_code, 200)
        self.assertTrue(hasil.context['view_only'])
        self.assertFalse(hasil.context['can_submit_verification'])

    def test_hasil_verifikasi_tidak_dapat_diubah_kembali(self):
        verifikasi = VerifikasiCuti.objects.create(
            layanan_cuti=self.layanan,
            verifikator1=self.orang_lain,
            keputusan1='setuju',
            catatan1='Keputusan awal.',
        )
        self.client.force_login(self.orang_lain)
        url = reverse(
            'layanan_urls:layanan_cuti_verifikasi',
            kwargs={'id': self.layanan.pk},
        )

        response = self.client.post(
            url,
            {'keputusan1': 'tolak', 'catatan1': 'Mencoba mengubah.'},
        )

        self.assertRedirects(response, url, fetch_redirect_response=False)
        verifikasi.refresh_from_db()
        self.assertEqual(verifikasi.keputusan1, 'setuju')
        self.assertEqual(verifikasi.catatan1, 'Keputusan awal.')

    def test_verifikator_yang_belum_memutuskan_mendapat_form_edit(self):
        VerifikasiCuti.objects.create(
            layanan_cuti=self.layanan,
            verifikator1=self.orang_lain,
        )
        self.client.force_login(self.orang_lain)

        response = self.client.get(
            reverse(
                'layanan_urls:layanan_cuti_verifikasi',
                kwargs={'id': self.layanan.pk},
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['view_only'])
        self.assertTrue(response.context['can_submit_verification'])
        self.assertEqual(response.context['current_level'], 1)
        self.assertContains(response, 'Simpan Verifikasi')

    def test_verifikator_dapat_menyimpan_keputusan_lalu_melihat_hasilnya(self):
        self._buat_pelimpahan_disetujui()
        verifikasi = VerifikasiCuti.objects.create(
            layanan_cuti=self.layanan,
            verifikator1=self.orang_lain,
        )
        self.client.force_login(self.orang_lain)
        url = reverse(
            'layanan_urls:layanan_cuti_verifikasi',
            kwargs={'id': self.layanan.pk},
        )

        response = self.client.post(
            url,
            {'keputusan1': 'setuju', 'catatan1': 'Pengajuan sesuai.'},
        )

        self.assertRedirects(
            response,
            reverse('layanan_urls:layanan_cuti_bawahan_listview'),
            fetch_redirect_response=False,
        )
        verifikasi.refresh_from_db()
        self.layanan.refresh_from_db()
        self.assertEqual(verifikasi.keputusan1, 'setuju')
        self.assertEqual(self.layanan.status, 'disetujui')

        hasil = self.client.get(url)
        self.assertEqual(hasil.status_code, 200)
        self.assertTrue(hasil.context['view_only'])
        self.assertContains(hasil, 'Pengajuan sesuai.')

    def test_dokumen_cuti_memerlukan_login_dan_hak_akses(self):
        url = reverse('file_urls:formulir_cuti_pdf', kwargs={'pk': self.riwayat.pk})
        self.assertEqual(self.client.get(url).status_code, 302)

        self.client.force_login(self.orang_lain)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.pemilik)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'%PDF-'))

    def test_relasi_verifikasi_tidak_dapat_dikirim_dari_browser(self):
        self.assertEqual(set(Verifikator2CutiForm().fields), {'keputusan2', 'catatan2'})
        self.assertEqual(set(Verifikator3CutiForm().fields), {'keputusan3', 'catatan3'})

    def test_pengajuan_pending_mencadangkan_saldo_dan_penolakan_melepasnya(self):
        checker = CheckCuti()
        saldo_dengan_pengajuan = checker.cek_sisa_cuti(self.pemilik)

        self.layanan.status = 'ditolak'
        self.layanan.save(update_fields=['status'])
        self.riwayat.status_cuti = 'Batal'
        self.riwayat.save(update_fields=['status_cuti'])

        self.assertEqual(checker.cek_sisa_cuti(self.pemilik), saldo_dengan_pengajuan + 2)

    def test_klaim_tunda_tidak_mengurangi_saldo_dua_kali(self):
        checker = CheckCuti()
        sumber = RiwayatCuti.objects.create(
            pegawai=self.pemilik,
            jenis_cuti='Cuti Tahunan',
            lama_cuti=2,
            tahun_cuti=date.today().year - 1,
            status_cuti='Tunda',
        )
        saldo_sebelum_klaim = checker.cek_sisa_cuti(self.pemilik)

        KlaimCutiTunda.objects.create(
            sumber_tunda=sumber,
            cuti_klaim=self.riwayat,
            jumlah_hari_diklaim=2,
        )

        saldo_setelah_klaim = checker.cek_sisa_cuti(self.pemilik)
        snapshot = checker.buat_snapshot_saldo_cuti(
            self.pemilik,
            date.today().year,
        )
        self.assertEqual(saldo_setelah_klaim, saldo_sebelum_klaim)
        self.assertEqual(snapshot['total_tersedia'], saldo_setelah_klaim)
        self.assertEqual(
            snapshot['total_tersedia'],
            sum(row['dapat_digunakan'] for row in snapshot['rows']),
        )
        baris_n1 = next(row for row in snapshot['rows'] if row['label'] == 'N-1')
        self.assertEqual(baris_n1['hak_tunda'], 2)
        self.assertEqual(baris_n1['terpakai_tunda'], 2)
        self.assertEqual(baris_n1['sisa_tunda'], 0)
        self.assertEqual(baris_n1['dapat_digunakan'], 0)
        baris_n = next(row for row in snapshot['rows'] if row['label'] == 'N')
        self.assertEqual(baris_n['dicadangkan'], 0)

    def test_pembatalan_pemutihan_melepaskan_klaim_cuti_tunda(self):
        sumber = RiwayatCuti.objects.create(
            pegawai=self.pemilik,
            jenis_cuti='Cuti Tahunan',
            lama_cuti=3,
            tahun_cuti=date.today().year - 1,
            status_cuti='Tunda',
        )
        KlaimCutiTunda.objects.create(
            sumber_tunda=sumber,
            cuti_klaim=self.riwayat,
            jumlah_hari_diklaim=2,
        )
        self.assertEqual(sumber.sisa_hari_tunda, 1)

        self.client.force_login(self.admin_cuti)
        response = self.client.post(
            reverse('layanan_urls:cuti_pemutihan_admin'),
            {
                'tanggal_mulai': date.today().replace(
                    month=1,
                    day=1,
                ).isoformat(),
                'tanggal_akhir': date.today().isoformat(),
                'status': 'proses',
                'pengajuan_ids': [str(self.layanan.pk)],
                'aksi': 'dibatalkan',
                'catatan': 'Pengajuan tidak berlaku akibat gangguan.',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sumber.sisa_hari_tunda, 3)

    def test_klaim_tunda_harus_milik_pegawai_yang_sama(self):
        sumber = RiwayatCuti.objects.create(
            pegawai=self.pemilik,
            jenis_cuti='Cuti Tahunan',
            lama_cuti=3,
            tahun_cuti=date.today().year - 1,
            status_cuti='Tunda',
        )
        cuti_orang_lain = RiwayatCuti.objects.create(
            pegawai=self.orang_lain,
            jenis_cuti='Cuti Tahunan',
            lama_cuti=1,
            tahun_cuti=date.today().year,
        )
        klaim = KlaimCutiTunda(
            sumber_tunda=sumber,
            cuti_klaim=cuti_orang_lain,
            jumlah_hari_diklaim=1,
        )
        with self.assertRaises(ValidationError):
            klaim.full_clean()

    def _buat_pelimpahan_disetujui(self):
        return PelimpahanTugas.objects.create(
            riwayat_cuti=self.riwayat,
            pemberi_tugas=self.pemilik,
            penerima_tugas=self.orang_lain,
            deskripsi_tugas='Menjalankan tugas rutin',
            tgl_mulai=self.riwayat.tgl_mulai_cuti,
            tgl_selesai=self.riwayat.tgl_akhir_cuti,
            status='disetujui',
            persetujuan_penerima='disetujui',
            persetujuan_atasan='disetujui',
            butuh_persetujuan_atasan=False,
        )

    def _buat_perubahan(self, jenis):
        mulai_baru = self.riwayat.tgl_mulai_cuti + timedelta(days=7)
        akhir_baru = mulai_baru + timedelta(days=1)
        return PerubahanJadwalCuti.objects.create(
            riwayat_cuti=self.riwayat,
            diajukan_oleh=self.pemilik,
            jenis_perubahan=jenis,
            status='menunggu_verifikasi' if jenis == 'perubahan_final' else 'diterapkan',
            tanggal_mulai_lama=self.riwayat.tgl_mulai_cuti,
            tanggal_akhir_lama=self.riwayat.tgl_akhir_cuti,
            lama_cuti_lama=self.riwayat.lama_cuti,
            tanggal_mulai_baru=mulai_baru,
            tanggal_akhir_baru=akhir_baru,
            lama_cuti_baru=2,
            alasan='Penyesuaian jadwal pelayanan',
        )

    def test_perubahan_sebelum_verifikasi_diterapkan_dan_pelimpahan_diulang(self):
        pelimpahan = self._buat_pelimpahan_disetujui()
        perubahan = self._buat_perubahan('langsung')

        apply_nonfinal_change(perubahan.pk)

        self.riwayat.refresh_from_db()
        pelimpahan.refresh_from_db()
        perubahan.refresh_from_db()
        self.assertEqual(self.riwayat.tgl_mulai_cuti, perubahan.tanggal_mulai_baru)
        self.assertEqual(pelimpahan.tgl_mulai, perubahan.tanggal_mulai_baru)
        self.assertEqual(pelimpahan.status, 'menunggu_penerima')
        self.assertEqual(pelimpahan.persetujuan_penerima, 'belum')
        self.assertTrue(perubahan.snapshot_pelimpahan)

    def test_revisi_saat_proses_mereset_keputusan_verifikasi(self):
        self._buat_pelimpahan_disetujui()
        verifikasi = VerifikasiCuti.objects.create(
            layanan_cuti=self.layanan,
            verifikator1=self.orang_lain,
            keputusan1='setuju',
        )
        self.assertEqual(determine_change_type(self.riwayat), 'revisi_proses')
        perubahan = self._buat_perubahan('revisi_proses')

        apply_nonfinal_change(perubahan.pk)

        verifikasi.refresh_from_db()
        self.riwayat.refresh_from_db()
        perubahan.refresh_from_db()
        self.assertEqual(verifikasi.keputusan1, 'belum')
        self.assertEqual(self.riwayat.status_cuti, 'Belum')
        self.assertEqual(self.layanan.__class__.objects.get(pk=self.layanan.pk).status, 'pengajuan')
        self.assertEqual(perubahan.snapshot_verifikasi['1']['keputusan'], 'setuju')

    def test_perubahan_setelah_final_menunggu_pelimpahan_sebelum_diterapkan(self):
        pelimpahan = self._buat_pelimpahan_disetujui()
        self.layanan.status = 'disetujui'
        self.layanan.save(update_fields=['status'])
        tanggal_lama = self.riwayat.tgl_mulai_cuti
        perubahan = self._buat_perubahan('perubahan_final')

        approve_final_change(perubahan.pk)

        self.riwayat.refresh_from_db()
        pelimpahan.refresh_from_db()
        perubahan.refresh_from_db()
        self.assertEqual(self.riwayat.tgl_mulai_cuti, tanggal_lama)
        self.assertEqual(perubahan.status, 'menunggu_pelimpahan')
        self.assertEqual(pelimpahan.status, 'menunggu_penerima')

        pelimpahan.status = 'disetujui'
        pelimpahan.persetujuan_penerima = 'disetujui'
        pelimpahan.persetujuan_atasan = 'disetujui'
        pelimpahan.save()
        finalize_pending_schedule_change(pelimpahan.pk)

        self.riwayat.refresh_from_db()
        perubahan.refresh_from_db()
        self.assertEqual(self.riwayat.tgl_mulai_cuti, perubahan.tanggal_mulai_baru)
        self.assertEqual(perubahan.status, 'diterapkan')

    def test_penolakan_pelimpahan_memulihkan_persetujuan_jadwal_lama(self):
        pelimpahan = self._buat_pelimpahan_disetujui()
        self.layanan.status = 'disetujui'
        self.layanan.save(update_fields=['status'])
        tanggal_pelimpahan_lama = pelimpahan.tgl_mulai
        perubahan = self._buat_perubahan('perubahan_final')
        approve_final_change(perubahan.pk)

        pelimpahan.refresh_from_db()
        pelimpahan.status = 'ditolak_penerima'
        pelimpahan.persetujuan_penerima = 'ditolak'
        pelimpahan.save()
        reject_pending_schedule_change(pelimpahan.pk)

        pelimpahan.refresh_from_db()
        perubahan.refresh_from_db()
        self.assertEqual(perubahan.status, 'ditolak')
        self.assertEqual(pelimpahan.status, 'disetujui')
        self.assertEqual(pelimpahan.persetujuan_penerima, 'disetujui')
        self.assertEqual(pelimpahan.tgl_mulai, tanggal_pelimpahan_lama)

    def test_hanya_verifikator_yang_dapat_memutuskan_perubahan_final(self):
        self._buat_pelimpahan_disetujui()
        self.layanan.status = 'disetujui'
        self.layanan.save(update_fields=['status'])
        perubahan = self._buat_perubahan('perubahan_final')
        perubahan.verifikator1 = self.orang_lain
        perubahan.save(update_fields=['verifikator1'])
        url = reverse(
            'layanan_urls:perubahan_jadwal_cuti_verifikasi',
            kwargs={'pk': perubahan.pk},
        )

        self.client.force_login(self.pemilik)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.orang_lain)
        response = self.client.post(url, {'keputusan': 'setuju', 'catatan': 'Disetujui'})
        self.assertEqual(response.status_code, 302)
        perubahan.refresh_from_db()
        self.assertEqual(perubahan.keputusan1, 'setuju')
        self.assertEqual(perubahan.status, 'menunggu_pelimpahan')

    def test_pemohon_dapat_membatalkan_perubahan_dan_pelimpahan_lama_dipulihkan(self):
        pelimpahan = self._buat_pelimpahan_disetujui()
        self.layanan.status = 'disetujui'
        self.layanan.save(update_fields=['status'])
        perubahan = self._buat_perubahan('perubahan_final')
        approve_final_change(perubahan.pk)

        cancel_schedule_change(perubahan.pk)

        perubahan.refresh_from_db()
        pelimpahan.refresh_from_db()
        self.assertEqual(perubahan.status, 'dibatalkan')
        self.assertEqual(pelimpahan.status, 'disetujui')
        self.assertEqual(pelimpahan.persetujuan_penerima, 'disetujui')
