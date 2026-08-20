from django.db import models
from django.db.models import ExpressionWrapper, DurationField
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.template.defaultfilters import slugify
from django.db.models import Sum, Case, When, F, Q, Count
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, date
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


class PolaKerjaPegawai(models.Model):
    REGULER = 'reguler'
    SHIFT = 'shift'
    POLA_KERJA_CHOICES = (
        (REGULER, 'Reguler'),
        (SHIFT, 'Shift'),
    )

    pegawai = models.ForeignKey(
        'myaccount.Users',
        on_delete=models.CASCADE,
        related_name='riwayat_pola_kerja',
    )
    pola_kerja = models.CharField(max_length=10, choices=POLA_KERJA_CHOICES)
    berlaku_mulai = models.DateField()
    berlaku_sampai = models.DateField(null=True, blank=True)
    keterangan = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-berlaku_mulai', '-pk')
        verbose_name = 'Pola kerja pegawai'
        verbose_name_plural = 'Riwayat pola kerja pegawai'

    def __str__(self):
        return f'{self.pegawai} - {self.get_pola_kerja_display()}'

    def clean(self):
        super().clean()
        if self.berlaku_sampai and self.berlaku_sampai < self.berlaku_mulai:
            raise ValidationError({
                'berlaku_sampai': 'Tanggal selesai tidak boleh sebelum tanggal mulai.'
            })

        if not self.pegawai_id or not self.berlaku_mulai:
            return
        overlaps = type(self).objects.filter(
            pegawai_id=self.pegawai_id,
            berlaku_mulai__lte=self.berlaku_sampai or date.max,
        ).filter(
            Q(berlaku_sampai__isnull=True)
            | Q(berlaku_sampai__gte=self.berlaku_mulai)
        )
        if self.pk:
            overlaps = overlaps.exclude(pk=self.pk)
        if overlaps.exists():
            raise ValidationError('Periode pola kerja pegawai tidak boleh tumpang tindih.')

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
        return f'{self.pegawai.first_name} ({self.bulan}/{self.tahun})'
    
    @property
    def kurang_lebih_jam_kerja(self):
        total = 0.0
        tz = timezone.get_current_timezone()

        for jadwal in self.jadwaldinassdm_set.select_related('kategori_jadwal'):
            kj = getattr(jadwal, 'kategori_jadwal', None)
            datang = getattr(kj, 'waktu_datang', None)
            pulang = getattr(kj, 'waktu_pulang', None)

            if datang and pulang:
                dt_mulai = timezone.make_aware(
                    datetime.combine(date.today(), datang),
                    tz
                )
                dt_selesai = timezone.make_aware(
                    datetime.combine(date.today(), pulang),
                    tz
                )

                # shift malam
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


# Pastikan choices ini ada dan digunakan oleh KehadiranKegiatan.status_ketepatan
STATUS_KEHADIRAN = (
    ('Tepat Waktu', 'Tepat Waktu'),
    ('Terlambat Ringan', 'Terlambat Ringan'),
    ('Terlambat Sedang', 'Terlambat Sedang'),
    ('Terlambat Berat', 'Terlambat Berat'),
    ('Cepat Pulang', 'Cepat Pulang'),
)

class AturanToleransiKeterlambatan(models.Model):
    nama_aturan = models.CharField(max_length=100, help_text="Deskripsi singkat aturan, misal: Toleransi Tepat Waktu")
    batas_atas_menit = models.PositiveIntegerField(help_text="Batas atas keterlambatan dalam menit untuk aturan ini.")
    status_yang_dihasilkan = models.CharField(
        max_length=30, 
        choices=STATUS_KEHADIRAN,
        help_text="Status yang akan diberikan jika keterlambatan memenuhi aturan ini."
    )
    urutan = models.PositiveSmallIntegerField(
        default=0, 
        help_text="Urutan evaluasi aturan, dari yang terkecil (paling ketat) ke terbesar."
    )
    is_aktif = models.BooleanField(default=True, help_text="Aktifkan atau nonaktifkan aturan ini.")

    class Meta:
        ordering = ['urutan']
        verbose_name = "Aturan Toleransi Keterlambatan"
        verbose_name_plural = "Aturan Toleransi Keterlambatan"

    def __str__(self):
        return f"{self.urutan}. Jika terlambat <= {self.batas_atas_menit} menit -> {self.status_yang_dihasilkan}"

