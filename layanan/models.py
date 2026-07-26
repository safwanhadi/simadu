from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.template.defaultfilters import slugify
from tinymce.models import HTMLField

from myaccount.models import Users
from dokumen.models import (
    RiwayatPendidikan, 
    RiwayatPanggol,
    RiwayatPengangkatan,
    RiwayatBekerja,
    RiwayatPenempatan,
    RiwayatProfesi,
    RiwayatPAK,
    RiwayatJabatan,
    RiwayatKinerja,
    RiwayatGajiBerkala,
    RiwayatSKP,
    RiwayatOrganisasi,
    RiwayatDiklat,
    RiwayatCuti,
    RiwayatHukuman,
    RiwayatPenghargaan,
    RiwayatKeluarga,
    UjiKompetensi,
    JENIS_JABATAN,
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_file_size(value):
    filesize = value.size
    if filesize > 2621440:  # 2.5MB limit
        raise ValidationError(_("Ukuran maksimal file 2.5 MB"))


# Create your models here.

class JenisLayanan(models.Model):
    nama = models.CharField(max_length=100)
    status = models.BooleanField(default=False)
    icon = models.CharField(max_length=50, blank=True)
    url = models.CharField(max_length=50, blank=True, null=True, unique=True)

    def __str__(self):
        return self.nama

STATUS = (
    ('belum', 'Belum diproses'),
    ('pengajuan', 'Pengajuan'),
    ('proses', 'Proses'),
    ('selesai', 'Selesai')
)


class LayananPencantumanGelar(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    pendidikan = models.ForeignKey(RiwayatPendidikan, on_delete=models.CASCADE)
    sk_tubel_ibel = models.FileField(upload_to="tubel_ibel/sk/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    status = models.CharField(max_length=50, default='belum', choices=STATUS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.layanan} - {self.status})'


class LayananGajiBerkala(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    riwayat = models.ForeignKey(RiwayatGajiBerkala, on_delete=models.SET_NULL, related_name='berkala_sebelum', null=True)
    berkala = models.ForeignKey(RiwayatGajiBerkala, on_delete=models.SET_NULL, related_name='berkala_saat_ini', null=True, blank=True)
    # kinerja = models.ForeignKey(RiwayatKinerja, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=50, default='belum', choices=STATUS)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        data = None
        if self.berkala is not None:
            data = self.berkala.tmt_gaji
        return f'{self.pegawai} ({self.layanan} - {data}) - {self.status}'


# syarat kenaikan pangkat
# struktural dan pelaksana: SKP dua tahun terakhir, sk pangkat terakhir, ijazah dan transkrip, sk pns dan cpns
# fungsional --> syarat pelaksana + PAK (semua pak) + SK Jabatan Fungsional
class LayananNaikPangkat(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.CASCADE)
    sk_kp_terakhir = models.ForeignKey('dokumen.RiwayatPanggol', on_delete=models.SET_NULL, null=True)
    kinerja_dua_thn = models.ManyToManyField('dokumen.RiwayatKinerja', blank=True)
    sk_jabfung = models.ForeignKey('dokumen.RiwayatJabatan', on_delete=models.SET_NULL, null=True, blank=True, help_text="Khusus Pejabat Fungsional")
    pak = models.ManyToManyField('dokumen.RiwayatPAK', blank=True, help_text="Khusus Pejabat Fungsional")
    pendidikan = models.ForeignKey('dokumen.RiwayatPendidikan', on_delete=models.SET_NULL, null=True)
    pengangkatan = models.ForeignKey('dokumen.RiwayatPengangkatan', on_delete=models.SET_NULL, null=True)
    mutasi = models.ForeignKey('dokumen.RiwayatBekerja', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=50, default='belum', choices=STATUS)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.layanan} - {self.status})'

# PAK terakhir, SKP dua tahun, sertifikat kompetensi, STR
class LayananNaikJabatan(models.Model):
    KATEGORI_PENGELOLAAN = (
        ('kenaikan', 'Kenaikan Jabatan'),
        ('pengangkatan_kembali', 'Pengangkatan Kembali'),
        ('perpindahan', 'Perpindahan dari Jabatan Lain'),
        ('penyesuaian', 'Inpassing/Penyesuaian'),
    )

    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    periode = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Bulan pengusulan yang digunakan untuk surat kolektif.',
    )
    kategori_pengelolaan = models.CharField(
        max_length=30,
        choices=KATEGORI_PENGELOLAAN,
        default='kenaikan',
    )
    jabatan_diusulkan = models.CharField(max_length=150, blank=True)
    formasi_tersedia = models.BooleanField(default=True)
    kinerja_dua_thn = models.ManyToManyField('dokumen.RiwayatKinerja', blank=True)
    kompetensi = models.ForeignKey('dokumen.UjiKompetensi', on_delete=models.SET_NULL, null=True)
    pendidikan = models.ForeignKey('dokumen.RiwayatPendidikan', on_delete=models.SET_NULL, null=True, blank=True)
    str_profesi = models.ForeignKey('dokumen.RiwayatProfesi', on_delete=models.SET_NULL, null=True, blank=True)
    pak = models.ForeignKey('dokumen.RiwayatPAK', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=50, default='belum', choices=STATUS)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.layanan} - {self.status})'


