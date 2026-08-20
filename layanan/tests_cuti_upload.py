import tempfile
from datetime import date, timedelta

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from dokumen.models import RiwayatCuti
from myaccount.models import AdminScopeAssignment, Users
from myaccount.roles import ADMIN_LAYANAN_CUTI

from .models import JenisLayanan, LayananCuti


class UploadFileCutiViewTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.override_media = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.override_media.enable()
        self.addCleanup(self.override_media.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.pegawai = Users.objects.create_user(
            email='pegawai-upload@example.com',
            password='rahasia',
            first_name='Pegawai',
            last_name='Cuti',
        )
        self.admin = Users.objects.create_user(
            email='admin-cuti-upload@example.com',
            password='rahasia',
            first_name='Admin',
            last_name='Cuti',
        )
        self.non_admin = Users.objects.create_user(
            email='pegawai-biasa@example.com',
            password='rahasia',
            first_name='Pegawai',
            last_name='Biasa',
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_LAYANAN_CUTI)
        self.admin.groups.add(group)
        AdminScopeAssignment.objects.create(
            user=self.admin,
            group=group,
            scope_type=AdminScopeAssignment.GLOBAL,
        )

        jenis_layanan = JenisLayanan.objects.create(
            nama='Layanan Cuti',
            status=True,
            url='cuti-upload-test',
        )
        self.layanan = LayananCuti.objects.create(
            pegawai=self.pegawai,
            layanan=jenis_layanan,
            status='disetujui',
            tahun=date.today().year,
        )
        self.riwayat = RiwayatCuti.objects.create(
            pegawai=self.pegawai,
            usulan=self.layanan,
            jenis_cuti='Cuti Tahunan',
            tgl_mulai_cuti=date.today() + timedelta(days=1),
            tgl_akhir_cuti=date.today() + timedelta(days=2),
            lama_cuti=2,
            tahun_cuti=date.today().year,
        )
        self.url = reverse(
            'layanan_urls:upload_file_cuti',
            kwargs={'pk': self.riwayat.pk},
        )

    @staticmethod
    def pdf_file(name='surat-cuti.pdf'):
        return SimpleUploadedFile(
            name,
            b'%PDF-1.4\n% dokumen surat cuti\n%%EOF',
            content_type='application/pdf',
        )

    def test_admin_dapat_mengunggah_surat_dan_menyelesaikan_pengajuan(self):
        self.client.force_login(self.admin)

        response = self.client.post(self.url, {'file': self.pdf_file()})

        self.assertRedirects(
            response,
            reverse(
                'layanan_urls:layanan_cuti_detail',
                kwargs={'pk': self.layanan.pk},
            ),
            fetch_redirect_response=False,
        )
        self.riwayat.refresh_from_db()
        self.layanan.refresh_from_db()
        self.assertTrue(self.riwayat.file.name.endswith('.pdf'))
        self.assertTrue(self.riwayat.file.storage.exists(self.riwayat.file.name))
        self.assertEqual(self.layanan.status, 'selesai')

    def test_superuser_melihat_tombol_upload_di_detail(self):
        superadmin = Users.objects.create_superuser(
            email='superadmin-cuti@example.com',
            password='rahasia',
            first_name='Super',
            last_name='Admin',
        )
        self.client.force_login(superadmin)

        response = self.client.get(
            reverse(
                'layanan_urls:layanan_cuti_detail',
                kwargs={'pk': self.layanan.pk},
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_upload_surat_cuti'])
        self.assertContains(response, 'Upload Surat Cuti')

    def test_file_bukan_pdf_ditolak_dan_status_tidak_berubah(self):
        self.client.force_login(self.admin)
        file_palsu = SimpleUploadedFile(
            'surat-cuti.pdf',
            b'ini bukan isi PDF',
            content_type='application/pdf',
        )

        response = self.client.post(self.url, {'file': file_palsu})

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'file',
            'Isi file tidak dikenali sebagai dokumen PDF yang valid.',
        )
        self.riwayat.refresh_from_db()
        self.layanan.refresh_from_db()
        self.assertFalse(self.riwayat.file)
        self.assertEqual(self.layanan.status, 'disetujui')

    def test_pegawai_bukan_admin_dilarang_mengunggah(self):
        self.client.force_login(self.non_admin)

        response = self.client.post(self.url, {'file': self.pdf_file()})

        self.assertEqual(response.status_code, 403)
        self.layanan.refresh_from_db()
        self.assertEqual(self.layanan.status, 'disetujui')

    def test_pengajuan_yang_belum_disetujui_tidak_dapat_diunggah(self):
        self.layanan.status = 'pengajuan'
        self.layanan.save(update_fields=('status',))
        self.client.force_login(self.admin)

        response = self.client.post(self.url, {'file': self.pdf_file()})

        self.assertEqual(response.status_code, 404)
        self.riwayat.refresh_from_db()
        self.layanan.refresh_from_db()
        self.assertFalse(self.riwayat.file)
        self.assertEqual(self.layanan.status, 'pengajuan')

    def test_status_selesai_tetap_dihitung_sebagai_cuti_disetujui(self):
        self.layanan.status = 'selesai'
        self.layanan.save(update_fields=('status',))

        # Pemanggilan tanpa parameter harus aman pada USE_TZ=False maupun True.
        self.assertIn(
            self.riwayat.status_pelaksanaan_aktual,
            ('Belum', 'Berlangsung', 'Selesai'),
        )
        self.assertEqual(
            self.riwayat.tentukan_status_pelaksanaan(
                pada=self.riwayat.tgl_mulai_cuti,
            ),
            'Berlangsung',
        )

    def test_halaman_cuti_bawahan_aman_dengan_use_tz_false(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('layanan_urls:layanan_cuti_bawahan_listview'),
        )

        self.assertEqual(response.status_code, 200)
