from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.template.defaultfilters import slugify
from jenissdm.models import ListKompetensi
from myaccount.models import Users

# Create your models here.

class InstansiDaerah(models.Model):
    pimpinan = models.CharField(max_length=100, blank=True)
    nama_pimpinan = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)
    instansi = models.CharField(max_length=100)

    def __str__(self):
        return self.instansi
    

class SatuanKerjaInduk(models.Model):
    pimpinan = models.CharField(max_length=100, blank=True)
    nama_pimpinan = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)
    instansi_daerah = models.ForeignKey('InstansiDaerah', on_delete=models.CASCADE)
    satuan_kerja = models.CharField(max_length=100)

    def __str__(self):
        return self.satuan_kerja
    

class UnitOrganisasi(models.Model):
    pimpinan = models.CharField(max_length=100, blank=True)
    nama_pimpinan = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)
    satker_induk = models.ForeignKey('SatuanKerjaInduk', on_delete=models.CASCADE)
    unor = models.CharField(max_length=100)
    
    def __str__(self):
        return self.unor
    
    
class StandarSDM(models.Model):
    unor = models.ForeignKey('UnitOrganisasi', on_delete=models.CASCADE)
    jenis_sdm = models.ForeignKey('jenissdm.JenisSDM', on_delete=models.CASCADE)
    jumlah = models.SmallIntegerField(null=True)
    status_wajib = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.jenis_sdm}-{self.jumlah}'
    

class Bidang(models.Model):
    pimpinan = models.CharField(max_length=100, blank=True)
    nama_pimpinan = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)
    unor = models.ForeignKey('UnitOrganisasi', on_delete=models.CASCADE)
    bidang = models.CharField(max_length=100)
    
    def __str__(self):
        return self.bidang


class SubBidang(models.Model):
    pimpinan = models.CharField(max_length=100, blank=True)
    nama_pimpinan = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)
    bidang = models.ForeignKey('Bidang', on_delete=models.CASCADE)
    sub_bidang = models.CharField(max_length=100)
    
    def __str__(self):
        return self.sub_bidang
    
STATUS = (
    ('kurang', 'kurang'),
    ('bagus', 'bagus'),
    ('mantap', 'mantap')
)
class UnitInstalasi(models.Model):
    pimpinan = models.CharField(max_length=100, blank=True)
    nama_pimpinan = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)
    sub_bidang = models.ForeignKey('SubBidang', on_delete=models.CASCADE)
    instalasi = models.CharField(max_length=50)
    status = models.CharField(max_length=10, blank=True, choices=STATUS)
    slug = models.SlugField(blank=True)

    def __str__(self):
        return f'{self.sub_bidang} - {self.instalasi}'
    
@receiver(pre_save, sender=UnitInstalasi)
def slugify_kategori_informasi(sender, instance, *args, **kwargs):
    instance.slug = slugify(instance.instalasi)


class StandarInstalasi(models.Model):
    instalasi = models.ForeignKey('UnitInstalasi', on_delete=models.CASCADE)
    jenis_sdm = models.ForeignKey('jenissdm.JenisSDM', on_delete=models.CASCADE)
    kompetensi_wajib = models.ManyToManyField(ListKompetensi, blank=True, related_name='kompetensi_wajib_sdm')
    kompetensi_wajib_parsial = models.ManyToManyField(ListKompetensi, blank=True, related_name='kompetensi_wajib_parsial_sdm')
    kompetensi_pendukung = models.ManyToManyField(ListKompetensi, blank=True, related_name='kompetensi_pendukung_sdm')

    def __str__(self):
        return self.instalasi.instalasi
    

#Tabel tengah
# class KompetensiWajibSDMPerinstalasi(models.Model):
#     kompetensi = models.ForeignKey(ListKompetensi, on_delete=models.CASCADE)
#     standar_instalasi = models.ForeignKey('StandarInstalasi', on_delete=models.CASCADE)
    

#tabel tengah
# class KompetensiPendukungSDMPerinstalasi(models.Model):
#     kompetensi = models.ForeignKey('jenissdm.ListKompetensi', on_delete=models.CASCADE)
#     standar_instalasi = models.ForeignKey('StandarInstalasi', on_delete=models.CASCADE)