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
    JENIS_JABATAN
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
    url = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.nama

STATUS = (
    ('belum', 'belum'),
    ('pengajuan', 'pengajuan'),
    ('proses', 'proses'),
    ('selesai', 'selesai')
)

# class LayananTubel(models.Model):
#     pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
#     layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
#     status = models.CharField(max_length=50, default='belum', choices=STATUS)


# class LayananPenyesuaianPendidikan(models.Model):
#     pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
#     layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
#     status = models.CharField(max_length=50, default='belum', choices=STATUS)


class LayananPengakuanGelar(models.Model):
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


class LayananPenerbitanPAK(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    kinerja = models.ForeignKey(RiwayatKinerja, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=50, default='belum', choices=STATUS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.layanan} - {self.status})'


class LayananKenaikanPangkat(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    jabatan = models.ForeignKey(RiwayatJabatan, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=50, default='belum', choices=STATUS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.layanan} - {self.status})'


class KenaikanPangkatJabFungsional(models.Model):
    jenis_kp = models.ForeignKey('LayananKenaikanPangkat', on_delete=models.CASCADE)
    sk_kp_terakhir = models.ForeignKey(RiwayatPanggol, on_delete=models.SET_NULL, null=True)
    kinerja_dua_thn = models.ManyToManyField(RiwayatKinerja, through='KinerjaKenaikanPangkatJafung', blank=True)
    pak = models.ForeignKey(RiwayatPAK, on_delete=models.SET_NULL, null=True)
    pendidikan = models.ForeignKey(RiwayatPendidikan, on_delete=models.SET_NULL, null=True)
    pengangkatan = models.ForeignKey(RiwayatPengangkatan, on_delete=models.SET_NULL, null=True)
    mutasi = models.ForeignKey(RiwayatBekerja, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.jenis_kp


#tabeltengah
class KinerjaKenaikanPangkatJafung(models.Model):
    kenaikan_pangkat = models.ForeignKey(KenaikanPangkatJabFungsional, on_delete=models.CASCADE)
    kinerja = models.ForeignKey(RiwayatKinerja, on_delete=models.SET_NULL, null=True)


class KenaikanPangkatJabStruktural(models.Model):
    jenis_kp = models.ForeignKey('LayananKenaikanPangkat', on_delete=models.CASCADE)
    sk_kp_terakhir = models.ForeignKey(RiwayatPanggol, on_delete=models.SET_NULL, null=True)
    kinerja_dua_thn = models.ManyToManyField(RiwayatKinerja, through='KinerjaKenaikanPangkatStruktural')
    diklat = models.ForeignKey(RiwayatDiklat, on_delete=models.SET_NULL, null=True)
    pendidikan = models.ForeignKey(RiwayatPendidikan, on_delete=models.SET_NULL, null=True)
    pengangkatan = models.ForeignKey(RiwayatPengangkatan, on_delete=models.SET_NULL, null=True)
    mutasi = models.ForeignKey(RiwayatBekerja, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.jenis_kp


#tabeltengah
class KinerjaKenaikanPangkatStruktural(models.Model):
    kenaikan_pangkat = models.ForeignKey(KenaikanPangkatJabStruktural, on_delete=models.CASCADE)
    kinerja = models.ForeignKey(RiwayatKinerja, on_delete=models.SET_NULL, null=True)


class KenaikanPangkatJabPelaksana(models.Model):
    jenis_kp = models.ForeignKey('LayananKenaikanPangkat', on_delete=models.CASCADE)
    sk_kp_terakhir = models.ForeignKey(RiwayatPanggol, on_delete=models.SET_NULL, null=True)
    kinerja_dua_thn = models.ManyToManyField(RiwayatKinerja, through='KinerjaKenaikanPangkatJabPelaksana')
    pendidikan = models.ForeignKey(RiwayatPendidikan, on_delete=models.SET_NULL, null=True)
    pengangkatan = models.ForeignKey(RiwayatPengangkatan, on_delete=models.SET_NULL, null=True)
    mutasi = models.ForeignKey(RiwayatBekerja, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.jenis_kp


#tabeltengah
class KinerjaKenaikanPangkatJabPelaksana(models.Model):
    kenaikan_pangkat = models.ForeignKey(KenaikanPangkatJabPelaksana, on_delete=models.CASCADE)
    kinerja = models.ForeignKey(RiwayatKinerja, on_delete=models.SET_NULL, null=True)


class LayananKenaikanJabatan(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    jabatan = models.ForeignKey(RiwayatJabatan, on_delete=models.SET_NULL, null=True)
    kinerja_dua_thn = models.ManyToManyField(RiwayatKinerja, through='KinerjaKenaikanJabFung')
    kompetensi = models.ForeignKey(UjiKompetensi, on_delete=models.SET_NULL, null=True)
    pak = models.ForeignKey(RiwayatPAK, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=50, default='belum', choices=STATUS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.layanan} - {self.status})'
    
    
#tabeltengah
class KinerjaKenaikanJabFung(models.Model):
    kenaikan_jabatan = models.ForeignKey(LayananKenaikanJabatan, on_delete=models.CASCADE)
    kinerja = models.ForeignKey(RiwayatKinerja, on_delete=models.SET_NULL, null=True)


# class LayananSTR(models.Model):
#     pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
#     layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
#     status = models.CharField(max_length=50, default='belum', choices=STATUS)

#     def __str__(self):
#         return f'{self.layanan} - {self.status}'

class LayananSIP(models.Model):
    # ijazah, ktp, srt sehat, rekom profesi, rekom faskes, str, surat pernyataan praktik, pasfoto
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    ijazah = models.ForeignKey(RiwayatPendidikan, on_delete=models.SET_NULL, null=True) 
    str_profesi = models.ForeignKey(RiwayatProfesi, on_delete=models.SET_NULL, null=True)
    rekom_profesi = models.FileField(upload_to='layanan/sip/rekom_pofesi/', validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    rekom_faskes = models.FileField(upload_to='layanan/sip/rekom_faskes/', validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    pernyataan_praktik = models.FileField(upload_to='layanan/sip/praktik/', validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    ket_sehat = models.FileField(upload_to='layanan/sip/sehat/', validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    pasfoto = models.FileField(upload_to='layanan/sip/foto/', validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    status = models.CharField(max_length=50, default='belum', choices=STATUS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.layanan} - {self.status})'


STATUS_CUTI = (
    ('draft', 'draft'),
    ('pengajuan', 'pengajuan'),
    ('tidak ditindaklanjut', 'tidak ditindaklanjut'),
    ('tindaklanjut', 'tindaklanjut'),
    ('selesai', 'selesai')
)


class LayananCuti(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    layanan = models.ForeignKey('JenisLayanan', on_delete=models.SET_NULL, null=True)
    jenis_jabatan = models.CharField(choices=JENIS_JABATAN, max_length=25, blank=True, verbose_name='Jenis Jabatan Saat Ini')
    cuti_tunda = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CUTI, default='draft', verbose_name='Status Cuti')
    is_read = models.BooleanField(default=False)
    tahun = models.IntegerField(blank=True, null=True, verbose_name='Tahun Cuti')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai.full_name} ({self.layanan} - {self.status})'
    

class VerifikasiCuti(models.Model):
    layanan_cuti = models.OneToOneField(LayananCuti, on_delete=models.CASCADE)
    verifikator1 = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='verifikator1_cuti')
    persetujuan1 = models.BooleanField(default=False)
    catatan1 = models.TextField(blank=True)
    verifikator2 = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='verifikator2_cuti')
    persetujuan2 = models.BooleanField(default=False)
    catatan2 = models.TextField(blank=True)
    verifikator3 = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='verifikator3_cuti')
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
        if self.layanan_cuti is not None:
            return f'{self.layanan_cuti.pegawai.full_name}-{persetujuan}'
        return f'{self.layanan_cuti}-{persetujuan}'
    

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
