from django.db import models
from layanan.models import JenisLayanan
from dokumen.models import DokumenSDM
from myaccount.models import Users

# Create your models here.

STATUS = (
    ('Laporan', 'Laporan'),
    ('Tindaklanjut', 'Tindaklanjut'),
    ('Selesai', 'Selesai')
)

class LaporanMasalah(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    deskripsi = models.TextField(help_text='Tuliskan terjadi error di menu apa? kapan terjadi error, apakah saat baru buka menu atau setelah mengirimkan data? atau permasalahan lainnya silahkan deskripsikan.')#kapan masalah terjadi apakah rutin pada saat menjalankan aplikasi atau, frekuensi terjadi masalah
    gambar = models.FileField(upload_to='lapor/')
    status = models.CharField(max_length=15, blank=True, choices=STATUS)
    keterangan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pegawai.full_name

class Saran(models.Model):
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    saran = models.TextField(help_text='Silahkan tuliskan saran anda disini')
    tanggapan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pegawai.full_name