from django.db import models
from django.db.models import ExpressionWrapper, DurationField
from datetime import timedelta
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.template.defaultfilters import slugify
from django.db.models import Sum, Case, When, F, Q, Count
from datetime import datetime, date
from .utils import hitung_standar_jam_kerja, hitung_standar_max_jam_kerja, jam_standar_min_hari, jam_standar_max_hari

# Create your models here.
KATEGORIJADWAL = (
    ('Pagi', 'Pagi'),
    ('Midle', 'Midle'),
    ('Siang', 'Siang'),
    ('Malam', 'Malam'),

)

KATEGORIDINAS = (
    ('Reguler', 'Reguler'),
    ('Piket', 'Piket'),
    ('Libur', 'Libur')
)

class KategoriJadwalDinas(models.Model):
    kategori_dinas = models.CharField(max_length=10)
    update_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.kategori_dinas

HARI=(
    ("Senin s/d kamis", "Senin s/d kamis"),
    ("Jumat", "Jumat"),
    ("Sabtu", "Sabtu"),
    ("Ahad", "Ahad"),
)

class DetailKategoriJadwalDinas(models.Model):
    kategori_dinas = models.ForeignKey(KategoriJadwalDinas, on_delete=models.CASCADE)
    hari = models.CharField(max_length=50, blank=True, choices=HARI)
    durasi_kerja = models.DecimalField(blank=True, null=True, max_digits=5, decimal_places=2)
    kategori_jadwal = models.CharField(max_length=25)
    akronim = models.CharField(max_length=5, blank=True, null=True)
    waktu_datang = models.TimeField(blank=True, null=True)
    waktu_pulang = models.TimeField(blank=True, null=True)
    update_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.kategori_dinas}-{self.hari}-{self.kategori_jadwal}'
    
    @property
    def rentang_waktu(self):
        jam = 0
        if self.kategori_jadwal == 'Malam':
            jam = self.waktu_datang.hour - self.waktu_pulang.hour
        else:
            jam = self.waktu_pulang.hour - self.waktu_datang.hour
        return f"{int(jam)} jam"

    def save(self, *args, **kwargs):
        if self.waktu_datang and self.waktu_pulang:
            dt_datang = datetime.combine(date.today(), self.waktu_datang)
            dt_pulang = datetime.combine(date.today(), self.waktu_pulang)
            if dt_pulang < dt_datang:
                dt_pulang += timedelta(days=1)  
            self.durasi_kerja = round((dt_pulang - dt_datang).total_seconds() / 3600, 1)  
              
        super().save(*args, **kwargs)

    
    
class HariLibur(models.Model):
    tanggal = models.DateField(unique=True)
    keterangan = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.tanggal} - {self.keterangan}"

STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('diajukan', 'Diajukan'),
    ('disetujui', 'Disetujui'),
    ('ditolak', 'Ditolak'),
]
CUTI_KEYWORDS = ('cuti', )      # bisa tambahkan 'izin', 'sakit', dll.
    
