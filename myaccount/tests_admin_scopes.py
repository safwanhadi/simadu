from datetime import date, timedelta

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase

from strukturorg.models import (
    Bidang, InstansiDaerah, SatuanKerjaInduk, SubBidang, UnitInstalasi,
    UnitOrganisasi,
)

from .admin_scopes import has_admin_scope
from .models import AdminScopeAssignment, Users
from django.urls import reverse

from .roles import ADMIN_AKUN, ADMIN_DISIPLIN, ADMIN_DOKUMEN


class AdminScopeAssignmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Users.objects.create_user(
            email='admin-scope@example.com',
            first_name='Admin',
            last_name='Scope',
            password='Password-Scope-123!',
        )
        cls.discipline_group, _ = Group.objects.get_or_create(
            name=ADMIN_DISIPLIN
        )
        cls.document_group, _ = Group.objects.get_or_create(
            name=ADMIN_DOKUMEN
        )
        cls.user.groups.add(cls.discipline_group)

        instansi = InstansiDaerah.objects.create(instansi='Instansi Scope')
        satker = SatuanKerjaInduk.objects.create(
            instansi_daerah=instansi,
            satuan_kerja='Satker Scope',
        )
        cls.unor = UnitOrganisasi.objects.create(
            satker_induk=satker,
            unor='Unit Organisasi Scope',
        )
        cls.bidang = Bidang.objects.create(
            unor=cls.unor,
            bidang='Bidang Scope',
        )
        cls.other_bidang = Bidang.objects.create(
            unor=cls.unor,
            bidang='Bidang Lain',
        )
        sub_bidang = SubBidang.objects.create(
            bidang=cls.bidang,
            sub_bidang='Sub Bidang Scope',
        )
        cls.instalasi = UnitInstalasi.objects.create(
            sub_bidang=sub_bidang,
            instalasi='Instalasi Scope',
        )

    def test_scope_tetap_membutuhkan_group_admin(self):
        AdminScopeAssignment.objects.create(
            user=self.user,
            group=self.document_group,
            scope_type=AdminScopeAssignment.GLOBAL,
        )

        self.assertFalse(
            has_admin_scope(self.user, ADMIN_DOKUMEN, self.instalasi)
        )

    def test_scope_induk_mencakup_struktur_turunan(self):
        AdminScopeAssignment.objects.create(
            user=self.user,
            group=self.discipline_group,
            scope_type=AdminScopeAssignment.BIDANG,
            bidang=self.bidang,
        )

        self.assertTrue(
            has_admin_scope(self.user, ADMIN_DISIPLIN, self.instalasi)
        )
        self.assertFalse(
            has_admin_scope(self.user, ADMIN_DISIPLIN, self.other_bidang)
        )

    def test_scope_kedaluwarsa_tidak_memberikan_akses(self):
        yesterday = date.today() - timedelta(days=1)
        AdminScopeAssignment.objects.create(
            user=self.user,
            group=self.discipline_group,
            scope_type=AdminScopeAssignment.GLOBAL,
            valid_from=yesterday,
            valid_until=yesterday,
        )

        self.assertFalse(
            has_admin_scope(self.user, ADMIN_DISIPLIN, self.instalasi)
        )

    def test_target_harus_sesuai_dengan_jenis_scope(self):
        assignment = AdminScopeAssignment(
            user=self.user,
            group=self.discipline_group,
            scope_type=AdminScopeAssignment.BIDANG,
            unit_organisasi=self.unor,
        )

        with self.assertRaises(ValidationError):
            assignment.save()

    def test_group_non_admin_tidak_dapat_diberi_scope(self):
        non_admin_group = Group.objects.create(name='Grup Non Admin')
        assignment = AdminScopeAssignment(
            user=self.user,
            group=non_admin_group,
            scope_type=AdminScopeAssignment.GLOBAL,
        )

        with self.assertRaises(ValidationError):
            assignment.save()

    def test_scope_yang_sama_tidak_dapat_diduplikasi(self):
        values = {
            'user': self.user,
            'group': self.discipline_group,
            'scope_type': AdminScopeAssignment.BIDANG,
            'bidang': self.bidang,
        }
        AdminScopeAssignment.objects.create(**values)

        with self.assertRaises(ValidationError):
            AdminScopeAssignment.objects.create(**values)


