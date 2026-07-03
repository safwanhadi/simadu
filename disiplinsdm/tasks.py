from django.utils import timezone
from datetime import datetime, timedelta
from disiplinsdm.models import JenisSDMPerinstalasi, KehadiranKegiatan, ApprovedJadwalDinasSDM, AlasanTidakHadir, LogKehadiran
# Import ketiga service Anda
from disiplinsdm.services import BridgeSyncService, AttendanceMappingService, AttendanceReconciliationService

def hitung_kehadiran_harian_task():
    """
    Fungsi Utama Django Q2 (Dijalankan Otomatis Setiap Pukul 01:00 Dini Hari).
    Menggabungkan proses Pull Data, Mapping, Rekonsiliasi, dan Deteksi TK.
    """
    # 1. Tentukan tanggal hari kemarin (target evaluasi)
    hari_ini = datetime.now().date()
    kemarin = hari_ini - timedelta(days=1)
    kemarin_str = kemarin.strftime('%Y-%m-%d')
    
    print(f"--- MEMULAI AUTOMATION PIPELINE UNTUK TANGGAL: {kemarin_str} ---")

    # =========================================================================
    # TAHAP 1: PULL DATA DARI MESIN ABSENSI (BridgeSyncService)
    # =========================================================================
    try:
        # Menarik data attlog dari Flask Bridge khusus untuk tanggal kemarin
        synced, ignored = BridgeSyncService.run_daily_sync(date_from=kemarin_str, limit=500)
        print(f"[TAHAP 1] Bridge Sync Selesai: {synced} data baru masuk ke MariaDB, {ignored} diabaikan.")
    except Exception as e:
        # Jika API/Network down, kita catat log tapi proses selanjutnya tetap dicoba
        print(f"[TAHAP 1] Gagal melakukan sinkronisasi API: {e}")

    # =========================================================================
    # TAHAP 2: MAPPING LOG MENTAH KE KEHADIRAN (AttendanceMappingService)
    # =========================================================================
    # Ambil scope pegawai aktif pada bulan berjalan
    scope_pegawai = JenisSDMPerinstalasi.objects.filter(bulan=kemarin.month, tahun=kemarin.year)
    if not scope_pegawai.exists():
        return f"Proses dihentikan. Tidak ada master data pegawai aktif di JenisSDMPerinstalasi pada periode {kemarin.month}/{kemarin.year}."

    print(f"[TAHAP 2] Scope Pegawai: {scope_pegawai.count()} pegawai aktif untuk bulan {kemarin.month}/{kemarin.year}.")
    
    # Ambil data raw logs yang baru saja ditarik (atau sudah ada) khusus untuk tanggal kemarin
    raw_logs_kemarin = LogKehadiran.objects.filter(
        datetime__date=kemarin,
        mapping__pegawai__in=scope_pegawai.values_list('pegawai', flat=True)
    )
    print(f"[TAHAP 2] Mulai Mapping: {raw_logs_kemarin.count()} log kehadiran mentah untuk tanggal {kemarin_str} akan diproses.")
    
    success_mapping = 0
    for log in raw_logs_kemarin:
        # Panggil fungsi mapping baris demi baris yang telah Anda buat sebelumnya
        kehadiran, msg = AttendanceMappingService.map_single_log(log)
        if kehadiran:
            success_mapping += 1
    print(f"[TAHAP 2] Mapping Log Selesai: {success_mapping} aktivitas berhasil dipetakan.")

    # =========================================================================
    # TAHAP 3: REKONSILIASI KETEPATAN WAKTU VS JADWAL (AttendanceReconciliationService)
    # =========================================================================
    total_reconciled = 0
    for peg_instalasi in scope_pegawai:
        count = AttendanceReconciliationService.reconcile_employee_monthly(
            pegawai_instalasi=peg_instalasi,
            bulan=kemarin.month,
            tahun=kemarin.year
        )
        total_reconciled += count
    print(f"[TAHAP 3] Rekonsiliasi Selesai: {total_reconciled} status kehadiran dievaluasi.")

    # =========================================================================
    # TAHAP 4: DETEKSI OTOMATIS PEGAWAI TANPA KETERANGAN (TK / MANGKIR)
    # =========================================================================
    alasan_tk, _ = AlasanTidakHadir.objects.get_or_create(alasan='Tanpa Keterangan')
    total_tk = 0

    # Ambil jadwal dinas kemarin yang sudah di-approve dan BUKAN jadwal libur
    jadwal_dinas_kemarin = ApprovedJadwalDinasSDM.objects.filter(
        tanggal=kemarin,
        is_approved=True
    ).exclude(kategori_jadwal__kategori_dinas__kategori_dinas='Libur')

    for jadwal in jadwal_dinas_kemarin:
        peg_instalasi = jadwal.pegawai
        
        # Cek apakah dia punya record kehadiran (minimal absen-datang) kemarin
        punya_absen_datang = KehadiranKegiatan.objects.filter(
            pegawai__pegawai=peg_instalasi.pegawai,
            tanggal__date=kemarin,
            pegawai__kegiatan__slug='absen-datang'
        ).exists()

        # Jika ada jadwal masuk tapi tidak ada log datang sama sekali -> Set TK
        if not punya_absen_datang:
            daftar_kegiatan = peg_instalasi.daftarkegiatanpegawai_set.filter(
                bulan=kemarin.month,
                tahun=kemarin.year,
                kegiatan__slug='absen-datang'
            ).first()

            if daftar_kegiatan:
                jam_jadwal = jadwal.kategori_jadwal.waktu_datang
                datetime_tk = timezone.make_aware(datetime.combine(kemarin, jam_jadwal))

                KehadiranKegiatan.objects.update_or_create(
                    pegawai=daftar_kegiatan,
                    tanggal=datetime_tk,
                    defaults={
                        'hadir': False,
                        'alasan': alasan_tk,
                        'status_ketepatan': 'Terlambat Berat',
                        'ket': f"Sistem (Q2 Pipeline): Tidak melakukan tapping pada jadwal {jadwal.kategori_jadwal.kategori_jadwal}"
                    }
                )
                total_tk += 1
    print(f"[TAHAP 4] Deteksi Mangkir Selesai: {total_tk} pegawai otomatis diset Tanpa Keterangan.")

    return f"Pipeline Sukses untuk Tanggal {kemarin_str}. Detail -> Map: {success_mapping}, Reconcile: {total_reconciled}, TK: {total_tk}."