class JenisSDMPerinstalasi(models.Model):
    jenis_sdm = models.ForeignKey('jenissdm.JenisSDM', on_delete=models.SET_NULL, null=True, blank=True)
    pegawai = models.ForeignKey('myaccount.Users', on_delete=models.CASCADE)
    unor = models.ForeignKey('strukturorg.UnitOrganisasi', on_delete=models.SET_NULL, null=True, blank=True)
    bidang = models.ForeignKey('strukturorg.Bidang', on_delete=models.SET_NULL, null=True, blank=True)
    sub_bidang = models.ForeignKey('strukturorg.SubBidang', on_delete=models.SET_NULL, null=True, blank=True)
    instalasi = models.ForeignKey('strukturorg.UnitInstalasi', on_delete=models.SET_NULL, null=True, blank=True)
    bulan = models.SmallIntegerField(null=True, blank=True)
    tahun = models.SmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    alasan_penolakan = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.bulan}/{self.tahun}) - {self.kurang_lebih_jam_kerja}'
    
    @property
    def kurang_lebih_jam_kerja(self):
        total = 0
        for jadwal in self.jadwaldinassdm_set.select_related('kategori_jadwal'):
            datang = jadwal.kategori_jadwal.waktu_datang if hasattr(jadwal, 'kategori_jadwal') and hasattr(jadwal.kategori_jadwal, 'waktu_datang') else None
            pulang = jadwal.kategori_jadwal.waktu_pulang if hasattr(jadwal, 'kategori_jadwal') and hasattr(jadwal.kategori_jadwal, 'waktu_pulang') else None
            if datang and pulang:
                dt_mulai = datetime.combine(date.today(), datang)
                dt_selesai = datetime.combine(date.today(), pulang)
                if dt_selesai < dt_mulai:
                    dt_selesai += timedelta(days=1)
                durasi_jam = (dt_selesai - dt_mulai).total_seconds() / 3600
                total += durasi_jam
        return round(total, 1)
    
    @property
    def jam_cuti_min(self) -> float:
        tgls = self.jadwaldinassdm_set.filter(
            kategori_jadwal__kategori_jadwal__iregex=r'^(?:' + '|'.join(CUTI_KEYWORDS) + r')',
            # kolom waktu NULL sebagai second safety‑net
            kategori_jadwal__waktu_datang__isnull=True,
            kategori_jadwal__waktu_pulang__isnull=True
        ).values_list('tanggal', flat=True)
        return round(sum(jam_standar_min_hari(tgl) for tgl in tgls), 1)

    @property
    def jam_cuti_max(self) -> float:
        tgls = self.jadwaldinassdm_set.filter(
            kategori_jadwal__kategori_jadwal__iregex=r'^(?:' + '|'.join(CUTI_KEYWORDS) + r')',
            kategori_jadwal__waktu_datang__isnull=True,
            kategori_jadwal__waktu_pulang__isnull=True
        ).values_list('tanggal', flat=True)
        return round(sum(jam_standar_max_hari(tgl) for tgl in tgls), 1)
    
    @property
    def standar_min_jam_kerja(self):
        if self.bulan and self.tahun:
            #kurang lebih 39 jam seminggu
            return hitung_standar_jam_kerja(HariLibur, self.bulan, self.tahun)
        return 0
    
    @property
    def standar_max_jam_kerja(self):
        if self.bulan and self.tahun:
            #kurang lebih 40 jam seminggu
            return hitung_standar_max_jam_kerja(HariLibur, self.bulan, self.tahun)
        return 0
    
    @property
    def standar_min_efektif(self):
        return round(max(self.standar_min_jam_kerja - self.jam_cuti_min, 0), 1)

    @property
    def standar_max_efektif(self):
        return round(max(self.standar_max_jam_kerja - self.jam_cuti_max, 0), 1)
    
    @property
    def selisih_jam_kerja(self):
        aktual = self.kurang_lebih_jam_kerja
        min_std = self.standar_min_efektif
        max_std = self.standar_max_efektif

        if aktual < min_std:
            return round(aktual - min_std, 1)  # kurang jam
        elif aktual <= max_std:
            return 0.0  # wajar
        return round(aktual - max_std, 1)  # lembur
    

class JadwalDinasSDM(models.Model):
    pegawai = models.ForeignKey(JenisSDMPerinstalasi, on_delete=models.CASCADE, blank=True, null=True)
    tanggal = models.DateField()
    kategori_jadwal = models.ForeignKey(DetailKategoriJadwalDinas, on_delete=models.SET_NULL, blank=True, null=True)
    catatan = models.CharField(max_length=255, blank=True, null=True)
    update_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.kategori_jadwal is not None:
            return f'{self.pegawai.pegawai.full_name} - {self.kategori_jadwal.kategori_jadwal} ({self.tanggal})'
        return f'{self.pegawai.pegawai.full_name} - {self.kategori_jadwal} ({self.tanggal})'
    
    