class AdminScopeAssignmentCrudTests(TestCase):
    password = 'Password-Admin-Scope-123!'

    @classmethod
    def setUpTestData(cls):
        cls.admin = Users.objects.create_user(
            email='admin-akun-scope@example.com',
            first_name='Admin',
            last_name='Akun Scope',
            password=cls.password,
        )
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_AKUN)
        cls.admin.groups.add(admin_group)

        cls.target = Users.objects.create_user(
            email='target-scope@example.com',
            first_name='Target',
            last_name='Scope',
            password=cls.password,
        )
        cls.regular_user = Users.objects.create_user(
            email='regular-scope@example.com',
            first_name='Regular',
            last_name='Scope',
            password=cls.password,
        )
        cls.discipline_group, _ = Group.objects.get_or_create(
            name=ADMIN_DISIPLIN
        )
        cls.target.groups.add(cls.discipline_group)

        instansi = InstansiDaerah.objects.create(instansi='Instansi CRUD')
        satker = SatuanKerjaInduk.objects.create(
            instansi_daerah=instansi,
            satuan_kerja='Satker CRUD',
        )
        cls.unor = UnitOrganisasi.objects.create(
            satker_induk=satker,
            unor='Unit Organisasi CRUD',
        )
        cls.bidang = Bidang.objects.create(
            unor=cls.unor,
            bidang='Bidang CRUD',
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def assignment_data(self, **overrides):
        data = {
            'user': self.target.pk,
            'group': self.discipline_group.pk,
            'scope_type': AdminScopeAssignment.BIDANG,
            'bidang': self.bidang.pk,
            'valid_from': date.today().isoformat(),
            'valid_until': '',
            'is_active': 'on',
        }
        data.update(overrides)
        return data

    def test_admin_akun_dapat_membuka_daftar_dan_form(self):
        list_response = self.client.get(
            reverse('myaccount_urls:admin_scope_list')
        )
        form_response = self.client.get(
            reverse('myaccount_urls:admin_scope_create')
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(form_response.status_code, 200)
        self.assertContains(list_response, 'Cakupan Peran Admin')
        self.assertContains(form_response, 'Tambah Cakupan Admin')
        self.assertContains(form_response, 'admin-scope-select2')
        self.assertContains(form_response, "select.select2({", html=False)

    def test_admin_akun_dapat_membuat_scope(self):
        response = self.client.post(
            reverse('myaccount_urls:admin_scope_create'),
            self.assignment_data(),
        )

        assignment = AdminScopeAssignment.objects.get(user=self.target)
        self.assertRedirects(
            response,
            reverse('myaccount_urls:admin_scope_list'),
        )
        self.assertEqual(assignment.group, self.discipline_group)
        self.assertEqual(assignment.bidang, self.bidang)

    def test_user_harus_memiliki_role_yang_dipilih(self):
        self.target.groups.remove(self.discipline_group)

        response = self.client.post(
            reverse('myaccount_urls:admin_scope_create'),
            self.assignment_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pengguna belum memiliki peran admin ini')
        self.assertFalse(AdminScopeAssignment.objects.exists())

    def test_admin_akun_dapat_mengubah_scope_menjadi_global(self):
        assignment = AdminScopeAssignment.objects.create(
            user=self.target,
            group=self.discipline_group,
            scope_type=AdminScopeAssignment.BIDANG,
            bidang=self.bidang,
        )

        response = self.client.post(
            reverse(
                'myaccount_urls:admin_scope_update',
                args=[assignment.pk],
            ),
            self.assignment_data(
                scope_type=AdminScopeAssignment.GLOBAL,
                bidang='',
            ),
        )

        assignment.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('myaccount_urls:admin_scope_list'),
        )
        self.assertEqual(assignment.scope_type, AdminScopeAssignment.GLOBAL)
        self.assertIsNone(assignment.bidang)

    def test_admin_akun_dapat_menghapus_scope(self):
        assignment = AdminScopeAssignment.objects.create(
            user=self.target,
            group=self.discipline_group,
            scope_type=AdminScopeAssignment.GLOBAL,
        )

        response = self.client.post(
            reverse(
                'myaccount_urls:admin_scope_delete',
                args=[assignment.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse('myaccount_urls:admin_scope_list'),
        )
        self.assertFalse(
            AdminScopeAssignment.objects.filter(pk=assignment.pk).exists()
        )

    def test_user_biasa_tidak_dapat_mengelola_scope(self):
        self.client.force_login(self.regular_user)

        list_response = self.client.get(
            reverse('myaccount_urls:admin_scope_list')
        )
        create_response = self.client.post(
            reverse('myaccount_urls:admin_scope_create'),
            self.assignment_data(),
        )

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(create_response.status_code, 403)
        self.assertFalse(AdminScopeAssignment.objects.exists())