class LayananSIP(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    ijazah = models.ForeignKey(RiwayatPendidikan, on_delete=models.SET_NULL, null=True)
    str_profesi = models.ForeignKey(RiwayatProfesi, on_delete=models.SET_NULL, null=True)
    kecukupan_skp = models.FileField(
        upload_to='layanan/sip/kecukupan_skp/',
        validators=[validate_file_size],
        help_text='Ukuran maksimal file 2.5MB',
        blank=True
    )
    surat_permohonan_rekomendasi = models.FileField(
        upload_to='layanan/sip/rekomendasi_sip/',
        validators=[validate_file_size],
        help_text='Ukuran maksimal file 2.5MB',
        blank=True,
        verbose_name='Surat Permohonan Rekomendasi SIP yang sudah ditandatangani dan bermeterai',
    )
    surat_rekomendasi_sip = models.FileField(
        upload_to='layanan/sip/rekomendasi_sip/',
        validators=[validate_file_size],
        help_text='Ukuran maksimal file 2.5MB',
        blank=True,
        verbose_name='Surat Rekomendasi SIP yang Ditandatangani Pimpinan',
    )
    is_ktp = models.BooleanField(default=False)
    is_foto = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)

    status = models.CharField(max_length=50, default='belum', choices=STATUS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def cek_dokumen_profil(self):
        profil = getattr(self.pegawai, 'profil_user', None)

        self.is_ktp = bool(profil and profil.file_ktp)
        self.is_foto = bool(profil and profil.foto)

    def save(self, *args, **kwargs):
        self.cek_dokumen_profil()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.layanan} - {self.status})'
    
    @property
    def status_persyaratan(self):
        return {
            "ktp": self.is_ktp,
            "foto": self.is_foto,
            "ijazah": self.ijazah is not None,
            "str": self.str_profesi is not None,
            "skp": bool(self.kecukupan_skp),
        }
    
    
STATUS_PENGAJUAN_CUTI = (
    ('pengajuan', 'Diajukan'),
    ('tindaklanjut', 'Sedang diverifikasi'),
    ('disetujui', 'Disetujui'),
    ('selesai', 'Selesai'),
    ('ditolak', 'Ditolak'),
    ('dibatalkan', 'Dibatalkan'),
)


class LayananCuti(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    jenis_jabatan = models.CharField(choices=JENIS_JABATAN, max_length=25, blank=True, verbose_name='Jenis Jabatan Saat Ini')
    status = models.CharField(
        max_length=20,
        choices=STATUS_PENGAJUAN_CUTI,
        default='pengajuan',
        verbose_name='Status Pengajuan Cuti',
    )
    is_read = models.BooleanField(default=False)
    tahun = models.IntegerField(blank=True, null=True, verbose_name='Tahun Cuti')
    snapshot_saldo_cuti = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Snapshot Saldo Cuti',
        help_text='Saldo cuti pada saat pengajuan disimpan.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.layanan} - {self.status})'


AKSI_PEMUTIHAN_CUTI = (
    ('disetujui', 'Disetujui'),
    ('selesai', 'Selesai'),
    ('ditolak', 'Ditolak'),
    ('dibatalkan', 'Dibatalkan'),
)


class PemutihanCutiLog(models.Model):
    """Jejak audit perubahan massal status cuti oleh admin."""

    layanan_cuti = models.ForeignKey(
        LayananCuti,
        on_delete=models.CASCADE,
        related_name='log_pemutihan',
    )
    riwayat_cuti = models.ForeignKey(
        'dokumen.RiwayatCuti',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='log_pemutihan',
    )
    admin = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pemutihan_cuti_dilakukan',
    )
    aksi = models.CharField(max_length=20, choices=AKSI_PEMUTIHAN_CUTI)
    status_pengajuan_sebelum = models.CharField(max_length=20)
    status_pengajuan_sesudah = models.CharField(max_length=20)
    status_pelaksanaan_sebelum = models.CharField(max_length=20, blank=True)
    status_pelaksanaan_sesudah = models.CharField(max_length=20, blank=True)
    catatan = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')
        verbose_name = 'Log Pemutihan Cuti'
        verbose_name_plural = 'Log Pemutihan Cuti'

    def __str__(self):
        return (
            f'{self.layanan_cuti_id} - {self.get_aksi_display()} '
            f'oleh {self.admin_id}'
        )

