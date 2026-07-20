from django.urls import path

from .views import (
    LayananGajiBerkalaDocxView,
    formulir_cuti_pdf,
    LayananUsulanCutiDocxView,
    LayananCutiDocxView,
    pelimpahan_tugas_pdf,
    FormatPenilaianInovasiView,
    LayananDiklatSPTDocxView,
    LayananDiklatSPTDocxView2,
    TextSPTDiklatView,
    GeneratePermohonanRekomendasiSIPView,
    GenerateSuratKecukupanSKPView,
    GenerateRekomendasiSIPView,
)


urlpatterns=[
    path('berkala/<int:layanan_id>/', LayananGajiBerkalaDocxView.as_view(), name='berkala_docx'),
    path("usulan-cuti/<int:pk>/formulir-pdf/", formulir_cuti_pdf, name="formulir_cuti_pdf"),
    path('usulan-cuti/<int:layanan_id>/', LayananUsulanCutiDocxView.as_view(), name='usulan_cuti_docx'),
    path('cuti/<int:layanan_id>/', LayananCutiDocxView.as_view(), name='cuti_docx'),
    path('pelimpahan-tugas/<int:pk>/', pelimpahan_tugas_pdf, name='pelimpahan_tugas_pdf'),
    path('format-penilaian-inovasi/<int:layanan_id>/', FormatPenilaianInovasiView.as_view(), name='format_penilaian_inovasi_docx'),
    path('spt-diklat/<int:diklat_id>/', LayananDiklatSPTDocxView.as_view(), name='spt_diklat_view'),
    path('spt-diklat-multi/<int:diklat_id>/', LayananDiklatSPTDocxView2.as_view(), name='spt_diklat_multi_view'),
    path('text-spt/<int:diklat_id>/', TextSPTDiklatView.as_view(), name='text_spt_view'),
    path('text-spt/<int:diklat_id>/<int:id>/', TextSPTDiklatView.as_view(), name='text_spt_update_view'),
    
    # docxtpl = docxtpl.DocxTemplate("path/to/template.docx")
    path(
        "sip/<int:pk>/generate/permohonan-rekomendasi/",
        GeneratePermohonanRekomendasiSIPView.as_view(),
        name="generate_permohonan_rekomendasi_sip",
    ),
    path(
        "sip/<int:pk>/generate/kecukupan-skp/",
        GenerateSuratKecukupanSKPView.as_view(),
        name="generate_surat_kecukupan_skp",
    ),
    path(
        "sip/<int:pk>/generate/rekomendasi-skp/",
        GenerateRekomendasiSIPView.as_view(),
        name="generate_rekomendasi_sip",
    ),
]
