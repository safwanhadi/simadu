from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from layanan.access.cuti import can_supervise_employee, filter_users_for_leave_supervisor
from layanan.models import PelimpahanTugas
from layanan.utils import resolve_atasan_level3_for_level4
from myaccount.models import CoordinationAssignment, Users
from myaccount.roles import ADMIN_AKUN
from strukturorg.models import InstansiDaerah, SatuanKerjaInduk, UnitOrganisasi, PejabatStruktur


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    SESSION_ENGINE='django.contrib.sessions.backends.db',
)
class CoordinationAssignmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Users.objects.create_user(email='admin-koordinasi@example.test', first_name='Admin', last_name='Koordinasi', password='Password-123!')
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_AKUN)
        cls.admin.groups.add(admin_group)
        cls.coordinator = Users.objects.create_user(email='katimker@example.test', first_name='Ketua', last_name='Tim Kerja', password='Password-123!')
        cls.employee = Users.objects.create_user(email='staf@example.test', first_name='Staf', last_name='Pendukung', password='Password-123!')
        instansi = InstansiDaerah.objects.create(instansi='Instansi Uji')
        satker = SatuanKerjaInduk.objects.create(instansi_daerah=instansi, satuan_kerja='Satker Uji')
        cls.unit = UnitOrganisasi.objects.create(satker_induk=satker, unor='Tim Kerja Uji')
        cls.appointment = PejabatStruktur.objects.create(
            unit_organisasi=cls.unit,
            pejabat=cls.coordinator,
            nama_jabatan='Ketua Tim Kerja',
        )

    def test_penugasan_staf_tidak_mengubah_jabatan_katimker(self):
        assignment = CoordinationAssignment.objects.create(
            coordinator=self.coordinator,
            employee=self.employee,
            relation_type=CoordinationAssignment.SUPPORT_STAFF,
        )

        self.appointment.refresh_from_db()
        self.assertTrue(self.appointment.is_active)
        self.assertTrue(can_supervise_employee(self.coordinator, self.employee))
        self.assertIn(
            self.employee,
            filter_users_for_leave_supervisor(Users.objects.all(), self.coordinator),
        )
        self.assertTrue(assignment.is_active)

    def test_relasi_diri_sendiri_ditolak(self):
        assignment = CoordinationAssignment(
            coordinator=self.coordinator,
            employee=self.coordinator,
        )
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_atasan_langsung_menjadi_penyetuju_pelimpahan_cuti(self):
        CoordinationAssignment.objects.create(
            coordinator=self.coordinator,
            employee=self.employee,
            relation_type=CoordinationAssignment.DIRECT_SUPERVISOR,
        )
        pelimpahan = PelimpahanTugas(
            pemberi_tugas=self.employee,
            penerima_tugas=self.admin,
        )

        self.assertTrue(pelimpahan.requires_atasan_approval())
        self.assertEqual(
            resolve_atasan_level3_for_level4(self.employee),
            self.coordinator,
        )

    def test_staf_pendukung_tidak_otomatis_menjadi_penyetuju(self):
        CoordinationAssignment.objects.create(
            coordinator=self.coordinator,
            employee=self.employee,
            relation_type=CoordinationAssignment.SUPPORT_STAFF,
        )

        self.assertIsNone(resolve_atasan_level3_for_level4(self.employee))

    def test_admin_akun_dapat_membuat_dan_mengakhiri_penugasan(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('myaccount_urls:coordination_assignment_management'),
            {
                'coordinator': self.coordinator.pk,
                'employee': self.employee.pk,
                'relation_type': CoordinationAssignment.SUPPORT_STAFF,
                'valid_from': '2026-09-04',
                'notes': 'Staf pendukung Tim Kerja',
            },
        )
        self.assertRedirects(response, reverse('myaccount_urls:coordination_assignment_management'))
        assignment = CoordinationAssignment.objects.get()

        response = self.client.post(
            reverse('myaccount_urls:coordination_assignment_deactivate', args=[assignment.pk]),
            {'valid_until': '2026-09-04'},
        )
        self.assertRedirects(response, reverse('myaccount_urls:coordination_assignment_management'))
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)
