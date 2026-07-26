from django.urls import path
from .pdf_views import DownloadPresensiBulananPDFView
from .views import (    
    JadwalListView,
    DeleteJadwalView,
    JadwalUpdateView,
    JadwalDinasFormsetUpdateView,
    LogKehadiranView,
    SalinJadwalView,
    SalinJadwalInstalasiView,
    JadwalDinasDetailView,
    AjukanJadwalView,
    SetujuiJadwalView,
    JadwalBulananListView,
    ApprovedJadwalBulananListView,
    draft_export_jadwal_excel,
    export_jadwal_excel,
    EvaluasiJadwal,
    ApprovalJadwalInstalasi,
    PengajuanJadwalInstalasi,
    VerifikasiJadwalView,
    RekapPiketListView,
    
    KehadiranSpesialisListView,
    KehadiranCreateView,
    KehadiranUpdateView,
    KehadiranUtamaView,
    DetailKehadiranView,
    SinkronisasiLogView,
    SinkronisasiResultView,
    process_single_sync,
    sync_dashboard,
    sync_individual_api,
    # PenilaianKehadiranView,
    
    HariLiburView,
    HariLiburCreateView,
    HariLiburUpdateView,
    HariLiburDeleteView,
    
    RekapPresensiBulananView,
    UpdatePresensiPegawaiView,
    DetailPresensiPegawaiView,
    DownloadRekapPresensiExcelView,
    RawPresensiDatabaseListView,
)

urlpatterns = [
    path('', JadwalListView.as_view(), name='jadwal_list'),
    path('updatejadwal/<int:pk>/', JadwalUpdateView.as_view(), name='jadwal_update_view'),
    path('deletejadwal/<int:id>/', DeleteJadwalView.as_view(), name='jadwal_delete_view'),
    
    path('jadwal-auto-create/<int:pk>/', JadwalDinasFormsetUpdateView.as_view(), name='jadwal_auto_create'), #otomatis buat dan edit detail jadwal
    path('salin-jadwal/', SalinJadwalView.as_view(), name='salin_jadwal'), #salin jadwal persatu sdm
    path('salin-jadwal-instalasi/', SalinJadwalInstalasiView.as_view(), name='salin_jadwal_instalasi'), #salin jadwal utk satu instalasi
    path('jadwal/<int:pk>/detail/', JadwalDinasDetailView.as_view(), name='jadwal_detail'), #view detail jadwal untuk user
    path('jadwal/<int:pk>/ajukan/', AjukanJadwalView.as_view(), name='ajukan_jadwal'), 
    path('jadwal/<int:pk>/persetujuan/', SetujuiJadwalView.as_view(), name='setujui_jadwal'),
    path('jadwal/pivot/<int:inst>/', JadwalBulananListView.as_view(), name='jadwal_pivot'), #tabel jadwal 1 bulan
    path('jadwal/pivot/<int:inst>/approved/', ApprovedJadwalBulananListView.as_view(), name='jadwal_pivot_approved'), #tabel jadwal 1 bulan
    path('export-excel/<int:inst>/<int:bulan>/<int:tahun>/', export_jadwal_excel, name='export_jadwal_excel'),
    path('draft-export-excel/<int:inst>/<int:bulan>/<int:tahun>/', draft_export_jadwal_excel, name='draft_export_jadwal_excel'),
    path('evaluasi-jadwal/', EvaluasiJadwal.as_view(), name='evaluasi_jadwal'),
    path('pengajuan/<int:inst>/<int:bulan>/<int:tahun>/', PengajuanJadwalInstalasi.as_view(), name='pengajuan_jadwal_instalasi'),
    path('approval/<int:inst>/<int:bulan>/<int:tahun>/', ApprovalJadwalInstalasi.as_view(), name='approval_jadwal'),
    path('verifikasi-jadwal/<int:pk>/', VerifikasiJadwalView.as_view(), name='verifikasi_jadwal'),# verifikasi perubahan jadwal yang diajukan
    path('rekap-piket/', RekapPiketListView.as_view(), name='rekap_piket'),
    
    path('kehadiran/', KehadiranUtamaView.as_view(), name='kehadiran_list'),
    path('kehadiran-spesialis/', KehadiranSpesialisListView.as_view(), name='kehadiran_spesialis_list'),
    path('kehadiran/add/', KehadiranCreateView.as_view(), name='kehadiran_create'),
    path('kehadiran/<int:pk>/update/', KehadiranUpdateView.as_view(), name='kehadiran_update'),
    path('kehadiran/user/<int:pk>/', DetailKehadiranView.as_view(), name='kehadiran_detail_user'),
    path('kehadiran/upload-fingerprint/', KehadiranUtamaView.as_view(), name='kehadiran_upload_fingerprint'),
    path(
        'sinkronisasi/', 
        SinkronisasiLogView.as_view(), 
        name='sinkronisasi'
    ),
    path(
        'sinkronisasi/hasil/', 
        SinkronisasiResultView.as_view(), 
        name='sinkronisasi-result'
    ),
    path('log-kehadiran/', LogKehadiranView.as_view(), name='log-kehadiran'),
    # path('penilaian-kehadiran/', PenilaianKehadiranView.as_view(), name='penilaian-kehadiran'),
    path('sinkronisasi/dashboard/', sync_dashboard, name='sync_dashboard'),
    path('sinkronisasi/api/', sync_individual_api, name='sync_individual_api'),
    path('sync/process-single/', process_single_sync, name='process_single_sync'), 
    path('harilibur/', HariLiburView.as_view(), name='harilibur_list'),
    path('harilibur/add/', HariLiburCreateView.as_view(), name='harilibur_create'),
    path('harilibur/<int:pk>/update/', HariLiburUpdateView.as_view(), name='harilibur_update'),
    path('harilibur/<int:pk>/delete/', HariLiburDeleteView.as_view(), name='harilibur_delete'),
    
    # URL UNTUK MODEL BARU
    path('rekap-kehadiran/', RekapPresensiBulananView.as_view(), name='rekap_kehadiran_bulanan'),
    path('presensi/data-mentah/', RawPresensiDatabaseListView.as_view(), name='raw_presensi_database'),
    path('rekap-kehadiran/<int:pk>/detail/', DetailPresensiPegawaiView.as_view(), name='detail_presensi_pegawai'),
    path('rekap-khadiran/<int:pk>/update/', UpdatePresensiPegawaiView.as_view(), name='update_kehadiran_pegawai'),
    path('rekap/download-excel/', DownloadRekapPresensiExcelView.as_view(), name='download_excel'),
    path('rekap/download-pdf/', DownloadPresensiBulananPDFView.as_view(), name='download_presensi_pdf'),
]
