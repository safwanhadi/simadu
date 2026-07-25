from datetime import date, timedelta

from django import forms
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dokumen.forms import RiwayatPengajuanCutiForm
from dokumen.models import DokumenSDM, RiwayatCuti, RiwayatPengangkatan
from myaccount.models import Users
from myaccount.roles import ADMIN_LAYANAN_CUTI

from .forms import LayananCutiForm, pengajuan_cuti_formset
from .models import JenisLayanan, LayananCuti
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
