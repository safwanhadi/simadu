from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.template.defaultfilters import slugify
from hitcount.models import HitCount, HitCountMixin
from django.contrib.contenttypes.fields import GenericRelation
from datetime import datetime
from pytz import timezone as tz
from tinymce.models import HTMLField
from urllib.parse import parse_qs, urlparse
# Create your models here.


class KategoriInformasi(models.Model):
    kategori = models.CharField(max_length=50)
    slug = models.SlugField(blank=True)

    def __str__(self):
        return self.kategori

@receiver(pre_save, sender=KategoriInformasi)
def slugify_kategori_informasi(sender, instance, *args, **kwargs):
    instance.slug = slugify(instance.kategori)

STATUS = (
    ('draft', 'draft'),
    ('publish', 'publish')
)

class InformasiSDM(models.Model, HitCountMixin):
    kategori = models.ForeignKey(KategoriInformasi, on_delete=models.CASCADE)
    author = models.ForeignKey('myaccount.Users', on_delete=models.SET_NULL, null=True)
    judul = models.CharField(max_length=250)
    isi = HTMLField(blank=True)
    gambar = models.ImageField(upload_to='informasi/gambar/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft') 
    headline = models.BooleanField(default=False)
    active = models.BooleanField(default=True)#menentukan apakah dokumen dapat diakses oleh user atau hanya sebagai arsip
    pdf_file = models.FileField(upload_to='informasi/file/', blank=True, null=True)
    slug = models.SlugField(blank=True, max_length=250) #slug untuk judul
    hit_count_generic = GenericRelation(HitCount, object_id_field='object_pk', related_query_name='hit_count_generic_relation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.judul
    
    
@receiver(pre_save, sender=InformasiSDM)
def slugify_informasi(sender, instance, *args, **kwargs):
    instance.slug = slugify(instance.judul)


class KategoriVideo(models.Model):
    kategori = models.CharField(max_length=50)
    slug = models.SlugField(blank=True)

    def __str__(self):
        return self.kategori

@receiver(pre_save, sender=KategoriVideo)
def slugify_kategori_video(sender, instance, *args, **kwargs):
    instance.slug = slugify(instance.kategori)


class VideoYoutube(models.Model):
    kategori = models.ForeignKey(KategoriVideo, on_delete=models.CASCADE)
    author = models.ForeignKey('myaccount.Users', on_delete=models.SET_NULL, null=True)
    judul_video = models.CharField(max_length=250, blank=True)
    id_video = models.CharField(max_length=200, unique=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    headline = models.BooleanField(default=False)
    slug = models.SlugField(blank=True, max_length=250) #slug untuk judul
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.judul_video

    @property
    def youtube_id(self):
        """Return a usable YouTube ID for both legacy URLs and plain IDs."""
        value = (self.id_video or '').strip()
        if not value:
            return ''

        parsed = urlparse(value if '://' in value else f'https://{value}')
        hostname = (parsed.hostname or '').lower()
        if hostname in {'youtu.be', 'www.youtu.be'}:
            return parsed.path.strip('/').split('/')[0]
        if hostname.endswith('youtube.com'):
            if parsed.path == '/watch':
                return parse_qs(parsed.query).get('v', [value])[0]
            for prefix in ('/embed/', '/shorts/', '/live/'):
                if parsed.path.startswith(prefix):
                    return parsed.path[len(prefix):].split('/')[0]
        return value

    
@receiver(pre_save, sender=VideoYoutube)
def slugify_judul_video(sender, instance, *args, **kwargs):
    instance.slug = slugify(instance.judul_video)


class VideoComment(models.Model):
    video = models.ForeignKey(VideoYoutube, on_delete=models.CASCADE)
    author = models.ForeignKey('myaccount.Users', on_delete=models.SET_NULL, null=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.comment


class ReVideoComment(models.Model):
    comment = models.ForeignKey(VideoComment, on_delete=models.CASCADE)
    author = models.ForeignKey('myaccount.Users', on_delete=models.SET_NULL, null=True)
    recomment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.recomment


class NasehatdanHadist(models.Model):
    hadist = models.TextField()
    author_perawi = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.hadist
