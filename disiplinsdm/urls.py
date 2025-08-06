from django.urls import path
from .views import (    
    JadwalListView,
    DeleteJadwalView,
    JadwalUpdateView,
    JadwalDinasFormsetUpdateView,
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
    
    KehadiranListView,
    KehadiranSpesialisListView,
    KehadiranCreateView,
    KehadiranUpdateView,
    DetailKehadiranView,
    FingerprintAutoUploadView,
    
    HariLiburView,
    HariLiburCreateView,
    HariLiburUpdateView,
    HariLiburDeleteView,
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
    
    path('kehadiran/', KehadiranListView.as_view(), name='kehadiran_list'),
    path('kehadiran-spesialis/', KehadiranSpesialisListView.as_view(), name='kehadiran_spesialis_list'),
    path('kehadiran/add/', KehadiranCreateView.as_view(), name='kehadiran_create'),
    path('kehadiran/<int:pk>/update/', KehadiranUpdateView.as_view(), name='kehadiran_update'),
    path('kehadiran/user/<int:pk>/', DetailKehadiranView.as_view(), name='kehadiran_detail_user'),
    path('kehadiran/upload-fingerprint/', FingerprintAutoUploadView.as_view(), name='kehadiran_upload_fingerprint'),
    
    path('harilibur/', HariLiburView.as_view(), name='harilibur_list'),
    path('harilibur/add/', HariLiburCreateView.as_view(), name='harilibur_create'),
    path('harilibur/<int:pk>/update/', HariLiburUpdateView.as_view(), name='harilibur_update'),
    path('harilibur/<int:pk>/delete/', HariLiburDeleteView.as_view(), name='harilibur_delete'),
]