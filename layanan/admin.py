from django.contrib import admin

from .models import (
    JenisLayanan, 
    LayananCuti, 
    LayananGajiBerkala, 
    SumberPembiayaan, 
    LayananUsulanDiklat, 
    LayananUsulanInovasi, 
    VerifikasiCuti,
    PelimpahanTugas,
    VerifikasiDiklat
)

# Register your models here.

admin.site.register(JenisLayanan)
admin.site.register(LayananCuti)
admin.site.register(LayananGajiBerkala)
admin.site.register(SumberPembiayaan)
admin.site.register(LayananUsulanDiklat)
admin.site.register(LayananUsulanInovasi)
admin.site.register(VerifikasiCuti)
admin.site.register(PelimpahanTugas)
admin.site.register(VerifikasiDiklat)
