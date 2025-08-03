from django.contrib import admin
from .models import InformasiSDM, VideoYoutube, KategoriInformasi, KategoriVideo, VideoComment, ReVideoComment, NasehatdanHadist

# Register your models here.
admin.site.register(KategoriInformasi)
admin.site.register(KategoriVideo)
admin.site.register(InformasiSDM)
admin.site.register(VideoYoutube)
admin.site.register(VideoComment)
admin.site.register(ReVideoComment)
admin.site.register(NasehatdanHadist)