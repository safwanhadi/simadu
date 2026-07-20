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
)


urlpatterns = [
    path('', StandarInstalasiView.as_view(), name='dashboard_view'),
    path('sdm/<int:sdm>/', DetailNakes.as_view(), name='dashboard_sdm_view'),
    path('sdm/export-profesi/', ExportWorkforceProfessionExcelView.as_view(), name='export_workforce_profession'),
    path('grafik-kehadiran/', KehadiranGrafikView.as_view(), name='grafik_kehadiran_view'),
    path('grafik-kedisiplinan-instalasi/', ProsentaseKedisiplinanInstalasi.as_view(), name='grafik_kedisiplinan_instalasi_view'),
    path('dashboard-absensi/', DashboardAbsensiTemplateView.as_view(), name='dashboard_absensi_view'),
    path('export-harian/', ExportAbsensiHarianExcelView.as_view(), name='export_harian_excel'),
]
