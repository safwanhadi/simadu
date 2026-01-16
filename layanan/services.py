from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, F, Value, IntegerField, Case, When, Count, Q, OuterRef, Subquery
from django.db.models.functions import Coalesce, Greatest
from django.conf import settings
from .models import RiwayatCuti, LayananCuti, VerifikasiCuti, RiwayatPengangkatan
from dokumen.models import KlaimCutiTunda
from typing import Optional

class CheckCuti:
    CUTI_TAHUNAN = 'Cuti Tahunan'
    STATUS_KURANGI_CUTI = ['Selesai', 'Proses', 'Tunda']
    # Default kebijakan cuti tunda. Atasan (kasi/kasubbag) dapat mengaktifkan/menonaktifkan per permintaan.
    BASE_ALLOW_CUTI_TUNDA = getattr(settings, 'ALLOW_CUTI_TUNDA', True)
    HAK_CUTI_TAHUNAN = 12
    MAKSIMAL_KOMPENSASI_TAHUN = 6  # hak yang bisa diambil per tahun sebelumnya

    def set_allow_cuti_tunda(self, allow: Optional[bool] = None):
        """Simpan kebijakan cuti tunda di instance (default ke konfigurasi global)."""

        self._allow_cuti_tunda_cache = self.BASE_ALLOW_CUTI_TUNDA if allow is None else bool(allow)

    @property
    def allow_cuti_tunda(self) -> bool:
        """Kebijakan cuti tunda yang aktif untuk request saat ini."""

        return getattr(self, '_allow_cuti_tunda_cache', self.BASE_ALLOW_CUTI_TUNDA)

    def _get_penempatan_level(self, user) -> Optional[int]:
        """Kembalikan level penempatan aktif pegawai (1=Unor, 2=Bidang, 3=SubBidang, 4=Instalasi)."""

        if not user or not getattr(user, 'is_authenticated', False):
            return None

        riwayat = (
            user.riwayat_penempatan.filter(status=True)
            .order_by('-updated_at', '-id')
            .first()
            if hasattr(user, 'riwayat_penempatan')
            else None
        )
        if not riwayat:
            return None

        if riwayat.penempatan_level4:
            return 4
        if riwayat.penempatan_level3:
            return 3
        if riwayat.penempatan_level2:
            return 2
        if riwayat.penempatan_level1:
            return 1
        return None

    #untuk saat ini method ini tidak digunakan (masih menggunakan method bawaan dari aplikasi sebelumnya)
    def _get_admin_scope_level(self, user) -> Optional[int]:
        """Level kewenangan atasan berdasar profil_admin (1=Unor, 2=Bidang, 3=SubBidang, 4=Instalasi)."""

        profil_admin = getattr(user, 'profil_admin', None)
        if not profil_admin:
            return None

        if profil_admin.unor:
            return 1
        if profil_admin.bidang:
            return 2
        if profil_admin.sub_bidang:
            return 3
        if getattr(profil_admin, 'instalasi', None) and profil_admin.instalasi.exists():
            return 4
        return None

    #untuk saat ini method ini tidak digunakan (masih menggunakan method bawaan dari aplikasi sebelumnya)
    def can_manage_cuti_tunda(self, user, target_user=None, respect_policy: bool = True) -> bool:
        """
        Tentukan apakah *user* berhak memutuskan cuti tunda.

        - Minimal level kewenangan: SubBidang (kasi/kasubbag). Instalasi saja tidak cukup.
        - Rantai persetujuan: atasan satu tingkat di atas pemohon, misal:
          * Pegawai level instalasi → disetujui atasan SubBidang.
          * Kasi/Kasubbag (SubBidang) → disetujui atasan Bidang.
          * Kepala Bidang → disetujui atasan Unor.
        - Superuser selalu diizinkan.
        """

        if respect_policy and not self.allow_cuti_tunda:
            return False

        if not user or not getattr(user, 'is_authenticated', False):
            return False

        if user.is_superuser:
            return True

        admin_level = self._get_admin_scope_level(user)
        if not admin_level or admin_level > 3:  # minimal SubBidang
            return False

        if target_user:
            target_level = self._get_penempatan_level(target_user)
            if not target_level:
                return False
            return admin_level == target_level - 1

        return True

    def _status_pengurang_cuti(self):
        """Status yang mengurangi jatah cuti, bisa tanpa Tunda bila kebijakan meniadakan cuti tunda."""
        if self.allow_cuti_tunda:
            return self.STATUS_KURANGI_CUTI
        return [status for status in self.STATUS_KURANGI_CUTI if status != 'Tunda']

 # ------------------------------------------------------------------
    # 1) SUM PENGGUNAAN CUTI TAHUNAN PER TAHUN (pakai KlaimCutiTunda)
    # ------------------------------------------------------------------
    def _sum_cuti_diambil_per_tahun(self, user):
        """
        Dict {tahun: total_hari} = total hari cuti tahunan yang benar-benar DIAMBIL
        pada tahun itu (berdasarkan lama_cuti).
        Tidak peduli sumbernya (hak berjalan / tunda / kompensasi).
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return {}

        hasil = {}
        qs = (
            RiwayatCuti.objects
            .filter(
                pegawai=user,
                jenis_cuti=self.CUTI_TAHUNAN,
                status_cuti__in=['Selesai', 'Proses'],
            )
            .values('tahun_cuti')
            .annotate(total=Sum('lama_cuti'))
        )

        for row in qs:
            tahun = row['tahun_cuti']
            if tahun is None:
                continue
            hasil[int(tahun)] = int(row['total'] or 0)

        return hasil

    def _sum_cuti_per_tahun(self, user):
        """
        Menghitung pemakaian yang MENGURANGI hak cuti tahun berjalan, dengan konsep:
        - Normal: max(0, lama_cuti - total_klaim_tunda_untuk_cuti_ini)
        - pakai_tunda_saja: 0
        """

        if not user or not getattr(user, "is_authenticated", False):
            return {}

        # Subquery: total klaim tunda untuk tiap RiwayatCuti (cuti_klaim)
        klaim_total_sq = (
            KlaimCutiTunda.objects
            .filter(cuti_klaim_id=OuterRef("pk"))
            .values("cuti_klaim_id")
            .annotate(total=Sum("jumlah_hari_diklaim"))
            .values("total")[:1]
        )

        qs = (
            RiwayatCuti.objects
            .filter(
                pegawai=user,
                jenis_cuti=self.CUTI_TAHUNAN,
                status_cuti__in=["Selesai", "Proses"],
            )
            .annotate(
                total_klaim=Coalesce(Subquery(klaim_total_sq, output_field=IntegerField()), Value(0)),
            )
            .annotate(
                pakai_dari_hak_tahun_ini=Case(
                    When(pakai_tunda_saja=True, then=Value(0)),
                    default=Greatest(Value(0), F("lama_cuti") - F("total_klaim")),
                    output_field=IntegerField(),
                )
            )
            .values("tahun_cuti")
            .annotate(total=Sum("pakai_dari_hak_tahun_ini"))
        )

        hasil = {}
        for row in qs:
            tahun = row["tahun_cuti"]
            if tahun is None:
                continue
            hasil[int(tahun)] = int(row["total"] or 0)

        return hasil

    # ------------------------------------------------------------------
    # 2) TAHUN YANG MASIH PUNYA CUTI TUNDA (belum habis diklaim)
    # ------------------------------------------------------------------
    def _tahun_dengan_penundaan(self, user) -> dict:
        """
        Tahun-tahun yang memiliki cuti TAHUNAN berstatus Tunda
        dengan sisa hari > 0, beserta total sisa tiap tahun.
        Contoh: {2024: 7, 2023: 3}
        """
        if not self.allow_cuti_tunda:
            return {}

        if not user or not getattr(user, 'is_authenticated', False):
            return {}

        qs = (
            RiwayatCuti.objects
            .filter(
                pegawai=user,
                jenis_cuti=self.CUTI_TAHUNAN,
                status_cuti='Tunda',
            )
            .annotate(total_terklaim=Sum('klaim_keluar__jumlah_hari_diklaim'))
        )

        hasil = {}
        for r in qs:
            tahun = r.tahun_cuti
            if tahun is None:
                continue
            terklaim = r.total_terklaim or 0
            sisa = max(0, (r.lama_cuti or 0) - terklaim)
            if sisa > 0:
                hasil[tahun] = hasil.get(tahun, 0) + sisa

        return hasil

    # ------------------------------------------------------------------
    # 3) Fungsi pendukung lama (boleh dibiarkan, hanya pakai hasil baru)
    # ------------------------------------------------------------------
    def _sisa_cuti_per_tahun(self, total_pakai: int) -> int:
        """Sisa cuti per tahun berjalan (tanpa kompensasi tahun sebelumnya)."""
        return max(0, self.HAK_CUTI_TAHUNAN - total_pakai)

    def _kompensasi_tahun_sebelumnya(self, penggunaan_tahunan: dict, tahun: int, tunda_map: dict | None = None) -> int:
        """
        - Jika tahun punya Tunda: kompensasi = min(sisa hak tahun itu, total sisa tunda tahun itu)
        - Jika tidak: kompensasi = min(6, sisa hak tahun itu)
        """
        tunda_map = tunda_map or {}

        terpakai = penggunaan_tahunan.get(tahun, 0)
        sisa_hak = self._sisa_cuti_per_tahun(terpakai)
        if sisa_hak <= 0:
            return 0

        if tahun in tunda_map:
            # hanya boleh bawa sebanyak sisa tunda (bukan full 12)
            return min(sisa_hak, tunda_map[tahun])

        # tahun tanpa tunda: maksimal 6 hari kompensasi
        return min(self.MAKSIMAL_KOMPENSASI_TAHUN, sisa_hak)
    # ------------------------------------------------------------------
    # 4) cek_sisa_cuti -> pakai perhitungan baru
    # ------------------------------------------------------------------
    def _sum_reserved_tunda_tahun_ini(self, user, tahun_sekarang: int) -> int:
        """
        Jumlah hari yang 'dikunci' karena ada cuti tahunan tahun berjalan
        yang sudah diputuskan: Disetujui (Ditunda).
        Ini bukan cuti yang diambil, tapi menahan saldo agar tidak dipakai lagi di tahun yang sama.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return 0

        agg = (
            RiwayatCuti.objects.filter(
                pegawai=user,
                jenis_cuti=self.CUTI_TAHUNAN,
                tahun_cuti=tahun_sekarang,
                status_cuti="Tunda",
                status_persetujuan="disetujui",
            )
            .aggregate(total=Coalesce(Sum("lama_cuti"), 0))
        )
        return int(agg["total"] or 0)


    def cek_sisa_cuti(self, user) -> int:
        if not user or not getattr(user, "is_authenticated", False):
            return 0

        tahun_sekarang = date.today().year

        # 1) cuti yang benar-benar diambil tahun ini (Proses/Selesai)
        cuti_diambil = self._sum_cuti_diambil_per_tahun(user)
        total_ambil_tahun_ini = int(cuti_diambil.get(tahun_sekarang, 0) or 0)

        # 2) hitung total hak (hak tahunan + kompensasi tahun lalu & dua tahun lalu)
        penggunaan_tahunan = self._sum_cuti_per_tahun(user)
        tahun_penundaan = self._tahun_dengan_penundaan(user)

        komp_tahun_lalu = self._kompensasi_tahun_sebelumnya(
            penggunaan_tahunan, tahun_sekarang - 1, tahun_penundaan
        )
        komp_dua_tahun_lalu = self._kompensasi_tahun_sebelumnya(
            penggunaan_tahunan, tahun_sekarang - 2, tahun_penundaan
        )

        total_hak = int(self.HAK_CUTI_TAHUNAN + komp_tahun_lalu + komp_dua_tahun_lalu)

        # 3) KUNCI saldo: cuti tahun ini yang disetujui untuk ditunda (reserved)
        reserved_tahun_ini = self._sum_reserved_tunda_tahun_ini(user, tahun_sekarang)

        # 4) sisa hak yang boleh dipakai tahun ini
        return max(0, total_hak - total_ambil_tahun_ini - reserved_tahun_ini)

    # ------------------------------------------------------------------
    # 5) (Opsional) Rapikan cek_sisa_tunda_cuti -> pakai sisa_hari_tunda
    # ------------------------------------------------------------------
    def cek_sisa_tunda_cuti(self, user) -> int:
        """
        Total sisa hak TUNDA (Cuti Tahunan) dua tahun sebelumnya yang belum diklaim
        melalui KlaimCutiTunda.
        """

        if not user or not getattr(user, 'is_authenticated', False):
            return 0

        today = date.today()
        tahun_cuti = [today.year - 1, today.year - 2]

        qs = (
            RiwayatCuti.objects
            .filter(
                pegawai=user,
                jenis_cuti=self.CUTI_TAHUNAN,
                status_cuti='Tunda',
                tahun_cuti__in=tahun_cuti,
            )
            .annotate(total_terklaim=Sum('klaim_keluar__jumlah_hari_diklaim'))
        )

        total_sisa = 0
        for r in qs:
            terpakai = r.total_terklaim or 0
            sisa = max(0, (r.lama_cuti or 0) - terpakai)
            total_sisa += sisa

        return int(total_sisa)
    
    def cek_pegawai_cuti_perinstalasi(self, instalasi):
        """Hitung jumlah pegawai yang sedang/sudah cuti di satu penempatan."""

        # Jika tidak ada penempatan yang diberikan, kembalikan data kosong.
        if instalasi is None:
            return {'jumlah': 0, 'pegawai': RiwayatCuti.objects.none()}

        tanggal: date = date.today()

        base_filter = (
            Q(status_cuti__in=['Selesai', 'Proses'])
            & Q(tgl_akhir_cuti__gte=tanggal)
            & Q(pegawai__riwayat_penempatan__status=True)
        )
        lokasi_filter = (
            Q(pegawai__riwayat_penempatan__penempatan_level4__instalasi=instalasi)
            | Q(pegawai__riwayat_penempatan__penempatan_level3__sub_bidang=instalasi)
            | Q(pegawai__riwayat_penempatan__penempatan_level2__bidang=instalasi)
            | Q(pegawai__riwayat_penempatan__penempatan_level1__unor=instalasi)
        )

        cuti_pegawai = (
            RiwayatCuti.objects
            .filter(base_filter & lokasi_filter)
            .select_related('pegawai', 'pegawai__profil_user')
            .distinct()
        )

        jumlah = cuti_pegawai.aggregate(jlh=Count('pegawai', distinct=True)).get('jlh') or 0

        return {
            'jumlah': jumlah,
            'pegawai': cuti_pegawai
        }
    
    def get_cuti_tunda_eligible(self, user, tahun_pengajuan: int):
        """
        Ambil queryset cuti TUNDA yang:
        - milik pegawai user
        - jenis = Cuti Tahunan
        - status_cuti = 'Tunda'
        - tahun_cuti = tahun_pengajuan - 1 atau tahun_pengajuan - 2
        - masih punya sisa hari tunda (belum habis diklaim)
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return RiwayatCuti.objects.none()

        tahun_eligible = [tahun_pengajuan - 1, tahun_pengajuan - 2]

        qs = (
            RiwayatCuti.objects
            .filter(
                pegawai=user,
                jenis_cuti=self.CUTI_TAHUNAN,
                status_cuti='Tunda',
                tahun_cuti__in=tahun_eligible,
            )
            .annotate(
                total_terklaim=Sum('klaim_keluar__jumlah_hari_diklaim')
            )
        )

        return qs.filter(
            Q(total_terklaim__lt=F('lama_cuti')) | Q(total_terklaim__isnull=True)
        )
    
    def cek_waktu_pengajuan_cuti_tunda(self, tahun_cuti) -> bool:
        tanggal_sekarang = date.today()
        pengajuan_cuti_tunda = False
        if tanggal_sekarang.year == tahun_cuti:
            pengajuan_cuti_tunda = True
            return pengajuan_cuti_tunda
        return pengajuan_cuti_tunda
    
    # def get_status_pegawai(self, pegawai):
    #     status = RiwayatPengangkatan.objects.filter(pegawai=pegawai).order_by('-id').first()
    #     return status
        
    def cek_waktu_pengajuan_cuti(self, tanggal_mulai_cuti, status_pegawai) -> bool:
        tanggal_sekarang = date.today()
        selisih_hari = (tanggal_mulai_cuti - tanggal_sekarang).days
        print('status_pegawai: ', status_pegawai)
        status = status_pegawai.strip()
        print('status: ', status == 'PNS')
        if selisih_hari < 0:
            return False  # tanggal cuti sudah lewat
        if status == "PNS":
            print('masuk PNS')
            return selisih_hari >= 7
        else:
            print('Tidak masuk kesini')
            return True
    
    def is_penerima_memiliki_pelimpahan_aktif(
        self,
        user,
        tgl_mulai: date,
        tgl_selesai: date
    ) -> bool:
        """
        Cek apakah user adalah penerima tugas untuk pelimpahan
        yang SUDAH disetujui dan rentang tanggalnya bentrok
        dengan pengajuan cuti (tgl_mulai - tgl_selesai).
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return False

        from .models import PelimpahanTugas  # sesuaikan path

        overlap_filter = (
            Q(tgl_mulai__lte=tgl_selesai) &
            Q(tgl_selesai__gte=tgl_mulai)
        )

        return PelimpahanTugas.objects.filter(
            penerima_tugas=user,
            persetujuan_penerima='disetujui',
            persetujuan_atasan='disetujui'
        ).filter(overlap_filter).exists()


