from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase

from dokumen.models import RiwayatCuti, RiwayatPenempatan
from myaccount.models import AdminScopeAssignment, Users
from myaccount.roles import ADMIN_LAYANAN_CUTI
from strukturorg.models import (
    Bidang, InstansiDaerah, SatuanKerjaInduk, SubBidang, UnitInstalasi,
    UnitOrganisasi,
)

from .access.cuti import (
    can_manage_cuti_history,
    filter_cuti_history_queryset,
    filter_queryset_for_leave_admin,
    is_leave_admin,
)
from .models import JenisLayanan, LayananCuti


class LeaveAdminScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Users.objects.create_user(
            email='admin-cuti-scope@example.com',
            first_name='Admin',
            last_name='Scope Cuti',
            password='password-test',
        )
        cls.employee_in_scope = Users.objects.create_user(
            email='pegawai-dalam-scope@example.com',
            first_name='Pegawai',
            last_name='Dalam Scope',
            password='password-test',
        )
        cls.employee_outside_scope = Users.objects.create_user(
            email='pegawai-luar-scope@example.com',
            first_name='Pegawai',
            last_name='Luar Scope',
            password='password-test',
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_LAYANAN_CUTI)
        cls.admin.groups.add(group)

        instansi = InstansiDaerah.objects.create(instansi='Instansi Scope Cuti')
        satker = SatuanKerjaInduk.objects.create(
            instansi_daerah=instansi,
            satuan_kerja='Satker Scope Cuti',
        )
        unor = UnitOrganisasi.objects.create(
            satker_induk=satker,
            unor='Unit Scope Cuti',
        )
        cls.bidang = Bidang.objects.create(
            unor=unor,
            bidang='Bidang Dalam Scope',
        )
        bidang_lain = Bidang.objects.create(
            unor=unor,
            bidang='Bidang Luar Scope',
        )
        sub_bidang = SubBidang.objects.create(
            bidang=cls.bidang,
            sub_bidang='Sub Dalam Scope',
        )
        sub_bidang_lain = SubBidang.objects.create(
            bidang=bidang_lain,
            sub_bidang='Sub Luar Scope',
        )
        instalasi = UnitInstalasi.objects.create(
            sub_bidang=sub_bidang,
            instalasi='Instalasi Dalam Scope',
        )
        instalasi_lain = UnitInstalasi.objects.create(
            sub_bidang=sub_bidang_lain,
            instalasi='Instalasi Luar Scope',
        )
        RiwayatPenempatan.objects.create(
            pegawai=cls.employee_in_scope,
            penempatan_level4=instalasi,
            status=True,
        )
        RiwayatPenempatan.objects.create(
            pegawai=cls.employee_outside_scope,
            penempatan_level4=instalasi_lain,
            status=True,
        )
        AdminScopeAssignment.objects.create(
            user=cls.admin,
            group=group,
            scope_type=AdminScopeAssignment.BIDANG,
            bidang=cls.bidang,
        )

        layanan_jenis = JenisLayanan.objects.create(
            nama='Cuti Scope',
            url='cuti-scope-test',
            status=True,
        )
        cls.leave_in_scope = LayananCuti.objects.create(
            pegawai=cls.employee_in_scope,
            layanan=layanan_jenis,
            status='pengajuan',
            tahun=date.today().year,
        )
        cls.leave_outside_scope = LayananCuti.objects.create(
            pegawai=cls.employee_outside_scope,
            layanan=layanan_jenis,
            status='pengajuan',
            tahun=date.today().year,
        )
        cls.history_in_scope = RiwayatCuti.objects.create(
            pegawai=cls.employee_in_scope,
            jenis_cuti='Cuti Tahunan',
            tahun_cuti=date.today().year,
        )
        cls.history_outside_scope = RiwayatCuti.objects.create(
            pegawai=cls.employee_outside_scope,
            jenis_cuti='Cuti Tahunan',
            tahun_cuti=date.today().year,
        )

    def test_role_dan_assignment_hanya_berlaku_dalam_scope(self):
        self.assertTrue(is_leave_admin(self.admin, self.employee_in_scope))
        self.assertFalse(is_leave_admin(self.admin, self.employee_outside_scope))

    def test_queryset_admin_dibatasi_ke_scope(self):
        scoped = filter_queryset_for_leave_admin(
            LayananCuti.objects.all(),
            self.admin,
        )

        self.assertQuerySetEqual(
            scoped.order_by('pk'),
            [self.leave_in_scope],
        )

    def test_group_tanpa_assignment_tidak_memberikan_akses(self):
        AdminScopeAssignment.objects.filter(user=self.admin).delete()

        self.assertFalse(is_leave_admin(self.admin))
        self.assertFalse(
            filter_queryset_for_leave_admin(
                LayananCuti.objects.all(),
                self.admin,
            ).exists()
        )

    def test_riwayat_cuti_menggunakan_scope_yang_sama(self):
        queryset = filter_cuti_history_queryset(
            RiwayatCuti.objects.all(),
            self.admin,
        )
        self.assertQuerySetEqual(
            queryset,
            [self.history_in_scope],
            ordered=False,
        )
        self.assertTrue(
            can_manage_cuti_history(self.admin, self.history_in_scope)
        )
        self.assertFalse(
            can_manage_cuti_history(
                self.admin,
                self.history_outside_scope,
            )
        )
