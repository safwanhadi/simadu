from django.contrib import admin
from .models import (
    KategoriJadwalDinas, 
    DetailKategoriJadwalDinas, 
    JadwalDinasSDM, 
    ApprovedJadwalDinasSDM,
    JenisSDMPerinstalasi, 
    KehadiranKegiatan, 
    AlasanTidakHadir, 
    JenisKegiatan, 
    DaftarKegiatanPegawai,
    HariLibur
    )

# Register your models here.
class DetailKategoriJadwalDinasAdmin(admin.ModelAdmin):
    list_display = ('kategori_dinas', 'hari', 'kategori_jadwal', 'waktu_datang', 'waktu_pulang', 'durasi_kerja')
    
class KehadiranKegiatanAdmin(admin.ModelAdmin):
    list_display = ('get_pegawai', 'get_kegiatan', 'tanggal', 'hadir', 'status_ketepatan', 'alasan')
    
    def get_kegiatan(self, obj):
        return obj.pegawai.kegiatan.jenis_kegiatan
    get_kegiatan.short_description = 'Kegiatan'
    get_kegiatan.admin_order_field = 'pegawai__kegiatan__jenis_kegiatan'
    
    def get_pegawai(self, obj):
        return obj.pegawai.pegawai.full_name
    get_pegawai.short_description = 'Pegawai'
    get_pegawai.admin_order_field = 'pegawai__pegawai__full_name'
    
class DaftarKegiatanPegawaiAdmin(admin.ModelAdmin):
    list_display = ('get_pegawai', 'instalasi', 'bulan', 'tahun')
    
    def get_pegawai(self, obj):
        return obj.pegawai.full_name
    get_pegawai.short_description = 'Pegawai'
    get_pegawai.admin_order_field = 'pegawai__full_name'

admin.site.register(KategoriJadwalDinas)
admin.site.register(DetailKategoriJadwalDinas, DetailKategoriJadwalDinasAdmin)
admin.site.register(JenisSDMPerinstalasi)
admin.site.register(JadwalDinasSDM)
admin.site.register(DaftarKegiatanPegawai, DaftarKegiatanPegawaiAdmin)
admin.site.register(AlasanTidakHadir)
admin.site.register(KehadiranKegiatan, KehadiranKegiatanAdmin)
admin.site.register(JenisKegiatan)
admin.site.register(HariLibur)
admin.site.register(ApprovedJadwalDinasSDM)
