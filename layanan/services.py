from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, F, Value, IntegerField, Case, When, Count, Q, OuterRef, Subquery
from django.db.models.functions import Coalesce, Greatest
from django.conf import settings
from .models import RiwayatCuti
from dokumen.models import KlaimCutiTunda
from typing import Optional

class CheckCuti:
    CUTI_TAHUNAN = 'Cuti Tahunan'
    STATUS_KURANGI_CUTI = ['Belum', 'Berlangsung', 'Selesai', 'Tunda']
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
                status_cuti__in=['Belum', 'Berlangsung', 'Selesai'],
            )
            .filter(Q(usulan__status__in=('disetujui', 'selesai')) | Q(usulan__isnull=True))
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
                status_cuti__in=["Belum", "Berlangsung", "Selesai"],
            )
            .filter(Q(usulan__status__in=('disetujui', 'selesai')) | Q(usulan__isnull=True))
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
    def _ringkasan_cuti_tunda(self, user) -> dict:
        """
        Ringkasan sumber cuti tunda per tahun, termasuk sumber yang sudah habis.

        Tahun yang sudah pernah memiliki sumber tunda harus tetap dicatat dengan
        sisa 0. Jika dihilangkan, perhitungan kompensasi akan menganggap tahun
        tersebut belum memiliki sumber tunda dan memberi hak otomatis lagi.
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
            .filter(Q(usulan__status__in=('disetujui', 'selesai')) | Q(usulan__isnull=True))
            .annotate(
                total_terklaim=Sum(
                    'klaim_keluar__jumlah_hari_diklaim',
                    filter=(
                        Q(klaim_keluar__cuti_klaim__status_cuti__in=(
                            'Belum', 'Berlangsung', 'Selesai',
                        ))
                        & (
                            Q(klaim_keluar__cuti_klaim__usulan__status__in=(
                                'pengajuan', 'tindaklanjut',
                                'disetujui', 'selesai',
                            ))
                            | Q(
                                klaim_keluar__cuti_klaim__usulan__isnull=True
                            )
                        )
                    ),
                )
            )
        )

        hasil = {}
        for r in qs:
            tahun = r.tahun_cuti
            if tahun is None:
                continue
            hak_tunda = int(r.lama_cuti or 0)
            terklaim = int(r.total_terklaim or 0)
            ringkasan = hasil.setdefault(
                int(tahun),
                {'hak_tunda': 0, 'terklaim': 0, 'sisa': 0},
            )
            ringkasan['hak_tunda'] += hak_tunda
            ringkasan['terklaim'] += terklaim
            ringkasan['sisa'] += max(0, hak_tunda - terklaim)

        return hasil

    def _tahun_dengan_penundaan(self, user) -> dict:
        return {
            tahun: data['sisa']
            for tahun, data in self._ringkasan_cuti_tunda(user).items()
        }

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
            )
            .filter(Q(usulan__status__in=('disetujui', 'selesai')) | Q(usulan__isnull=True))
            .aggregate(total=Coalesce(Sum("lama_cuti"), 0))
        )
        return int(agg["total"] or 0)

    def _sum_pending_cuti_tahun_ini(
        self,
        user,
        tahun_sekarang: int,
        pada: date | None = None,
    ) -> int:
        """
        Cadangkan bagian pengajuan aktif yang dibebankan ke saldo umum.

        Hari dari ``KlaimCutiTunda`` tidak dikurangkan lagi karena saldo
        sumber tundanya sudah berkurang ketika klaim dibuat.
        """
        klaim_total_sq = (
            KlaimCutiTunda.objects
            .filter(cuti_klaim_id=OuterRef('pk'))
            .values('cuti_klaim_id')
            .annotate(total=Sum('jumlah_hari_diklaim'))
            .values('total')[:1]
        )
        pada = pada or date.today()
        agg = (
            RiwayatCuti.objects
            .filter(
                pegawai=user,
                jenis_cuti=self.CUTI_TAHUNAN,
                tahun_cuti=tahun_sekarang,
                status_cuti='Belum',
                usulan__status__in=('pengajuan', 'tindaklanjut'),
            )
            .filter(
                Q(tgl_akhir_cuti__isnull=True)
                | Q(tgl_akhir_cuti__gte=pada)
            )
            .annotate(
                total_klaim=Coalesce(
                    Subquery(klaim_total_sq, output_field=IntegerField()),
                    Value(0),
                ),
            )
            .annotate(
                beban_saldo=Case(
                    When(pakai_tunda_saja=True, then=Value(0)),
                    default=Greatest(
                        Value(0),
                        F('lama_cuti') - F('total_klaim'),
                    ),
                    output_field=IntegerField(),
                ),
            )
            .aggregate(total=Coalesce(Sum('beban_saldo'), 0))
        )
        return int(agg['total'] or 0)


    def _hitung_sisa_cuti(self, user, tahun_ref: int) -> int:
        if not user or not getattr(user, "is_authenticated", False):
            return 0

        # Yang mengurangi saldo umum hanya beban setelah klaim tunda.
        penggunaan_tahunan = self._sum_cuti_per_tahun(user)
        tahun_penundaan = self._tahun_dengan_penundaan(user)
        total_ambil_tahun_ini = int(penggunaan_tahunan.get(tahun_ref, 0) or 0)

        komp_tahun_lalu = self._kompensasi_tahun_sebelumnya(
            penggunaan_tahunan, tahun_ref - 1, tahun_penundaan
        )
        komp_dua_tahun_lalu = self._kompensasi_tahun_sebelumnya(
            penggunaan_tahunan, tahun_ref - 2, tahun_penundaan
        )

        total_hak = int(self.HAK_CUTI_TAHUNAN + komp_tahun_lalu + komp_dua_tahun_lalu)
        reserved_tahun_ini = self._sum_reserved_tunda_tahun_ini(user, tahun_ref)
        pending_tahun_ini = self._sum_pending_cuti_tahun_ini(
            user,
            tahun_ref,
            pada=date.today(),
        )
        return max(0, total_hak - total_ambil_tahun_ini - reserved_tahun_ini - pending_tahun_ini)

    def cek_sisa_cuti(self, user) -> int:
        return self._hitung_sisa_cuti(user, date.today().year)

    def buat_snapshot_saldo_cuti(
        self,
        user,
        tahun_ref: int | None = None,
        pada: date | None = None,
    ) -> dict:
        """Bangun saldo yang dapat dibekukan pada saat pengajuan dibuat."""
        tahun_ref = int(tahun_ref or date.today().year)
        pada = pada or date.today()
        penggunaan = self._sum_cuti_per_tahun(user)
        ringkasan_tunda = self._ringkasan_cuti_tunda(user)
        tahun_penundaan = {
            tahun: data['sisa']
            for tahun, data in ringkasan_tunda.items()
        }
        kapasitas = {
            tahun_ref - 2: self._kompensasi_tahun_sebelumnya(
                penggunaan, tahun_ref - 2, tahun_penundaan
            ),
            tahun_ref - 1: self._kompensasi_tahun_sebelumnya(
                penggunaan, tahun_ref - 1, tahun_penundaan
            ),
            tahun_ref: self.HAK_CUTI_TAHUNAN,
        }

        # Beban tahun berjalan memakai hak N terlebih dahulu, kemudian N-1
        # dan N-2. Pisahkan pemakaian final dari pencadangan pengajuan aktif
        # agar pengurang saldo dapat diaudit pada formulir.
        terpakai_tahun_berjalan = int(penggunaan.get(tahun_ref, 0) or 0)
        beban_dicadangkan = (
            self._sum_reserved_tunda_tahun_ini(user, tahun_ref)
            + self._sum_pending_cuti_tahun_ini(user, tahun_ref, pada=pada)
        )
        saldo_per_tahun = dict(kapasitas)
        sisa_beban = terpakai_tahun_berjalan
        for tahun in (tahun_ref, tahun_ref - 1, tahun_ref - 2):
            dipakai = min(saldo_per_tahun[tahun], sisa_beban)
            saldo_per_tahun[tahun] -= dipakai
            sisa_beban -= dipakai

        dicadangkan_per_tahun = {
            tahun_ref - 2: 0,
            tahun_ref - 1: 0,
            tahun_ref: 0,
        }
        sisa_cadangan = beban_dicadangkan
        for tahun in (tahun_ref, tahun_ref - 1, tahun_ref - 2):
            dicadangkan = min(saldo_per_tahun[tahun], sisa_cadangan)
            saldo_per_tahun[tahun] -= dicadangkan
            dicadangkan_per_tahun[tahun] = dicadangkan
            sisa_cadangan -= dicadangkan

        rows = []

        for label, tahun in (
            ('N-2', tahun_ref - 2),
            ('N-1', tahun_ref - 1),
            ('N', tahun_ref),
        ):
            terpakai_hak = int(penggunaan.get(tahun, 0) or 0)
            data_tunda = ringkasan_tunda.get(
                tahun,
                {'hak_tunda': 0, 'terklaim': 0, 'sisa': 0},
            )
            terpakai_tunda = int(data_tunda['terklaim'])
            terpakai_total = (
                terpakai_hak
                + terpakai_tunda
                + int(dicadangkan_per_tahun[tahun])
            )
            sisa_hak = self._sisa_cuti_per_tahun(terpakai_total)
            rows.append({
                'label': label,
                'tahun': tahun,
                'hak_awal': self.HAK_CUTI_TAHUNAN,
                'terpakai': terpakai_total,
                'terpakai_hak': terpakai_hak,
                'terpakai_tunda': terpakai_tunda,
                'dicadangkan': int(dicadangkan_per_tahun[tahun]),
                'sisa_hak': int(sisa_hak),
                'dapat_digunakan': int(saldo_per_tahun[tahun]),
                'hak_tunda': int(data_tunda['hak_tunda']),
                'sisa_tunda': int(data_tunda['sisa']),
            })

        return {
            'versi': 3,
            'dibuat_pada': pada.isoformat(),
            'tahun_referensi': tahun_ref,
            'total_tersedia': int(sum(saldo_per_tahun.values())),
            'rows': rows,
        }

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
            .filter(Q(usulan__status__in=('disetujui', 'selesai')) | Q(usulan__isnull=True))
        )

        return int(sum(r.sisa_hari_tunda for r in qs))
    
    def cek_pegawai_cuti_perinstalasi(self, instalasi):
        """Hitung jumlah pegawai yang sedang/sudah cuti di satu penempatan."""

        # Jika tidak ada penempatan yang diberikan, kembalikan data kosong.
        if instalasi is None:
            return {'jumlah': 0, 'pegawai': RiwayatCuti.objects.none()}

        tanggal: date = date.today()

        base_filter = (
            Q(status_cuti__in=['Belum', 'Berlangsung', 'Selesai'])
            & (Q(usulan__status__in=('disetujui', 'selesai')) | Q(usulan__isnull=True))
            & Q(tgl_mulai_cuti__lte=tanggal)
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
            .filter(Q(usulan__status__in=('disetujui', 'selesai')) | Q(usulan__isnull=True))
            .annotate(
                total_terklaim=Sum(
                    'klaim_keluar__jumlah_hari_diklaim',
                    filter=(
                        Q(klaim_keluar__cuti_klaim__status_cuti__in=(
                            'Belum', 'Berlangsung', 'Selesai',
                        ))
                        & (
                            Q(klaim_keluar__cuti_klaim__usulan__status__in=(
                                'pengajuan', 'tindaklanjut',
                                'disetujui', 'selesai',
                            ))
                            | Q(
                                klaim_keluar__cuti_klaim__usulan__isnull=True
                            )
                        )
                    ),
                )
            )
        )

        return qs.filter(
            Q(total_terklaim__lt=F('lama_cuti')) | Q(total_terklaim__isnull=True)
        )
    
    def cek_waktu_pengajuan_cuti(self, tanggal_mulai_cuti, status_pegawai) -> bool:
        tanggal_sekarang = date.today()
        selisih_hari = (tanggal_mulai_cuti - tanggal_sekarang).days
        status = (status_pegawai or '').strip()
        if selisih_hari < 0:
            return False  # tanggal cuti sudah lewat
        if status == "PNS":
            return selisih_hari >= 7
        else:
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

    def is_memiliki_cuti_bentrok(
        self,
        user,
        tgl_mulai: date,
        tgl_selesai: date,
        exclude_riwayat_id=None,
    ) -> bool:
        """Cegah pengajuan cuti aktif milik pegawai yang saling bertabrakan."""
        if (
            not user
            or not tgl_mulai
            or not tgl_selesai
            or tgl_mulai > tgl_selesai
        ):
            return False

        queryset = (
            RiwayatCuti.objects
            .filter(
                pegawai=user,
                tgl_mulai_cuti__lte=tgl_selesai,
                tgl_akhir_cuti__gte=tgl_mulai,
            )
            .exclude(status_cuti__in=('Tunda', 'Batal'))
            .filter(
                Q(
                    usulan__status__in=(
                        'pengajuan',
                        'tindaklanjut',
                        'disetujui',
                        'selesai',
                    )
                )
                | Q(usulan__isnull=True)
            )
        )
        if exclude_riwayat_id:
            queryset = queryset.exclude(pk=exclude_riwayat_id)
        return queryset.exists()