# Setelah menambahkan model ini, jalankan:
# python manage.py makemigrations
# python manage.py migrate


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
    
    class Meta:
        verbose_name = "Daftar Kegiatan Pegawai"
        verbose_name_plural = "Daftar Kegiatan Pegawai"
        
        # DEFINISI UNIQUE CONSTRAINT UNTUK BULK_CREATE
        constraints = [
            models.UniqueConstraint(
                fields=['pegawai', 'kegiatan', 'bulan', 'tahun'],
                name='unique_rekap_kegiatan_pegawai_bulanan'
            )
        ]

    def __str__(self):
        return f'{self.pegawai.full_name}-{self.kegiatan} ({self.bulan}/{self.tahun})'
    
    @property
    def visite(self):
        """
        Menghitung total kehadiran dengan keterangan 'visite' untuk instance 
        DaftarKegiatanPegawai ini.
        Ini adalah cara yang lebih efisien dan lebih 'Django-native'.
        """
        # 1. Ambil semua objek terkait dari KehadiranKegiatan.
        # 2. Filter objek-objek tersebut yang memiliki ket 'visite'.
        # 3. Hitung jumlahnya.
        return self.kehadirankegiatan_set.filter(ket__icontains='visite', pegawai__pegawai__profil_user__is_dokter_spesialis=True).count()
    
    @property
    def terjadwal(self):
        return self.kehadirankegiatan_set.filter(ket__icontains='Sesuai').count()
    
    @property
    def jumlah_hadir(self):
        return self.kehadirankegiatan_set.filter(hadir=True).count()
    
    @property
    def jumlah_tk(self):
        return self.kehadirankegiatan_set.filter(alasan__alasan__icontains='Tanpa Keterangan').count()
    
    @property
    def jumlah_izin(self):
        return self.kehadirankegiatan_set.filter(alasan__alasan__icontains='Izin').count()
        
    @property
    def jumlah_sakit(self):
        return self.kehadirankegiatan_set.filter(alasan__alasan='Sakit').count()



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
    
    class Meta:
        verbose_name = "Kehadiran Kegiatan"
        verbose_name_plural = "Kehadiran Kegiatan"
        ordering = ['-tanggal']
        constraints = [
            models.UniqueConstraint(
                fields=['pegawai_id', 'tanggal'],
                name='unique_kehadiran_pegawai_tanggal'
            )
        ]

    
class MappingMesinAbsensi(models.Model):
    mesin_id = models.CharField(max_length=255, unique=True, verbose_name="ID Pegawai Mesin")
    pegawai = models.OneToOneField('myaccount.Users', on_delete=models.CASCADE, verbose_name="Pegawai SIMADU")
    
    class Meta:
        verbose_name = "Mapping Mesin Absensi"
        verbose_name_plural = "Mapping Mesin Absensi"
    
    def __str__(self):
        return f'Mesin ID: {self.mesin_id} - Pegawai: {self.pegawai.full_name}'
      
    
