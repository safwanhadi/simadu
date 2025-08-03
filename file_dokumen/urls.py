from django.urls import path

from .views import (
    LayananGajiBerkalaDocxView,
    LayananUsulanCutiDocxView,
    LayananCutiDocxView,
    LayananCutiPelimpahanTugasDocxView,
    FormatPenilaianInovasiView,
    LayananDiklatSPTDocxView,
    LayananDiklatSPTDocxView2,
    TextSPTDiklatView,
)


urlpatterns=[
    path('berkala/<int:layanan_id>/', LayananGajiBerkalaDocxView.as_view(), name='berkala_docx'),
    path('usulan-cuti/<int:layanan_id>/', LayananUsulanCutiDocxView.as_view(), name='usulan_cuti_docx'),
    path('cuti/<int:layanan_id>/', LayananCutiDocxView.as_view(), name='cuti_docx'),
    path('dakung/<int:layanan_id>/', LayananCutiPelimpahanTugasDocxView.as_view(), name='dakung_docx'),
    path('format-penilaian-inovasi/<int:layanan_id>/', FormatPenilaianInovasiView.as_view(), name='format_penilaian_inovasi_docx'),
    path('spt-diklat/<int:diklat_id>/', LayananDiklatSPTDocxView.as_view(), name='spt_diklat_view'),
    path('spt-diklat-multi/<int:diklat_id>/', LayananDiklatSPTDocxView2.as_view(), name='spt_diklat_multi_view'),
    path('text-spt/<int:diklat_id>/', TextSPTDiklatView.as_view(), name='text_spt_view'),
    path('text-spt/<int:diklat_id>/<int:id>/', TextSPTDiklatView.as_view(), name='text_spt_update_view'),
]