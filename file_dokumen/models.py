from django.db import models

# Create your models here.

class TextSPTDiklat(models.Model):
    diklat = models.ForeignKey('layanan.LayananUsulanDiklat', on_delete=models.CASCADE)
    dasar_pelaksanaan = models.TextField(blank=True)
    tujuan_pelaksanaan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.diklat)