class ApprovedJadwalDinasSDM(models.Model):
    pegawai = models.ForeignKey(JenisSDMPerinstalasi, on_delete=models.CASCADE, blank=True, null=True)
    tanggal = models.DateField()
    kategori_jadwal = models.ForeignKey(DetailKategoriJadwalDinas, on_delete=models.SET_NULL, blank=True, null=True)
    catatan = models.CharField(max_length=255, blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey('myaccount.Users', on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.kategori_jadwal is not None:
            return f'{self.pegawai.pegawai.full_name} - {self.kategori_jadwal.kategori_jadwal} ({self.tanggal})'
        return f'{self.pegawai.pegawai.full_name} - {self.kategori_jadwal} ({self.tanggal})'


class AlasanTidakHadir(models.Model):
    alasan = models.CharField(max_length=50)
    update_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.alasan


class JenisKegiatan(models.Model):
    jenis_kegiatan = models.CharField(max_length=50)
    slug = models.CharField(max_length=25, blank=True)
    ket = models.TextField(blank=True)
    
    def __str__(self):
        return self.jenis_kegiatan
    
@receiver(pre_save, sender=JenisKegiatan)
def slugify_jenis_kegiatan(sender, instance, *args, **kwargs):
    instance.slug = slugify(instance.jenis_kegiatan)


class DaftarKegiatanPegawai(models.Model):
    jenis_sdm = models.ForeignKey('jenissdm.JenisSDM', on_delete=models.SET_NULL, null=True, blank=True)
    pegawai = models.ForeignKey('myaccount.Users', on_delete=models.CASCADE)
    unor = models.ForeignKey('strukturorg.UnitOrganisasi', on_delete=models.SET_NULL, null=True, blank=True)
    bidang = models.ForeignKey('strukturorg.Bidang', on_delete=models.SET_NULL, null=True, blank=True)
    sub_bidang = models.ForeignKey('strukturorg.SubBidang', on_delete=models.SET_NULL, null=True, blank=True)
    instalasi = models.ForeignKey('strukturorg.UnitInstalasi', on_delete=models.SET_NULL, null=True, blank=True)
    kegiatan = models.ForeignKey(JenisKegiatan, on_delete=models.SET_NULL, null=True)
    bulan = models.SmallIntegerField(null=True, blank=True)
    tahun = models.SmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f'{self.pegawai.full_name}-{self.kegiatan} ({self.bulan}/{self.tahun})'
    
    @property
    def jumlah_hadir(self):
        status_hadir = self.kehadirankegiatan_set.values('pegawai__instalasi').annotate(
            jlh_hadir = Count(Case(When(Q(hadir=True), then=F('id'))))
        )
        hadir = 0
        if status_hadir:
            hadir = status_hadir[0]['jlh_hadir']
        return hadir
    
    @property
    def jumlah_tk(self):
        status_hadir = self.kehadirankegiatan_set.values('pegawai__instalasi').annotate(
                jlh_tk = Count(Case(When(Q(alasan__alasan='Tanpa Keterangan') & Q(hadir=False), then=F('id'))))
        )
        tk = 0
        if status_hadir:
            tk = status_hadir[0]['jlh_tk']
        return tk
    
    @property
    def jumlah_izin(self):
        status_hadir = self.kehadirankegiatan_set.values('pegawai__instalasi').annotate(
            jlh_izin = Count(Case(When(Q(alasan__alasan='Izin') & Q(hadir=False), then=F('id'))))
        )
        izin = 0
        if status_hadir:
            izin = status_hadir[0]['jlh_izin']
        return izin
    
    @property
    def jumlah_sakit(self):
        status_hadir = self.kehadirankegiatan_set.values('pegawai__instalasi').annotate(
            jlh_sakit = Count(Case(When(Q(alasan__alasan='Sakit') & Q(hadir=False), then=F('id'))))
        )
        sakit = 0
        if status_hadir:
            sakit = status_hadir[0]['jlh_sakit']
        return sakit


STATUS_KEHADIRAN = (
    ('Tepat Waktu', 'Tepat Waktu'),
    ('Terlambat', 'Terlambat'),
    ('Cepat Pulang', 'Cepat Pulang'),
)


class KehadiranKegiatan(models.Model):
    pegawai = models.ForeignKey(DaftarKegiatanPegawai, on_delete=models.CASCADE, null=True)
    tanggal = models.DateTimeField()
    hadir = models.BooleanField(default=False)
    alasan = models.ForeignKey(AlasanTidakHadir, on_delete=models.SET_NULL, null=True, blank=True)
    status_ketepatan = models.CharField(max_length=20, choices=STATUS_KEHADIRAN, blank=True, null=True)
    ket = models.TextField(blank=True)

    def __str__(self):
        if self.pegawai is None:
            return 'Kehadiran tidak terdaftar'
        if self.hadir:
            return f'{self.pegawai.pegawai.full_name} Hadir'
        return f'{self.pegawai.pegawai.full_name} Tidak hadir'