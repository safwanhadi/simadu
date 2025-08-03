from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.template.defaultfilters import slugify

# Create your models here.    
    
class ProfesiSDM(models.Model):
    profesi = models.CharField(max_length=50)

    def __str__(self):
        return self.profesi


KATEGORISDM=(
    ('Nakes', 'Nakes'),
    ('Non Nakes', 'Non Nakes')
)

class JenisSDM(models.Model):
    profesi = models.ForeignKey(ProfesiSDM, on_delete=models.CASCADE, blank=True, null=True)
    kategori_sdm = models.CharField(max_length=25, blank=True, choices=KATEGORISDM)
    jenis_sdm = models.CharField(max_length=50)
    slug = models.SlugField(max_length=100, blank=True)
    warna_card = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return self.jenis_sdm
    
@receiver(pre_save, sender=JenisSDM)
def slugify_jenissdm(sender, instance, *args, **kwargs):
    instance.slug = slugify(instance.jenis_sdm)


SIFAT = (
    ("Wajib", "Wajib"),
    ("Pendukung", "Pendukung")
)

class ListKompetensi(models.Model):
    jenis_sdm = models.ForeignKey(JenisSDM, on_delete=models.SET_NULL, null=True, blank=True)
    kompetensi = models.CharField(max_length=200)
    # sifat = models.CharField(max_length=10, blank=True, choices=SIFAT)

    def __str__(self):
        return f'{self.kompetensi} - {self.jenis_sdm}'