class CutiApprovalService:
    """Service untuk menangani persetujuan cuti berjenjang berdasarkan ProfilAdmin"""
    
    def __init__(self):
        self.check_cuti = CheckCuti()
    
    def get_approval_chain(self, user):
        """Get rantai persetujuan untuk user berdasarkan penempatannya"""
        level = self.check_cuti._get_penempatan_level(user)
        
        if level == 4:  # Pegawai di Instalasi → butuh persetujuan SubBidang, Bidang, Unor
            return ['sub_bidang', 'bidang', 'unor']
        elif level == 3:  # Pegawai di SubBidang → butuh persetujuan Bidang, Unor
            return ['bidang', 'unor']
        elif level == 2:  # Pegawai di Bidang → butuh persetujuan Unor
            return ['unor']
        elif level == 1:  # Pegawai di Unor → tidak butuh persetujuan (atau bisa ke atasan lebih tinggi)
            return []
        else:
            return []
    
    def get_approvers_for_level(self, level, user_penempatan):
        """Get daftar user yang berwenang untuk approval level tertentu"""
        from myaccount.models import ProfilAdmin
        
        approvers = []
        
        if level == 'sub_bidang':
            # Cari user yang memiliki ProfilAdmin dengan sub_bidang yang sama dengan penempatan user
            if user_penempatan and user_penempatan.penempatan_level3:
                approvers = ProfilAdmin.objects.filter(
                    sub_bidang=user_penempatan.penempatan_level3
                ).values_list('user', flat=True)
            elif user_penempatan and user_penempatan.penempatan_level4:
                # Jika user di instalasi, cari sub_bidang dari instalasi tersebut
                approvers = ProfilAdmin.objects.filter(
                    sub_bidang=user_penempatan.penempatan_level4.sub_bidang
                ).values_list('user', flat=True)
                
        elif level == 'bidang':
            # Cari user yang memiliki ProfilAdmin dengan bidang yang sama
            if user_penempatan and user_penempatan.penempatan_level2:
                approvers = ProfilAdmin.objects.filter(
                    bidang=user_penempatan.penempatan_level2
                ).values_list('user', flat=True)
            elif user_penempatan and user_penempatan.penempatan_level3:
                # Jika user di sub_bidang, cari bidang dari sub_bidang tersebut
                approvers = ProfilAdmin.objects.filter(
                    bidang=user_penempatan.penempatan_level3.bidang
                ).values_list('user', flat=True)
            elif user_penempatan and user_penempatan.penempatan_level4:
                # Jika user di instalasi, cari bidang dari instalasi tersebut
                approvers = ProfilAdmin.objects.filter(
                    bidang=user_penempatan.penempatan_level4.sub_bidang.bidang
                ).values_list('user', flat=True)
                
        elif level == 'unor':
            # Cari user yang memiliki ProfilAdmin dengan unor yang sama
            if user_penempatan and user_penempatan.penempatan_level1:
                approvers = ProfilAdmin.objects.filter(
                    unor=user_penempatan.penempatan_level1
                ).values_list('user', flat=True)
            elif user_penempatan and user_penempatan.penempatan_level2:
                # Jika user di bidang, cari unor dari bidang tersebut
                approvers = ProfilAdmin.objects.filter(
                    unor=user_penempatan.penempatan_level2.unor
                ).values_list('user', flat=True)
            elif user_penempatan and user_penempatan.penempatan_level3:
                # Jika user di sub_bidang, cari unor dari sub_bidang tersebut
                approvers = ProfilAdmin.objects.filter(
                    unor=user_penempatan.penempatan_level3.bidang.unor
                ).values_list('user', flat=True)
            elif user_penempatan and user_penempatan.penempatan_level4:
                # Jika user di instalasi, cari unor dari instalasi tersebut
                approvers = ProfilAdmin.objects.filter(
                    unor=user_penempatan.penempatan_level4.sub_bidang.bidang.unor
                ).values_list('user', flat=True)
        
        return approvers
    
    def get_next_approval_level(self, layanan_cuti):
        """Get level persetujuan berikutnya menggunakan VerifikasiCuti"""
        # Get or create verification record
        if layanan_cuti.verifikasi.exists():
            verifikasi = layanan_cuti.verifikasi.first()
            current_level = verifikasi.current_level
        else:
            current_level = None
        
        approval_chain = self.get_approval_chain(layanan_cuti.pegawai)
        
        # Map approval chain to levels
        level_mapping = {
            'sub_bidang': 1,
            'bidang': 2, 
            'unor': 3
        }
        
        for level_name in approval_chain:
            level_num = level_mapping.get(level_name)
            if current_level is None or level_num > current_level:
                return level_name
        
        return None
    
    def can_approve(self, user, layanan_cuti):
        """Check apakah user bisa menyetujui cuti ini berdasarkan ProfilAdmin dan VerifikasiCuti"""
        next_level_name = self.get_next_approval_level(layanan_cuti)
        
        if not next_level_name:
            return False
        
        # Get user's ProfilAdmin
        profil_admin = getattr(user, 'profil_admin', None)
        if not profil_admin:
            return False
        
        # Get penempatan dari pegawai yang mengajukan cuti
        user_penempatan = (
            layanan_cuti.pegawai.riwayat_penempatan.filter(status=True)
            .order_by('-updated_at', '-id')
            .first()
        )
        
        if not user_penempatan:
            return False
        
        # Check if user has authority for this level based on ProfilAdmin
        if next_level_name == 'sub_bidang':
            # User harus memiliki ProfilAdmin dengan sub_bidang yang sesuai
            if profil_admin.sub_bidang:
                if user_penempatan.penempatan_level3:
                    return profil_admin.sub_bidang == user_penempatan.penempatan_level3
                elif user_penempatan.penempatan_level4:
                    return profil_admin.sub_bidang == user_penempatan.penempatan_level4.sub_bidang
            return False
            
        elif next_level_name == 'bidang':
            # User harus memiliki ProfilAdmin dengan bidang yang sesuai
            if profil_admin.bidang:
                if user_penempatan.penempatan_level2:
                    return profil_admin.bidang == user_penempatan.penempatan_level2
                elif user_penempatan.penempatan_level3:
                    return profil_admin.bidang == user_penempatan.penempatan_level3.bidang
                elif user_penempatan.penempatan_level4:
                    return profil_admin.bidang == user_penempatan.penempatan_level4.sub_bidang.bidang
            return False
            
        elif next_level_name == 'unor':
            # User harus memiliki ProfilAdmin dengan unor yang sesuai
            if profil_admin.unor:
                if user_penempatan.penempatan_level1:
                    return profil_admin.unor == user_penempatan.penempatan_level1
                elif user_penempatan.penempatan_level2:
                    return profil_admin.unor == user_penempatan.penempatan_level2.unor
                elif user_penempatan.penempatan_level3:
                    return profil_admin.unor == user_penempatan.penempatan_level3.bidang.unor
                elif user_penempatan.penempatan_level4:
                    return profil_admin.unor == user_penempatan.penempatan_level4.sub_bidang.bidang.unor
            return False
        
        return False
    
    def approve_cuti(self, layanan_cuti, approver, status, catatan='', file_verifikasi=None):
        """Proses persetujuan cuti menggunakan VerifikasiCuti"""
        next_level_name = self.get_next_approval_level(layanan_cuti)
        
        if not next_level_name:
            raise ValueError("Tidak ada level persetujuan berikutnya")
        
        if not self.can_approve(approver, layanan_cuti):
            raise ValueError("User tidak memiliki wewenang untuk menyetujui cuti ini")
        
        # Get or create verification record
        if layanan_cuti.verifikasi.exists():
            verifikasi = layanan_cuti.verifikasi.first()
        else:
            verifikasi = VerifikasiCuti(layanan_cuti=layanan_cuti)
        
        # Map level name to level number
        level_mapping = {
            'sub_bidang': 1,
            'bidang': 2,
            'unor': 3
        }
        level_num = level_mapping.get(next_level_name)
        
        # Set approval for specific level
        verifikasi.set_approval_for_level(
            level=level_num,
            approver=approver,
            status=status,  # True for approve, False for reject
            catatan=catatan,
            file_verifikasi=file_verifikasi
        )
        
        # Update layanan cuti status
        if not status:  # Rejected
            layanan_cuti.status = 'Ditolak'
        elif status:  # Approved
            # Check if this is final approval
            next_level_after = self.get_next_approval_level(layanan_cuti)
            if not next_level_after:
                layanan_cuti.status = 'Disetujui Unor'
            else:
                layanan_cuti.status = f'Disetujui {next_level_name.title()}'
        
        layanan_cuti.save()
        
        return verifikasi