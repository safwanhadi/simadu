from django.urls import path
from .views import (
    StandarSDMInstalasi, 
    DetailNakes, 
    KehadiranGrafikView, 
    ProsentaseKedisiplinanInstalasi,
    StandarInstalasiView,
    DashboardAbsensiView,
    DashboardAbsensiTemplateView,
    ExportAbsensiHarianExcelView,
    ExportWorkforceProfessionExcelView,
    tandai_hadist_modal_sudah_tampil,
)


urlpatterns = [
    path('', StandarInstalasiView.as_view(), name='dashboard_view'),
    path('sdm/<int:sdm>/', DetailNakes.as_view(), name='dashboard_sdm_view'),
    path('sdm/export-profesi/', ExportWorkforceProfessionExcelView.as_view(), name='export_workforce_profession'),
    path('grafik-kehadiran/', KehadiranGrafikView.as_view(), name='grafik_kehadiran_view'),
    path('grafik-kedisiplinan-instalasi/', ProsentaseKedisiplinanInstalasi.as_view(), name='grafik_kedisiplinan_instalasi_view'),
    path('dashboard-absensi/', DashboardAbsensiTemplateView.as_view(), name='dashboard_absensi_view'),
    path('export-harian/', ExportAbsensiHarianExcelView.as_view(), name='export_harian_excel'),
    path(
        'hadist/modal/sudah-tampil/',
        tandai_hadist_modal_sudah_tampil,
        name='tandai_hadist_modal_sudah_tampil',
    ),
]
