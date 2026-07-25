from django.contrib import admin
from django import forms

from .models import (
    Bidang, InstansiDaerah, PejabatStruktur, SatuanKerjaInduk, StandarInstalasi,
    StandarSDM, SubBidang, UnitInstalasi, UnitOrganisasi,
)

# Register your models here.
@admin.register(StandarInstalasi)
class StandarInstalasiAdmin(admin.ModelAdmin):
    autocomplete_fields = ['kompetensi_wajib', 'kompetensi_wajib_parsial', 'kompetensi_pendukung']
    list_display = ('instalasi', 'jenis_sdm', 'get_wajib', 'get_wajib_parsial', 'get_pendukung')

    def get_wajib(self, obj):
            return ", ".join([p.kompetensi for p in obj.kompetensi_wajib.all()])
    
    def get_wajib_parsial(self, obj):
          return ", ".join([p.kompetensi for p in obj.kompetensi_wajib_parsial.all()])
  
    def get_pendukung(self, obj):
          return ", ".join([p.kompetensi for p in obj.kompetensi_pendukung.all()])
    
class UnitInstalasiAdmin(admin.ModelAdmin):
      list_display = ('instalasi', 'sub_bidang', 'slug')
      readonly_fields = ('nama_pimpinan',)
      # search_fields = ['instalasi', 'sub_bidang', ]
      
class SubBidangAdmin(admin.ModelAdmin):
    list_display = ('sub_bidang', 'bidang')
    readonly_fields = ('nama_pimpinan',)


class StrukturNodeAdmin(admin.ModelAdmin):
    readonly_fields = ('nama_pimpinan',)

admin.site.register(InstansiDaerah, StrukturNodeAdmin)
admin.site.register(SatuanKerjaInduk, StrukturNodeAdmin)
admin.site.register(UnitOrganisasi, StrukturNodeAdmin)
admin.site.register(Bidang, StrukturNodeAdmin)
admin.site.register(SubBidang, SubBidangAdmin)
admin.site.register(StandarSDM)
admin.site.register(UnitInstalasi, UnitInstalasiAdmin)


@admin.register(PejabatStruktur)
class PejabatStrukturAdmin(admin.ModelAdmin):
    list_display = (
        'pejabat', 'struktur_object', 'jenis_penugasan', 'nama_jabatan', 'tanggal_mulai',
        'tanggal_selesai', 'is_active',
    )
    list_filter = ('is_active', 'jenis_penugasan', 'tanggal_mulai')
    search_fields = (
        'pejabat__first_name', 'pejabat__last_name', 'pejabat__email',
        'nama_jabatan', 'instansi_daerah__instansi',
        'satuan_kerja_induk__satuan_kerja', 'unit_organisasi__unor',
        'bidang__bidang', 'sub_bidang__sub_bidang',
        'unit_instalasi__instalasi',
    )
    autocomplete_fields = ('pejabat',)
    readonly_fields = ('created_at', 'updated_at')