KEPUTUSAN_VERIF = (
    ("belum", "Belum diputuskan"),
    ("setuju", "Disetujui"),
    ("tunda", "Ditunda"),
    ("tolak", "Ditolak"),
)   

class VerifikasiCuti(models.Model):
    layanan_cuti = models.OneToOneField(LayananCuti, on_delete=models.CASCADE)
    verifikator1 = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='verifikator1_cuti')
    persetujuan1 = models.BooleanField(null=True, blank=True)
    keputusan1 = models.CharField(max_length=10, choices=KEPUTUSAN_VERIF, default="belum")
    catatan1 = models.TextField(blank=True)
    diputuskan_pada1 = models.DateTimeField(null=True, blank=True)
    verifikator2 = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='verifikator2_cuti')
    persetujuan2 = models.BooleanField(null=True, blank=True)
    keputusan2 = models.CharField(max_length=10, choices=KEPUTUSAN_VERIF, default="belum")
    catatan2 = models.TextField(blank=True)
    diputuskan_pada2 = models.DateTimeField(null=True, blank=True)
    verifikator3 = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='verifikator3_cuti')
    persetujuan3 = models.BooleanField(null=True, blank=True)
    keputusan3 = models.CharField(max_length=10, choices=KEPUTUSAN_VERIF, default="belum")
    catatan3 = models.TextField(blank=True)
    diputuskan_pada3 = models.DateTimeField(null=True, blank=True)
    tanggal = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        persetujuan = ''
        if self.persetujuan1 and self.persetujuan2 and self.persetujuan3:
            persetujuan = '3 level'
        elif self.persetujuan1 and self.persetujuan2:
            persetujuan = '2 level'
        elif self.persetujuan1:
            persetujuan = '1 level'
        else:
            persetujuan = 'Belum ada'
        if self.layanan_cuti is not None:
            return f'{self.layanan_cuti.pegawai.full_name}-{persetujuan}'
        return f'{self.layanan_cuti}-{persetujuan}'
    

STATUS_PELIMPAHAN = (
    ("draft", "Draft"),
    ("menunggu_penerima", "Menunggu persetujuan penerima"),
    ("ditolak_penerima", "Ditolak penerima"),
    ("menunggu_atasan", "Menunggu persetujuan atasan (khusus level instalasi)"),
    ("ditolak_atasan", "Ditolak atasan"),
    ("disetujui", "Disetujui"),
)

STATUS_PERS = (
    ("belum", "Belum diputuskan"),
    ("disetujui", "Disetujui"),
    ("ditolak", "Ditolak"),
)

