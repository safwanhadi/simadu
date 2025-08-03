from django.urls import path

from .views import (
    JenisLayananView,
    LayanananCutiInlineCreateView,
    LayananCutiInlineFormView,
    LayananCutiUpdateView,
    LayananCutiTundaView,
    LayananCreateCutiFromCutiTunda,#using createview
    LayananUpdateCUtiTundaView,#using updateview
    
    LayananGajiBerkalaView,
    LayananGajiBerkalaUpdateView,
    LayananGajiBerkalaAPIView,
    LayananGajiBerkalaAdminView,
    LayananGajiBerkalaAdminAddView,
    LayananGajiBerkalaUpload,
    
    LayananUsulanDiklatView,
    LayananUsulanDiklatStaffView,
    LayananUsulanDiklatListView,
    LayananUsulanDiklatCreateView,
    LayananUsulanDiklatUpdateView,
    PenugasanDiklatCreateView,
    PengalihanDiklatCreateView,
    VerifikasiDiklatView,
    CatatanSDMUsulanLayananDiklatUpdateView,
    
    LayananUsulanInovasiView,
    LayananUsulanInovasiUpdateView,
    NotifikasiView
)


urlpatterns=[
    path('', JenisLayananView.as_view(), name='layanan_view'),
    path('yancuti/<str:status>/', LayananCutiInlineFormView.as_view(), name='layanan_cuti_view'),
    path('yancuti/<str:status>/<int:id>/', LayananCutiUpdateView.as_view(), name='layanan_cuti_update_view'),
    path('pengajuan-cuti/', LayanananCutiInlineCreateView.as_view(), name='pengajuan_cuti_view'),
    path('list-cuti-tunda/', LayananCutiTundaView.as_view(), name='layanan_cuti_tunda_view'),
    path('cuti-tunda/<int:pk>/', LayananCreateCutiFromCutiTunda.as_view(), name='layanan_ambil_cuti_tunda_view'),
    path('update-cuti-tunda/<int:pk>/', LayananUpdateCUtiTundaView.as_view(), name='layanan_update_cuti_tunda_view'),
    path('yanberkala/', LayananGajiBerkalaView.as_view(), name='layanan_berkala_view'),
    path('yanberkala/<int:id>/', LayananGajiBerkalaUpdateView.as_view(), name='layanan_berkala_update_view'),
    path('api/berkala/<int:id>/', LayananGajiBerkalaAPIView.as_view(), name='layanan_berkala_api_view'),
    path('yanberkala/proses/<int:layanan_id>/<str:nip>/', LayananGajiBerkalaAdminView.as_view(), name='layanan_berkala_admin_view'),
    path('yanberkala/proses/add/<int:layanan_id>/<str:nip>/', LayananGajiBerkalaAdminAddView.as_view(), name='layanan_berkala_admin_add_view'),
    path('yanberkala/proses/upload/<int:berkala_id>/<int:layanan_id>/<str:nip>/', LayananGajiBerkalaUpload.as_view(), name='layanan_berkala_admin_upload_view'),
    path('yandiklat-list/', LayananUsulanDiklatView.as_view(), name='layanan_diklat_view'),
    path('yandiklat/', LayananUsulanDiklatListView.as_view(), name='layanan_diklat_list_view'),
    path('yandiklat-staf/', LayananUsulanDiklatStaffView.as_view(), name='layanan_diklat_staf_view'),
    path('yandiklat-usulan/', LayananUsulanDiklatCreateView.as_view(), name='layanan_diklat_usulan_view'),
    path('yandiklat-penugasan/', PenugasanDiklatCreateView.as_view(), name='layanan_diklat_penugasan_view'),
    path('yandiklat-pengalihan/<int:pk>/', PengalihanDiklatCreateView.as_view(), name='layanan_diklat_pengalihan_view'),
    path('yandiklat/<int:pk>/', LayananUsulanDiklatUpdateView.as_view(), name='layanan_diklat_update_view'),
    path('catatan-sdm/<int:pk>/', CatatanSDMUsulanLayananDiklatUpdateView.as_view(), name='catatan_sdm_update_view'),
    path('verifikasi-diklat/<int:pk>/', VerifikasiDiklatView.as_view(), name='verifikasi_diklat_update_view'),
    path('yaninovasi/', LayananUsulanInovasiView.as_view(), name='layanan_inovasi_view'),
    path('yaninovasi/<int:id>/', LayananUsulanInovasiUpdateView.as_view(), name='layanan_inovasi_update_view'),
    path('notifikasi/', NotifikasiView.as_view(), name='notifikasi_view'),
    path('notifikasi/<int:id>/', NotifikasiView.as_view(), name='notifikasi_update_view'),
]
