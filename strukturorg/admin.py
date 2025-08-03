from django.contrib import admin
from django import forms

from .models import InstansiDaerah, SatuanKerjaInduk, UnitOrganisasi, Bidang, SubBidang, StandarSDM, UnitInstalasi, StandarInstalasi

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
      # search_fields = ['instalasi', 'sub_bidang', ]

admin.site.register(InstansiDaerah)
admin.site.register(SatuanKerjaInduk)
admin.site.register(UnitOrganisasi)
admin.site.register(Bidang)
admin.site.register(SubBidang)
admin.site.register(StandarSDM)
admin.site.register(UnitInstalasi, UnitInstalasiAdmin)