class PelimpahanTugas(models.Model):
    # 1 dokumen pelimpahan untuk 1 riwayat cuti
    riwayat_cuti = models.OneToOneField(
        "dokumen.RiwayatCuti",  # sesuaikan app label
        on_delete=models.CASCADE,
        related_name="pelimpahan_tugas"
    )

    pemberi_tugas = models.ForeignKey(
        "myaccount.Users", on_delete=models.CASCADE, related_name="pelimpahan_dibuat"
    )
    penerima_tugas = models.ForeignKey(
        "myaccount.Users", on_delete=models.CASCADE, related_name="pelimpahan_diterima"
    )

    deskripsi_tugas = models.TextField()
    tgl_mulai = models.DateField()
    tgl_selesai = models.DateField()

    status = models.CharField(max_length=30, choices=STATUS_PELIMPAHAN, default="draft")

    # persetujuan penerima
    persetujuan_penerima = models.CharField(max_length=20, choices=STATUS_PERS, default="belum")
    catatan_penerima = models.TextField(blank=True)

    # persetujuan atasan (khusus bila pemberi level4)
    atasan_penyetuju = models.ForeignKey(
        "myaccount.Users",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="pelimpahan_disetujui_atasan"
    )
    persetujuan_atasan = models.CharField(max_length=20, choices=STATUS_PERS, default="belum")
    catatan_atasan = models.TextField(blank=True)
    butuh_persetujuan_atasan = models.BooleanField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.tgl_mulai and self.tgl_selesai and self.tgl_mulai > self.tgl_selesai:
            raise ValidationError("Tanggal mulai tidak boleh melebihi tanggal selesai.")

    def __str__(self):
        return f"Pelimpahan {self.pemberi_tugas} -> {self.penerima_tugas}"

    # ========= aturan utama =========
    def requires_atasan_approval(self) -> bool:
        """
        - pemberi level4 (UnitInstalasi) => True (wajib persetujuan atasan level3)
        - pemberi level3+ => False
        """
        if self.butuh_persetujuan_atasan is not None:
            return self.butuh_persetujuan_atasan

        rp = (
            self.pemberi_tugas.riwayat_penempatan.filter(status=True)
            .order_by("-updated_at", "-id")
            .first()
        )
        if not rp:
            return False
        _, level = rp._penempatan_aktif
        return level == "level4"

    def is_final_approved(self) -> bool:
        """
        Final disetujui jika:
        - penerima setuju
        - jika butuh atasan: atasan setuju
        - jika tidak butuh atasan: selesai setelah penerima setuju
        """
        if self.persetujuan_penerima != "disetujui":
            return False
        if self.requires_atasan_approval():
            return self.persetujuan_atasan == "disetujui"
        return True


JENIS_PERUBAHAN_JADWAL = (
    ('langsung', 'Perubahan sebelum verifikasi'),
    ('revisi_proses', 'Revisi saat verifikasi berjalan'),
    ('perubahan_final', 'Perubahan setelah persetujuan final'),
)

STATUS_PERUBAHAN_JADWAL = (
    ('menunggu_verifikasi', 'Menunggu verifikasi perubahan'),
    ('menunggu_pelimpahan', 'Menunggu persetujuan ulang pelimpahan'),
    ('diterapkan', 'Perubahan diterapkan'),
    ('ditolak', 'Perubahan ditolak'),
    ('dibatalkan', 'Dibatalkan pemohon'),
)


class PerubahanJadwalCuti(models.Model):
    """Audit dan workflow perubahan jadwal yang diajukan oleh pemohon cuti."""

    riwayat_cuti = models.ForeignKey(
        'dokumen.RiwayatCuti',
        on_delete=models.CASCADE,
        related_name='perubahan_jadwal',
    )
    diajukan_oleh = models.ForeignKey(
        Users,
        on_delete=models.PROTECT,
        related_name='perubahan_jadwal_cuti_diajukan',
    )
    jenis_perubahan = models.CharField(max_length=20, choices=JENIS_PERUBAHAN_JADWAL)
    status = models.CharField(
        max_length=25,
        choices=STATUS_PERUBAHAN_JADWAL,
        default='menunggu_verifikasi',
    )
    tanggal_mulai_lama = models.DateField()
    tanggal_akhir_lama = models.DateField()
    lama_cuti_lama = models.PositiveSmallIntegerField()
    tanggal_mulai_baru = models.DateField()
    tanggal_akhir_baru = models.DateField()
    lama_cuti_baru = models.PositiveSmallIntegerField()
    alasan = models.TextField()

    snapshot_verifikasi = models.JSONField(default=dict, blank=True)
    snapshot_pelimpahan = models.JSONField(default=dict, blank=True)

    verifikator1 = models.ForeignKey(
        Users, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verifikator1_perubahan_jadwal_cuti',
    )
    keputusan1 = models.CharField(max_length=10, choices=KEPUTUSAN_VERIF, default='belum')
    catatan1 = models.TextField(blank=True)
    diputuskan_pada1 = models.DateTimeField(null=True, blank=True)
    verifikator2 = models.ForeignKey(
        Users, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verifikator2_perubahan_jadwal_cuti',
    )
    keputusan2 = models.CharField(max_length=10, choices=KEPUTUSAN_VERIF, default='belum')
    catatan2 = models.TextField(blank=True)
    diputuskan_pada2 = models.DateTimeField(null=True, blank=True)
    verifikator3 = models.ForeignKey(
        Users, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verifikator3_perubahan_jadwal_cuti',
    )
    keputusan3 = models.CharField(max_length=10, choices=KEPUTUSAN_VERIF, default='belum')
    catatan3 = models.TextField(blank=True)
    diputuskan_pada3 = models.DateTimeField(null=True, blank=True)

    diterapkan_pada = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at', '-id')

    def clean(self):
        super().clean()
        if self.tanggal_mulai_baru and self.tanggal_akhir_baru:
            if self.tanggal_akhir_baru < self.tanggal_mulai_baru:
                raise ValidationError('Tanggal akhir baru tidak boleh sebelum tanggal mulai baru.')
            jumlah = (self.tanggal_akhir_baru - self.tanggal_mulai_baru).days + 1
            if self.lama_cuti_baru and self.lama_cuti_baru != jumlah:
                raise ValidationError('Jumlah hari perubahan tidak sesuai dengan rentang tanggal baru.')

    @property
    def is_active(self):
        return self.status in ('menunggu_verifikasi', 'menunggu_pelimpahan')

    def __str__(self):
        return f'Perubahan jadwal cuti #{self.riwayat_cuti_id} ({self.get_status_display()})'


