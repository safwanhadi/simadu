from django.contrib import admin

from .forms import RiwayatJabatanAdminForm

from .models import (
    PangkatGolongan,
    DokumenSDM,
    UjiKompetensi,
    Kompetensi,
    JenjangJafung,
    JenjangStruktural,
    RiwayatPendidikan, 
    RiwayatPengangkatan,
    RiwayatBekerja,
    RiwayatPenempatan,
    RiwayatProfesi,
    RiwayatSIPProfesi,
    RiwayatPanggol,
    RiwayatJabatan,
    RiwayatGajiBerkala,
    RiwayatSKP,
    RiwayatOrganisasi,
    RiwayatDiklat,
    RiwayatCuti,
    KlaimCutiTunda,
    RiwayatHukuman,
    RiwayatPenghargaan,
    RiwayatKeluarga,
    OrangTua,
    Pasangan,
    Anak,
    PredikatKinerja,
    RiwayatInovasi,
    BidangInovasi,
    KewajibanDokumen,
)

# Register your models here.
class RiwayatJabatanAdmin(admin.ModelAdmin):
    form = RiwayatJabatanAdminForm


class KewajibanDokumenInline(admin.TabularInline):
    model = KewajibanDokumen
    extra = 0
    fields = ('status_pegawai', 'wajib')


class DokumenSDMAdmin(admin.ModelAdmin):
    list_display = ('nama', 'url', 'daftar_status_wajib')
    search_fields = ('nama', 'url')
    inlines = (KewajibanDokumenInline,)

    @admin.display(description='Wajib untuk status')
    def daftar_status_wajib(self, obj):
        return ', '.join(
            obj.kewajiban_status.filter(wajib=True).values_list(
                'status_pegawai', flat=True,
            )
        ) or '-'


@admin.register(KewajibanDokumen)
class KewajibanDokumenAdmin(admin.ModelAdmin):
    list_display = ('dokumen', 'status_pegawai', 'wajib')
    list_filter = ('status_pegawai', 'wajib')
    search_fields = ('dokumen__nama', 'dokumen__url')
    
class KompetensiAdmin(admin.ModelAdmin):
    list_display = ('pegawai', 'get_kompetensi', 'berlaku_sd')
    search_fields = ('pegawai',)
    autocomplete_fields = ('kompetensi',)
    
    def get_kompetensi(self, obj):
            return obj.kompetensi.kompetensi if obj.kompetensi else '-'
        
    get_kompetensi.short_description = 'Kompetensi Pegawai'
    
# class KompetensiAdmin(admin.ModelAdmin):
#     list_display = ('display_pegawai', 'kompetensi', 'berlaku_sd')
#     search_fields = ('pegawai',)
#     autocomplete_fields = ('pegawai',)
    
#     def display_pegawai(self, obj):
#         """Returns a comma-separated list of authors for the book."""
#         return ", ".join([f'{pegawai.first_name} {pegawai.last_name}' for pegawai in obj.pegawai.all()])
  
class RiwayatCutiAdmin(admin.ModelAdmin):
    list_display = ('pegawai', 'jenis_cuti', 'tgl_mulai_cuti', 'tgl_akhir_cuti', 'status_cuti')
admin.site.register(PangkatGolongan)
admin.site.register(DokumenSDM, DokumenSDMAdmin)
admin.site.register(JenjangStruktural)
admin.site.register(JenjangJafung)
admin.site.register(RiwayatPendidikan)
admin.site.register(RiwayatPengangkatan)
admin.site.register(RiwayatBekerja)
admin.site.register(RiwayatPenempatan)
admin.site.register(RiwayatProfesi)
admin.site.register(RiwayatSIPProfesi)
admin.site.register(RiwayatPanggol)
admin.site.register(UjiKompetensi)
admin.site.register(Kompetensi, KompetensiAdmin)
admin.site.register(RiwayatJabatan, RiwayatJabatanAdmin)
admin.site.register(RiwayatGajiBerkala)
admin.site.register(RiwayatSKP)
admin.site.register(RiwayatOrganisasi)
admin.site.register(RiwayatDiklat)
admin.site.register(RiwayatCuti, RiwayatCutiAdmin)
admin.site.register(KlaimCutiTunda)
admin.site.register(RiwayatHukuman)
admin.site.register(RiwayatPenghargaan)
admin.site.register(RiwayatKeluarga)
admin.site.register(OrangTua)
admin.site.register(Pasangan)
admin.site.register(Anak)
admin.site.register(PredikatKinerja)
admin.site.register(RiwayatInovasi)
admin.site.register(BidangInovasi)
