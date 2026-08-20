from django.contrib.auth.models import Group
from django.test import TestCase
from types import SimpleNamespace

from dokumen.models import RiwayatPenempatan
from myaccount.models import AdminScopeAssignment, Users
from myaccount.roles import ADMIN_DISIPLIN
from strukturorg.models import (
    Bidang,
    InstansiDaerah,
    SatuanKerjaInduk,
    SubBidang,
    UnitInstalasi,
    UnitOrganisasi,
)
from strukturorg.models import PejabatStruktur

from .access import (
    can_approve_discipline_installation,
    can_approve_discipline_schedule,
    can_delete_discipline_schedule,
    filter_installations_for_discipline_admin,
    filter_installations_for_structural_officer,
    filter_users_for_structural_officer,
    is_discipline_structural_officer,
    is_discipline_admin,
)


class DisciplineAdminScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Users.objects.create_user(
            email='discipline-scope@example.com',
            first_name='Admin',
            last_name='Disiplin',
            password='Scope-test-123!',
        )
        cls.group, _ = Group.objects.get_or_create(name=ADMIN_DISIPLIN)
        cls.admin.groups.add(cls.group)

        instansi = InstansiDaerah.objects.create(instansi='Instansi')
        satker = SatuanKerjaInduk.objects.create(
            instansi_daerah=instansi,
            satuan_kerja='Satker',
        )
        unor = UnitOrganisasi.objects.create(
            satker_induk=satker,
            unor='Unor',
        )
        cls.bidang = Bidang.objects.create(unor=unor, bidang='Bidang A')
        bidang_lain = Bidang.objects.create(unor=unor, bidang='Bidang B')
        sub_bidang = SubBidang.objects.create(
            bidang=cls.bidang,
            sub_bidang='Sub A',
        )
        sub_bidang_lain = SubBidang.objects.create(
            bidang=bidang_lain,
            sub_bidang='Sub B',
        )
        cls.allowed = UnitInstalasi.objects.create(
            sub_bidang=sub_bidang,
            instalasi='Instalasi A',
        )
        cls.denied = UnitInstalasi.objects.create(
            sub_bidang=sub_bidang_lain,
            instalasi='Instalasi B',
        )
        cls.employee = Users.objects.create_user(
            email='employee-scope@example.com',
            first_name='Pegawai',
            last_name='Scope',
            password='Scope-test-123!',
        )
        RiwayatPenempatan.objects.create(
            pegawai=cls.employee,
            penempatan_level4=cls.allowed,
            status=True,
        )
        cls.sub_bidang_leader = Users.objects.create_user(
            email='leader-scope@example.com',
            first_name='Kepala',
            last_name='Subbidang',
            password='Scope-test-123!',
        )
        PejabatStruktur.objects.create(
            pejabat=cls.sub_bidang_leader,
            sub_bidang=sub_bidang,
            nama_jabatan='Kepala Sub Bidang',
        )
        cls.installation_leader = Users.objects.create_user(
            email='installation-leader@example.com',
            first_name='Kepala',
            last_name='Instalasi',
            password='Scope-test-123!',
        )
        PejabatStruktur.objects.create(
            pejabat=cls.installation_leader,
            unit_instalasi=cls.allowed,
            nama_jabatan='Kepala Instalasi',
        )

    def test_role_tanpa_assignment_tidak_dianggap_admin_modul(self):
        self.assertFalse(is_discipline_admin(self.admin))
        self.assertFalse(
            filter_installations_for_discipline_admin(
                UnitInstalasi.objects.all(),
                self.admin,
            ).exists()
        )

    def test_scope_bidang_hanya_mencakup_instalasi_turunannya(self):
        AdminScopeAssignment.objects.create(
            user=self.admin,
            group=self.group,
            scope_type=AdminScopeAssignment.BIDANG,
            bidang=self.bidang,
        )

        queryset = filter_installations_for_discipline_admin(
            UnitInstalasi.objects.all(),
            self.admin,
        )

        self.assertTrue(is_discipline_admin(self.admin))
        self.assertTrue(
            is_discipline_admin(self.admin, structure=self.allowed)
        )
        self.assertFalse(
            is_discipline_admin(self.admin, structure=self.denied)
        )
        self.assertQuerySetEqual(queryset, [self.allowed], ordered=False)

    def test_pejabat_hanya_melihat_turunan_struktur_yang_dipimpin(self):
        installations = filter_installations_for_structural_officer(
            UnitInstalasi.objects.all(),
            self.sub_bidang_leader,
        )
        employees = filter_users_for_structural_officer(
            Users.objects.all(),
            self.sub_bidang_leader,
        )

        self.assertQuerySetEqual(
            installations,
            [self.allowed],
            ordered=False,
        )
        self.assertQuerySetEqual(
            employees,
            [self.employee],
            ordered=False,
        )
        self.assertTrue(is_discipline_structural_officer(
            self.sub_bidang_leader,
            employee=self.employee,
        ))

    def test_persetujuan_jadwal_hanya_untuk_kepala_ruangan(self):
        self.assertTrue(can_approve_discipline_schedule(
            self.installation_leader,
            self.employee,
        ))
        self.assertFalse(can_approve_discipline_schedule(
            self.sub_bidang_leader,
            self.employee,
        ))
        self.assertTrue(can_approve_discipline_installation(
            self.installation_leader,
            self.allowed,
        ))
        self.assertFalse(can_approve_discipline_installation(
            self.sub_bidang_leader,
            self.allowed,
        ))

    def test_pejabat_hanya_dapat_menghapus_jadwal_draft_atau_ditolak(self):
        for status in ('draft', 'ditolak'):
            self.assertTrue(can_delete_discipline_schedule(
                self.installation_leader,
                SimpleNamespace(pegawai=self.employee, status=status),
            ))
        for status in ('diajukan', 'disetujui'):
            self.assertFalse(can_delete_discipline_schedule(
                self.installation_leader,
                SimpleNamespace(pegawai=self.employee, status=status),
            ))
