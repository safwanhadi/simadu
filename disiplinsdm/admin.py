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
    HariLibur,
    PolaKerjaPegawai,
    AturanToleransiKeterlambatan,
    MappingMesinAbsensi,
    LogKehadiran,
    AbsensiHarian,
    LogAktivitasAbsen,
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
    list_display = ('get_pegawai', 'instalasi', 'kegiatan', 'bulan', 'tahun')
    
    def get_pegawai(self, obj):
        return obj.pegawai.full_name
    get_pegawai.short_description = 'Pegawai'
    get_pegawai.admin_order_field = 'pegawai__full_name'


@admin.register(AturanToleransiKeterlambatan)
class AturanToleransiAdmin(admin.ModelAdmin):
    list_display = ('nama_aturan', 'urutan', 'batas_atas_menit', 'status_yang_dihasilkan', 'is_aktif')
    list_editable = ('is_aktif', 'urutan', 'batas_atas_menit', 'status_yang_dihasilkan')
    list_filter = ('is_aktif',)

class MappingMesinAbsensiAdmin(admin.ModelAdmin):
    list_display=('mesin_id', 'pegawai')
    # search_fields=('pegawai',)
    autocomplete_fields = ('pegawai',)
    
class ApprovedJadwalDinasSDMAdmin(admin.ModelAdmin):
    raw_id_fields = ['pegawai', 'kategori_jadwal', 'approved_by']
    
class LogAktivitasAbsenAdmin(admin.ModelAdmin):
    list_display = ('absensi_harian', 'tipe', 'waktu', 'status_ketepatan')
    
admin.site.register(MappingMesinAbsensi, MappingMesinAbsensiAdmin)
admin.site.register(LogKehadiran)
admin.site.register(AbsensiHarian)
admin.site.register(LogAktivitasAbsen, LogAktivitasAbsenAdmin)
admin.site.register(KategoriJadwalDinas)
admin.site.register(DetailKategoriJadwalDinas, DetailKategoriJadwalDinasAdmin)
admin.site.register(JenisSDMPerinstalasi)
admin.site.register(JadwalDinasSDM)
admin.site.register(DaftarKegiatanPegawai, DaftarKegiatanPegawaiAdmin)
admin.site.register(AlasanTidakHadir)
admin.site.register(KehadiranKegiatan, KehadiranKegiatanAdmin)
admin.site.register(JenisKegiatan)
admin.site.register(HariLibur)
admin.site.register(ApprovedJadwalDinasSDM, ApprovedJadwalDinasSDMAdmin)


@admin.register(PolaKerjaPegawai)
class PolaKerjaPegawaiAdmin(admin.ModelAdmin):
    list_display = ('pegawai', 'pola_kerja', 'berlaku_mulai', 'berlaku_sampai')
    list_filter = ('pola_kerja',)
    search_fields = ('pegawai__first_name', 'pegawai__last_name', 'pegawai__email')
    autocomplete_fields = ('pegawai',)