STATUS_DIKLAT = (
    ('usulan', 'usulan'),
    ('proses', 'proses'),
    ('tidak ditindaklanjut', 'tidak ditindaklanjut'),
    ('tindaklanjut', 'tindaklanjut'),
    ('selesai', 'selesai')
)


class SumberPembiayaan(models.Model):
    sumber = models.CharField(max_length=25)
    slug = models.SlugField(blank=True)

    def __str__(self):
        return self.sumber

@receiver(pre_save, sender=SumberPembiayaan)
def slugify_sumber(sender, instance, *args, **kwargs):
    instance.slug = slugify(instance.sumber)


class LayananUsulanDiklat(models.Model):
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    justifikasi = HTMLField(blank=True)
    brosur = models.FileField(upload_to='diklat/brosur/', blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    tor = models.FileField(upload_to='diklat/tor/', blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    spt = models.FileField(upload_to='diklat/spt/', blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    pembiayaan = models.ForeignKey(SumberPembiayaan, on_delete=models.SET_NULL, null=True, blank=True)
    biaya = models.FloatField(blank=True, null=True, verbose_name='Jumlah Biaya')
    bukti_lunas = models.FileField(upload_to='diklat/kwitansi/', blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    catatan_sdm = HTMLField(blank=True)
    status = models.CharField(max_length=50, default='usulan', choices=STATUS_DIKLAT)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.layanan} ({self.riwayatdiklat_set.first()}-{self.status})'
    

class VerifikasiDiklat(models.Model):
    layanan_diklat = models.OneToOneField(LayananUsulanDiklat, on_delete=models.CASCADE)
    verifikator1 = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='verifikator1_diklat')
    persetujuan1 = models.BooleanField(default=False)
    catatan1 = models.TextField(blank=True)
    verifikator2 = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='verifikator2_diklat')
    persetujuan2 = models.BooleanField(default=False)
    catatan2 = models.TextField(blank=True)
    verifikator3 = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='verifikator3_diklat')
    persetujuan3 = models.BooleanField(default=False)
    catatan3 = models.TextField(blank=True)
    tanggal = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        persetujuan = ''
        if self.persetujuan1 and self.persetujuan2 and self.persetujuan3:
            persetujuan = '3 level'
        elif self.persetujuan1 and self.persetujuan2:
            persetujuan = '2 level'
        elif self.persetujuan1:
            persetujuan = '1 level'
        else:
            persetujuan = 'Belum ada'
        if self.layanan_diklat is not None:
            return f'{self.layanan_diklat.riwayatdiklat_set.first()}-{persetujuan}'
        return f'{self.layanan_diklat}-{persetujuan}'
    

STATUS_INOVASI = (
    ('usulan', 'usulan'),
    ('proses', 'proses'),
    ('tidak ditindaklanjut', 'tidak ditindaklanjut'),
    ('tindaklanjut', 'tindaklanjut'),
    ('selesai', 'selesai')
)
class LayananUsulanInovasi(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    inovasi = models.ForeignKey('dokumen.RiwayatInovasi', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='usulan', choices=STATUS_INOVASI)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.layanan:
            return f'{self.pegawai.full_name} - {self.status}'
        else:
            return f'{self.layanan} - {self.status}'
