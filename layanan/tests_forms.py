from django import forms
from django.test import TestCase
from django.urls import reverse

from dokumen.models import RiwayatPendidikan
from myaccount.models import Users

from .forms import LayananNaikJabatanForm, LayananNaikPangkatForm


class LayananNaikPangkatFormTests(TestCase):
    def test_form_pegawai_dapat_diinisialisasi_untuk_user_biasa(self):
        user = Users.objects.create_user(
            email='form-pangkat@example.com',
            first_name='Form',
            last_name='Pangkat',
            password=None,
        )

        form = LayananNaikPangkatForm(user=user)

        self.assertEqual(
            list(form.fields['pegawai'].queryset.values_list('pk', flat=True)),
            [user.pk],
        )
        self.assertEqual(form.fields['pegawai'].initial, user)
        self.assertIsInstance(form.fields['pegawai'].widget, forms.HiddenInput)

    def test_admin_mendapat_dropdown_dokumen_milik_pegawai_yang_dipilih(self):
        admin = Users.objects.create_superuser(
            email='admin-promosi@example.com',
            password='test-password',
        )
        employee = Users.objects.create_user(
            email='pegawai-promosi@example.com',
            password=None,
        )
        education = RiwayatPendidikan.objects.create(
            pegawai=employee,
            level_pend='S1',
            pendidikan='Administrasi Publik',
            nama_sek='Universitas Contoh',
            no_ijazah='IJZ-001',
        )

        pangkat_form = LayananNaikPangkatForm(
            data={'pegawai': employee.pk},
            user=admin,
        )
        jabatan_form = LayananNaikJabatanForm(
            data={'pegawai': employee.pk},
            user=admin,
        )

        self.assertIn(education, pangkat_form.fields['pendidikan'].queryset)
        self.assertIn(education, jabatan_form.fields['pendidikan'].queryset)

    def test_api_dropdown_mengembalikan_data_baru_milik_pegawai(self):
        employee = Users.objects.create_user(
            email='dropdown-promosi@example.com',
            password='test-password',
        )
        education = RiwayatPendidikan.objects.create(
            pegawai=employee,
            level_pend='S1',
            pendidikan='Manajemen',
            nama_sek='Universitas Contoh',
            no_ijazah='IJZ-002',
        )
        self.client.force_login(employee)

        response = self.client.get(
            reverse(
                'layanan_urls:promotion_supporting_options',
                kwargs={'service': 'pangkat', 'employee_id': employee.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['fields']['pendidikan'],
            [{'id': education.pk, 'text': str(education)}],
        )

    def test_api_dropdown_menolak_pegawai_di_luar_scope(self):
        employee = Users.objects.create_user(
            email='pemilik-promosi@example.com',
            password='test-password',
        )
        other_employee = Users.objects.create_user(
            email='pegawai-lain-promosi@example.com',
            password=None,
        )
        self.client.force_login(employee)

        response = self.client.get(
            reverse(
                'layanan_urls:promotion_supporting_options',
                kwargs={'service': 'jabatan', 'employee_id': other_employee.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
