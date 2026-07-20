from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from myaccount.models import ProfilSDM, Users
from myaccount.roles import ADMIN_DOKUMEN

from .document_registry import DOCUMENT_TYPES
from .export_views import csv_safe
from .models import DokumenSDM, RiwayatPendidikan


class DocumentExportCSVTests(TestCase):
    password = 'Password-Export-123!'

    @classmethod
    def setUpTestData(cls):
        cls.employee = cls.create_employee(
            'pegawai-export@example.com',
            'Pegawai Export',
            '199001',
        )
        cls.other_employee = cls.create_employee(
            'pegawai-export-lain@example.com',
            'Pegawai Lain',
            '199002',
        )
        cls.admin = cls.create_employee(
            'admin-export@example.com',
            'Admin Export',
            '199003',
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_DOKUMEN)
        cls.admin.groups.add(group)

        document_type = DokumenSDM.objects.create(
            nama='Riwayat Pendidikan',
            url='pendidikan',
        )
        RiwayatPendidikan.objects.create(
            pegawai=cls.employee,
            dokumen=document_type,
            pendidikan='Data Pendidikan Milik Sendiri',
            nama_sek='Universitas Sendiri',
        )
        RiwayatPendidikan.objects.create(
            pegawai=cls.other_employee,
            dokumen=document_type,
            pendidikan='Data Pendidikan Milik Pegawai Lain',
            nama_sek='Universitas Lain',
        )

    @classmethod
    def create_employee(cls, email, first_name, nip):
        user = Users.objects.create_user(
            email=email,
            first_name=first_name,
            last_name='',
            password=cls.password,
        )
        ProfilSDM.objects.create(
            user=user,
            nip=nip,
            no_hp='08123456789',
            email_pribadi=email,
        )
        return user

    def get_export(self, user, params=None, document_type='pendidikan'):
        self.client.force_login(user)
        return self.client.get(
            reverse(
                'riwayat_urls:document_export_csv',
                kwargs={'document_type': document_type},
            ),
            params or {},
        )

    @staticmethod
    def get_content(response):
        return b''.join(response.streaming_content).decode('utf-8-sig')

    def test_regular_user_exports_only_own_documents(self):
        response = self.get_export(
            self.employee,
            {'nip': self.other_employee.profil_user.nip},
        )

        content = self.get_content(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Data Pendidikan Milik Sendiri', content)
        self.assertNotIn('Data Pendidikan Milik Pegawai Lain', content)

    def test_document_admin_can_export_selected_employee(self):
        response = self.get_export(
            self.admin,
            {'nip': self.other_employee.profil_user.nip},
        )

        content = self.get_content(response)
        self.assertIn('Data Pendidikan Milik Pegawai Lain', content)
        self.assertNotIn('Data Pendidikan Milik Sendiri', content)

    def test_unknown_document_type_returns_404(self):
        response = self.get_export(self.employee, document_type='rahasia')
        self.assertEqual(response.status_code, 404)

    def test_all_registered_document_types_have_working_endpoint(self):
        for document_type in DOCUMENT_TYPES:
            with self.subTest(document_type=document_type):
                response = self.get_export(self.admin, document_type=document_type)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(self.get_content(response).startswith('Nama Pegawai,NIP,'))

    def test_csv_safe_prevents_spreadsheet_formula(self):
        self.assertEqual(csv_safe('=HYPERLINK("https://example.com")'), "'=HYPERLINK(\"https://example.com\")")
