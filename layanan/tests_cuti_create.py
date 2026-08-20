from datetime import date, timedelta

from django import forms
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dokumen.forms import RiwayatPengajuanCutiForm
from dokumen.models import DokumenSDM, RiwayatCuti, RiwayatPengangkatan
from disiplinsdm.models import HariLibur, PolaKerjaPegawai
from myaccount.models import AdminScopeAssignment, Users
from myaccount.roles import ADMIN_LAYANAN_CUTI

from .forms import LayananCutiForm, pengajuan_cuti_formset
from .models import JenisLayanan, LayananCuti, PelimpahanTugas
from .services import CheckCuti


class LayananCutiCreateTests(TestCase):
    def setUp(self):
        self.pegawai = Users.objects.create_user(
            email='create-cuti-pegawai@example.com',
            password='rahasia',
            first_name='Pegawai',
            last_name='Create',
        )
        self.pegawai_lain = Users.objects.create_user(
            email='create-cuti-lain@example.com',
            password='rahasia',
            first_name='Pegawai',
            last_name='Lain',
        )
        self.admin = Users.objects.create_user(
            email='create-cuti-admin@example.com',
            password='rahasia',
            first_name='Admin',
            last_name='Cuti',
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_LAYANAN_CUTI)
        self.admin.groups.add(group)
        AdminScopeAssignment.objects.create(
            user=self.admin,
            group=group,
            scope_type=AdminScopeAssignment.GLOBAL,
        )
        self.superuser = Users.objects.create_superuser(
            email='superuser-create-cuti@example.com',
            password='rahasia',
            first_name='Superuser',
            last_name='Cuti',
        )

        self.jenis_layanan, _ = JenisLayanan.objects.update_or_create(
            url='yancuti',
            defaults={'nama': 'Layanan Cuti', 'status': True},
        )
        self.dokumen, _ = DokumenSDM.objects.update_or_create(
            url='cuti',
            defaults={'nama': 'Cuti'},
        )
        for pegawai in (self.pegawai, self.pegawai_lain):
            RiwayatPengangkatan.objects.create(
                pegawai=pegawai,
                dokumen=self.dokumen,
                status_pegawai='Kontrak',
                no_srt_putusan=f'SK-{pegawai.pk}',
                tgl_srt_putusan=date.today(),
            )
            PolaKerjaPegawai.objects.create(
                pegawai=pegawai,
                pola_kerja=PolaKerjaPegawai.REGULER,
                berlaku_mulai=date.today().replace(month=1, day=1),
            )

    def request_for(self, user, path='/'):
        request = RequestFactory().get(path)
        request.user = user
        return request

    def test_admin_mendapat_field_pemilihan_pegawai(self):
        form = LayananCutiForm(request=self.request_for(self.admin))

        self.assertNotIsInstance(form.fields['pegawai'].widget, forms.HiddenInput)
        self.assertIn(self.pegawai, form.fields['pegawai'].queryset)

    def test_pegawai_biasa_hanya_dapat_mengajukan_untuk_dirinya(self):
        form = LayananCutiForm(request=self.request_for(self.pegawai))

        self.assertIsInstance(form.fields['pegawai'].widget, forms.HiddenInput)
        self.assertQuerySetEqual(
            form.fields['pegawai'].queryset,
            Users.objects.filter(pk=self.pegawai.pk),
            transform=lambda user: user,
        )

    def test_admin_cuti_dapat_melihat_dan_menambah_pola_kerja(self):
        self.client.force_login(self.admin)
        url = reverse('layanan_urls:pola_kerja_pegawai')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pola Kerja Pegawai')
        self.assertContains(response, self.pegawai.email)
        self.assertEqual(response.context['paginator'].per_page, 25)

        PolaKerjaPegawai.objects.filter(pegawai=self.pegawai_lain).delete()
        response = self.client.post(url, {
            'pegawai': self.pegawai_lain.pk,
            'pola_kerja': PolaKerjaPegawai.SHIFT,
            'berlaku_mulai': date.today().isoformat(),
            'berlaku_sampai': '',
            'keterangan': 'Pola shift dari Admin Cuti',
        })

        self.assertRedirects(response, url)
        self.assertTrue(PolaKerjaPegawai.objects.filter(
            pegawai=self.pegawai_lain,
            pola_kerja=PolaKerjaPegawai.SHIFT,
        ).exists())

    def test_pegawai_biasa_tidak_dapat_mengelola_pola_kerja(self):
        self.client.force_login(self.pegawai)

        response = self.client.get(
            reverse('layanan_urls:pola_kerja_pegawai')
        )

        self.assertEqual(response.status_code, 403)

    def test_sumber_tunda_mengikuti_pegawai_target_admin(self):
        sumber_tunda = RiwayatCuti.objects.create(
            pegawai=self.pegawai,
            dokumen=self.dokumen,
            jenis_cuti='Cuti Tahunan',
            lama_cuti=3,
            tahun_cuti=date.today().year - 1,
            status_cuti='Tunda',
        )
        form = RiwayatPengajuanCutiForm(
            request=self.request_for(self.admin),
            target_pegawai=self.pegawai,
            tahun_pengajuan=date.today().year,
            check_cuti=CheckCuti(),
        )

        self.assertIn(
            sumber_tunda,
            form.fields['cuti_tunda_dipilih'].queryset,
        )

    def test_form_tidak_menawarkan_cuti_tertunda_lama(self):
        form = RiwayatPengajuanCutiForm(
            request=self.request_for(self.pegawai),
            target_pegawai=self.pegawai,
            tahun_pengajuan=date.today().year,
            check_cuti=CheckCuti(),
        )
        values = {value for value, _label in form.fields['jenis_cuti'].choices}

        self.assertNotIn('Cuti Tertunda', values)
        self.assertIn('Cuti Besar', values)
        self.assertIn('Cuti Diluar Tanggungan Negara', values)

    def test_formset_menolak_lebih_dari_satu_detail(self):
        prefix = pengajuan_cuti_formset.get_default_prefix()
        data = {
            f'{prefix}-TOTAL_FORMS': '2',
            f'{prefix}-INITIAL_FORMS': '0',
            f'{prefix}-MIN_NUM_FORMS': '1',
            f'{prefix}-MAX_NUM_FORMS': '1',
        }
        formset = pengajuan_cuti_formset(
            data=data,
            form_kwargs={
                'request': self.request_for(self.pegawai),
                'target_pegawai': self.pegawai,
                'tahun_pengajuan': date.today().year,
                'check_cuti': CheckCuti(),
            },
        )

        self.assertFalse(formset.is_valid())
        self.assertIn('paling banyak', str(formset.non_form_errors()).lower())

    def test_pengajuan_bentrok_ditolak(self):
        mulai = date.today() + timedelta(days=10)
        layanan_lama = LayananCuti.objects.create(
            pegawai=self.pegawai,
            layanan=self.jenis_layanan,
            status='pengajuan',
            tahun=date.today().year,
        )
        RiwayatCuti.objects.create(
            pegawai=self.pegawai,
            dokumen=self.dokumen,
            usulan=layanan_lama,
            jenis_cuti='Cuti Tahunan',
            tgl_mulai_cuti=mulai,
            tgl_akhir_cuti=mulai + timedelta(days=2),
            lama_cuti=3,
            tahun_cuti=date.today().year,
            status_cuti='Belum',
        )

        self.assertTrue(
            CheckCuti().is_memiliki_cuti_bentrok(
                self.pegawai,
                mulai + timedelta(days=1),
                mulai + timedelta(days=3),
            )
        )

    def test_pegawai_dapat_membuat_satu_pengajuan_cuti_tahunan(self):
        self.client.force_login(self.pegawai)
        mulai = date.today() + timedelta(days=10)
        prefix = pengajuan_cuti_formset.get_default_prefix()
        response = self.client.post(
            reverse('layanan_urls:layanan_cuti_create_view'),
            {
                'pegawai': self.pegawai.pk,
                'layanan': self.jenis_layanan.pk,
                'status': 'pengajuan',
                'tahun': date.today().year,
                f'{prefix}-TOTAL_FORMS': '1',
                f'{prefix}-INITIAL_FORMS': '0',
                f'{prefix}-MIN_NUM_FORMS': '1',
                f'{prefix}-MAX_NUM_FORMS': '1',
                f'{prefix}-0-jenis_cuti': 'Cuti Tahunan',
                f'{prefix}-0-alasan_cuti': 'Keperluan keluarga',
                f'{prefix}-0-tgl_mulai_cuti': mulai.isoformat(),
                f'{prefix}-0-tgl_akhir_cuti': (mulai + timedelta(days=1)).isoformat(),
                f'{prefix}-0-lama_cuti': '2',
                f'{prefix}-0-domisili_saat_cuti': 'Mataram',
            },
        )

        riwayat = RiwayatCuti.objects.get(
            pegawai=self.pegawai,
            usulan__status='pengajuan',
        )
        self.assertRedirects(
            response,
            reverse(
                'layanan_urls:pelimpahan_create',
                kwargs={'riwayat_pk': riwayat.pk},
            ),
            fetch_redirect_response=False,
        )
        self.assertEqual(riwayat.status_cuti, 'Belum')
        self.assertEqual(riwayat.jenis_cuti, 'Cuti Tahunan')
        self.assertFalse(riwayat.menggunakan_pola_shift)
        snapshot = riwayat.usulan.snapshot_saldo_cuti
        self.assertEqual(snapshot['versi'], 3)
        self.assertEqual(len(snapshot['rows']), 3)
        self.assertEqual(
            snapshot['total_tersedia'],
            sum(row['dapat_digunakan'] for row in snapshot['rows']),
        )
        self.assertEqual(
            snapshot['total_tersedia'],
            CheckCuti().cek_sisa_cuti(self.pegawai),
        )

    def test_superuser_diarahkan_dan_dapat_mengisi_pelimpahan_pegawai(self):
        self.client.force_login(self.superuser)
        mulai = date.today() + timedelta(days=10)
        selesai = mulai + timedelta(days=1)
        prefix = pengajuan_cuti_formset.get_default_prefix()
        response = self.client.post(
            reverse('layanan_urls:layanan_cuti_create_view'),
            {
                'pegawai': self.pegawai.pk,
                'layanan': self.jenis_layanan.pk,
                'status': 'pengajuan',
                'tahun': date.today().year,
                f'{prefix}-TOTAL_FORMS': '1',
                f'{prefix}-INITIAL_FORMS': '0',
                f'{prefix}-MIN_NUM_FORMS': '1',
                f'{prefix}-MAX_NUM_FORMS': '1',
                f'{prefix}-0-jenis_cuti': 'Cuti Alasan Penting',
                f'{prefix}-0-alasan_cuti': 'Keperluan keluarga',
                f'{prefix}-0-tgl_mulai_cuti': mulai.isoformat(),
                f'{prefix}-0-tgl_akhir_cuti': selesai.isoformat(),
                f'{prefix}-0-lama_cuti': '2',
                f'{prefix}-0-domisili_saat_cuti': 'Mataram',
            },
        )

        riwayat = RiwayatCuti.objects.get(
            pegawai=self.pegawai,
            jenis_cuti='Cuti Alasan Penting',
        )
        pelimpahan_url = reverse(
            'layanan_urls:pelimpahan_create',
            kwargs={'riwayat_pk': riwayat.pk},
        )
        self.assertRedirects(
            response,
            pelimpahan_url,
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.get(pelimpahan_url).status_code, 200)

        response = self.client.post(
            pelimpahan_url,
            {
                'penerima_tugas': self.pegawai_lain.pk,
                'deskripsi_tugas': 'Menangani tugas rutin selama cuti.',
                'tgl_mulai': mulai.isoformat(),
                'tgl_selesai': selesai.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 302)
        pelimpahan = PelimpahanTugas.objects.get(riwayat_cuti=riwayat)
        self.assertEqual(pelimpahan.pemberi_tugas, self.pegawai)
        self.assertEqual(pelimpahan.penerima_tugas, self.pegawai_lain)

    def test_cuti_tahunan_reguler_melewati_minggu_dan_hari_libur(self):
        mulai = date.today() + timedelta(days=10)
        while mulai.weekday() != 5:
            mulai += timedelta(days=1)
        HariLibur.objects.create(
            tanggal=mulai + timedelta(days=2),
            keterangan='Libur pengujian',
        )
        form = RiwayatPengajuanCutiForm(
            data={
                'jenis_cuti': 'Cuti Tahunan',
                'alasan_cuti': 'Keperluan keluarga',
                'tgl_mulai_cuti': mulai.isoformat(),
                'lama_cuti': '3',
                'domisili_saat_cuti': 'Mataram',
            },
            request=self.request_for(self.pegawai),
            target_pegawai=self.pegawai,
            tahun_pengajuan=date.today().year,
            check_cuti=CheckCuti(),
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data['tgl_akhir_cuti'],
            mulai + timedelta(days=4),
        )

    def test_cuti_tahunan_shift_tetap_menghitung_hari_libur(self):
        PolaKerjaPegawai.objects.filter(pegawai=self.pegawai).delete()
        PolaKerjaPegawai.objects.create(
            pegawai=self.pegawai,
            pola_kerja=PolaKerjaPegawai.SHIFT,
            berlaku_mulai=date.today().replace(month=1, day=1),
        )
        mulai = date.today() + timedelta(days=10)
        HariLibur.objects.create(
            tanggal=mulai + timedelta(days=1),
            keterangan='Libur pengujian shift',
        )
        form = RiwayatPengajuanCutiForm(
            data={
                'jenis_cuti': 'Cuti Tahunan',
                'alasan_cuti': 'Keperluan keluarga',
                'tgl_mulai_cuti': mulai.isoformat(),
                'lama_cuti': '3',
                'domisili_saat_cuti': 'Mataram',
            },
            request=self.request_for(self.pegawai),
            target_pegawai=self.pegawai,
            tahun_pengajuan=date.today().year,
            check_cuti=CheckCuti(),
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data['tgl_akhir_cuti'],
            mulai + timedelta(days=2),
        )

    def test_cuti_tahunan_baru_ditolak_tanpa_pola_kerja(self):
        PolaKerjaPegawai.objects.filter(pegawai=self.pegawai).delete()
        mulai = date.today() + timedelta(days=10)
        form = RiwayatPengajuanCutiForm(
            data={
                'jenis_cuti': 'Cuti Tahunan',
                'alasan_cuti': 'Keperluan keluarga',
                'tgl_mulai_cuti': mulai.isoformat(),
                'lama_cuti': '2',
                'domisili_saat_cuti': 'Mataram',
            },
            request=self.request_for(self.pegawai),
            target_pegawai=self.pegawai,
            tahun_pengajuan=date.today().year,
            check_cuti=CheckCuti(),
        )

        self.assertFalse(form.is_valid())
        self.assertIn('Pola kerja pegawai belum ditentukan', str(form.errors))
