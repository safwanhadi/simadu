from django.contrib.auth.models import Group
from django.test import TestCase

from dokumen.models import RiwayatDiklat, RiwayatPenempatan
from myaccount.models import AdminScopeAssignment, Users
from myaccount.roles import ADMIN_LAYANAN_DIKLAT
from strukturorg.models import (
    Bidang,
    InstansiDaerah,
    PejabatStruktur,
    SatuanKerjaInduk,
    SubBidang,
    UnitInstalasi,
    UnitOrganisasi,
)

from .access.diklat import (
    can_administer_diklat,
    can_manage_diklat_history,
    can_view_diklat,
    filter_diklat_history_queryset,
    filter_queryset_for_diklat_admin,
    is_diklat_verifier,
)
from .models import LayananUsulanDiklat, VerifikasiDiklat


class DiklatScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        instansi = InstansiDaerah.objects.create(instansi='Instansi Diklat')
        satker = SatuanKerjaInduk.objects.create(
            instansi_daerah=instansi,
            satuan_kerja='Satker Diklat',
        )
        unor = UnitOrganisasi.objects.create(
            satker_induk=satker,
            unor='Unor Diklat',
        )
        cls.bidang = Bidang.objects.create(unor=unor, bidang='Bidang A')
        other_bidang = Bidang.objects.create(unor=unor, bidang='Bidang B')
        cls.sub_bidang = SubBidang.objects.create(
            bidang=cls.bidang,
            sub_bidang='Sub A',
        )
        other_sub = SubBidang.objects.create(
            bidang=other_bidang,
            sub_bidang='Sub B',
        )
        cls.installation = UnitInstalasi.objects.create(
            sub_bidang=cls.sub_bidang,
            instalasi='Instalasi A',
        )
        other_installation = UnitInstalasi.objects.create(
            sub_bidang=other_sub,
            instalasi='Instalasi B',
        )

        cls.employee = cls._user('pegawai-diklat@example.com', 'Pegawai')
        cls.other_employee = cls._user(
            'pegawai-diklat-lain@example.com',
            'Pegawai Lain',
        )
        RiwayatPenempatan.objects.create(
            pegawai=cls.employee,
            penempatan_level4=cls.installation,
            status=True,
        )
        RiwayatPenempatan.objects.create(
            pegawai=cls.other_employee,
            penempatan_level4=other_installation,
            status=True,
        )

        cls.admin = cls._user('admin-diklat@example.com', 'Admin Diklat')
        group, _ = Group.objects.get_or_create(name=ADMIN_LAYANAN_DIKLAT)
        cls.admin.groups.add(group)
        AdminScopeAssignment.objects.create(
            user=cls.admin,
            group=group,
            scope_type=AdminScopeAssignment.BIDANG,
            bidang=cls.bidang,
        )

        cls.supervisor = cls._user('atasan-diklat@example.com', 'Atasan')
        PejabatStruktur.objects.create(
            pejabat=cls.supervisor,
            sub_bidang=cls.sub_bidang,
            nama_jabatan='Kepala Sub Bidang',
        )
        cls.verifier = cls._user('verifikator-diklat@example.com', 'Verifikator')

        cls.proposal = cls._proposal_for(cls.employee, 'Diklat A')
        cls.other_proposal = cls._proposal_for(
            cls.other_employee,
            'Diklat B',
        )
        VerifikasiDiklat.objects.create(
            layanan_diklat=cls.proposal,
            verifikator1=cls.verifier,
        )

    @classmethod
    def _user(cls, email, first_name):
        return Users.objects.create_user(
            email=email,
            first_name=first_name,
            last_name='Scope',
            password='Diklat-scope-123!',
        )

    @classmethod
    def _proposal_for(cls, employee, name):
        proposal = LayananUsulanDiklat.objects.create()
        history = RiwayatDiklat.objects.create(
            usulan=proposal,
            jenis_diklat='Pelatihan',
            nama_diklat=name,
            penyelenggara='RS',
        )
        history.pegawai.add(employee)
        return proposal

    def test_admin_hanya_mengelola_usulan_dalam_assignment(self):
        queryset = filter_queryset_for_diklat_admin(
            LayananUsulanDiklat.objects.all(),
            self.admin,
        )
        self.assertQuerySetEqual(
            queryset,
            [self.proposal],
            ordered=False,
        )
        self.assertTrue(can_administer_diklat(self.admin, self.proposal))
        self.assertFalse(
            can_administer_diklat(self.admin, self.other_proposal)
        )

    def test_riwayat_app_dokumen_menggunakan_scope_diklat_yang_sama(self):
        history = RiwayatDiklat.objects.get(usulan=self.proposal)
        other_history = RiwayatDiklat.objects.get(
            usulan=self.other_proposal,
        )
        queryset = filter_diklat_history_queryset(
            RiwayatDiklat.objects.all(),
            self.admin,
        )

        self.assertQuerySetEqual(queryset, [history], ordered=False)
        self.assertTrue(
            can_manage_diklat_history(self.admin, history)
        )
        self.assertFalse(
            can_manage_diklat_history(self.admin, other_history)
        )

    def test_pejabat_hanya_melihat_usulan_bawahannya(self):
        self.assertTrue(can_view_diklat(self.supervisor, self.proposal))
        self.assertFalse(
            can_view_diklat(self.supervisor, self.other_proposal)
        )

    def test_verifikator_hanya_dapat_mengisi_level_snapshotnya(self):
        self.assertTrue(is_diklat_verifier(
            self.verifier,
            self.proposal,
            level='1',
        ))
        self.assertFalse(is_diklat_verifier(
            self.verifier,
            self.proposal,
            level='2',
        ))