class LogKehadiran(models.Model):
    mapping = models.ForeignKey(MappingMesinAbsensi, on_delete=models.CASCADE)
    datetime = models.DateTimeField()
    direction = models.CharField(max_length=10)  # 'IN' atau 'OUT'
    devicename = models.CharField(max_length=255)
    personname = models.CharField(max_length=255)
    
    class Meta:
        verbose_name = "Log Kehadiran"
        verbose_name_plural = "Log Kehadiran"
        # Mencegah duplikasi jika pegawai melakukan presensi ulang (shift ganti)
        constraints = [
            models.UniqueConstraint(
                fields=['mapping', 'datetime', 'direction'],
                name='unique_log_pegawai_waktu_arah'
            )
        ]
        ordering = ['-datetime'] # Default urutkan data terbaru di atas
        indexes = [
            models.Index(fields=['mapping', 'datetime']),
        ]
    
    def __str__(self):
        return f'{self.personname} - {self.direction} at {self.datetime} (Device: {self.devicename})'


################################### MODEL BARU UNTUK PRESENSI #################################

class AbsensiHarian(models.Model):
    """
    MODEL PARENT (Header)
    Mencatat rangkuman kehadiran seorang pegawai dalam satu hari tertentu.
    """
    pegawai = models.ForeignKey('myaccount.Users', on_delete=models.CASCADE)
    tanggal = models.DateField()
    unor = models.ForeignKey('strukturorg.UnitOrganisasi', on_delete=models.PROTECT, verbose_name="Unit Organisasi")
    bidang = models.ForeignKey('strukturorg.Bidang', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Bidang / Bagian")
    sub_bidang = models.ForeignKey('strukturorg.SubBidang', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Tim Kerja / Sub Bagian")
    instalasi = models.ForeignKey('strukturorg.UnitInstalasi', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Instalasi / Ruangan")
    
    # Rangkuman status final hari itu (diisi otomatis via trigger/save method atau background task)
    STATUS_PILIHAN = [
        ('', 'Belum Presensi'),
        ('HADIR', 'Hadir'),
        ('ALPA', 'Alpa / Tanpa Keterangan'),
        ('IZIN', 'Izin / Sakit / Cuti'),
        ('DINAS', 'Dinas Luar'),
        ('LIBUR', 'Libur')
    ]
    status_final = models.CharField(max_length=10, choices=STATUS_PILIHAN, default='')
    keterangan = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('pegawai', 'tanggal') # Memastikan 1 pegawai hanya punya 1 parent per hari
        ordering = ['-tanggal']
        # Tambahkan indexing pada kombinasi struktur ini untuk mempercepat query laporan manajemen
        indexes = [
            models.Index(fields=['tanggal', 'unor']),
            models.Index(fields=['tanggal', 'bidang']),
            models.Index(fields=['tanggal', 'sub_bidang']),
        ]

    def __str__(self):
        return f"{self.pegawai.full_name} - {self.tanggal}: {self.status_final}"


class LogAktivitasAbsen(models.Model):
    """
    MODEL CHILD (Detail)
    Mencatat setiap detak transaksi/kegiatan absen pegawai pada hari tersebut.
    """
    TIPE_LOG = [
        ('DATANG', 'Absen Datang'),
        ('APEL', 'Apel Pagi'),
        ('PULANG', 'Absen Pulang'),
        ('ISHOMA_OUT', 'Keluar Istirahat'),
        ('ISHOMA_IN', 'Masuk Istirahat'),
    ]
    
    absensi_harian = models.ForeignKey(AbsensiHarian, on_delete=models.CASCADE, related_name='logs')
    tipe = models.CharField(max_length=15, choices=TIPE_LOG)
    waktu = models.DateTimeField() # Menyimpan tanggal dan jam presisi dari mesin/aplikasi
    
    status_ketepatan = models.CharField(max_length=50, blank=True, null=True) # Misal: "Tepat Waktu", "Terlambat"
    alasan = models.ForeignKey('AlasanTidakHadir', on_delete=models.SET_NULL, null=True, blank=True)
    devicename = models.CharField(max_length=50, blank=True, null=True) # Untuk pelacakan fingerprint/perangkat

    class Meta:
        ordering = ['waktu']

    def __str__(self):
        return f"{self.tipe} - {self.waktu.time()}"
