from datetime import date

from django.db import models
from django.core.exceptions import ValidationError
from django.db import transaction
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


class PejabatStruktur(models.Model):
    """Riwayat pejabat pada satu simpul struktur organisasi.

    Field ``nama_pimpinan`` pada model struktur tetap dipertahankan sebagai
    cache kompatibilitas. Sumber kebenaran pejabat dan masa jabatannya ada di
    model ini, sehingga pergantian pejabat tidak mengubah riwayat pengajuan.
    """

    TARGET_FIELDS = (
        'instansi_daerah',
        'satuan_kerja_induk',
        'unit_organisasi',
        'bidang',
        'sub_bidang',
        'unit_instalasi',
    )
    DEFINITIF = 'definitif'
    PLT = 'plt'
    PLH = 'plh'
    JENIS_PENUGASAN = (
        (DEFINITIF, 'Definitif'),
        (PLT, 'Pelaksana Tugas (Plt.)'),
        (PLH, 'Pelaksana Harian (Plh.)'),
    )

    instansi_daerah = models.ForeignKey(
        InstansiDaerah, on_delete=models.CASCADE, null=True, blank=True,
        related_name='riwayat_pejabat',
    )
    satuan_kerja_induk = models.ForeignKey(
        SatuanKerjaInduk, on_delete=models.CASCADE, null=True, blank=True,
        related_name='riwayat_pejabat',
    )
    unit_organisasi = models.ForeignKey(
        UnitOrganisasi, on_delete=models.CASCADE, null=True, blank=True,
        related_name='riwayat_pejabat',
    )
    bidang = models.ForeignKey(
        Bidang, on_delete=models.CASCADE, null=True, blank=True,
        related_name='riwayat_pejabat',
    )
    sub_bidang = models.ForeignKey(
        SubBidang, on_delete=models.CASCADE, null=True, blank=True,
        related_name='riwayat_pejabat',
    )
    unit_instalasi = models.ForeignKey(
        UnitInstalasi, on_delete=models.CASCADE, null=True, blank=True,
        related_name='riwayat_pejabat',
    )
    pejabat = models.ForeignKey(
        Users,
        on_delete=models.PROTECT,
        related_name='riwayat_jabatan_struktur',
    )
    jenis_penugasan = models.CharField(
        max_length=12,
        choices=JENIS_PENUGASAN,
        default=DEFINITIF,
    )
    nama_jabatan = models.CharField(max_length=100, blank=True)
    tanggal_mulai = models.DateField(default=date.today)
    tanggal_selesai = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    # TRUE hanya untuk masa jabatan aktif; NULL untuk seluruh riwayat lama.
    # Pola ini membuat unique constraint bekerja juga di MySQL/MariaDB yang
    # tidak mendukung conditional unique constraint.
    active_slot = models.BooleanField(null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-is_active', '-tanggal_mulai', '-id')
        verbose_name = 'Riwayat pejabat struktur'
        verbose_name_plural = 'Riwayat pejabat struktur'
        constraints = [
            models.UniqueConstraint(
                fields=('instansi_daerah', 'active_slot'),
                name='uniq_pejabat_aktif_instansi',
            ),
            models.UniqueConstraint(
                fields=('satuan_kerja_induk', 'active_slot'),
                name='uniq_pejabat_aktif_satker',
            ),
            models.UniqueConstraint(
                fields=('unit_organisasi', 'active_slot'),
                name='uniq_pejabat_aktif_unor',
            ),
            models.UniqueConstraint(
                fields=('bidang', 'active_slot'),
                name='uniq_pejabat_aktif_bidang',
            ),
            models.UniqueConstraint(
                fields=('sub_bidang', 'active_slot'),
                name='uniq_pejabat_aktif_subbidang',
            ),
            models.UniqueConstraint(
                fields=('unit_instalasi', 'active_slot'),
                name='uniq_pejabat_aktif_instalasi',
            ),
        ]

    @property
    def struktur_object(self):
        for field_name in self.TARGET_FIELDS:
            target = getattr(self, field_name, None)
            if target is not None:
                return target
        return None

    @property
    def target_field_name(self):
        for field_name in self.TARGET_FIELDS:
            if getattr(self, f'{field_name}_id', None) is not None:
                return field_name
        return None

    def clean(self):
        super().clean()
        selected = [
            field_name for field_name in self.TARGET_FIELDS
            if getattr(self, f'{field_name}_id', None) is not None
        ]
        if len(selected) != 1:
            raise ValidationError(
                'Pilih tepat satu struktur tempat pejabat bertugas.'
            )
        if self.tanggal_selesai and self.tanggal_selesai < self.tanggal_mulai:
            raise ValidationError({
                'tanggal_selesai': 'Tanggal selesai tidak boleh sebelum tanggal mulai.'
            })
        if self.is_active and self.tanggal_selesai:
            raise ValidationError({
                'tanggal_selesai': 'Pejabat aktif tidak boleh memiliki tanggal selesai.'
            })
        if self.is_active and self.pejabat_id and not self.pejabat.is_active:
            raise ValidationError({
                'pejabat': 'Akun pejabat harus berstatus aktif.'
            })

    def save(self, *args, **kwargs):
        self.active_slot = True if self.is_active else None
        if not self.is_active and self.tanggal_selesai is None:
            self.tanggal_selesai = date.today()
        # Constraint "satu pejabat aktif" divalidasi setelah pejabat lama
        # dinonaktifkan di dalam transaksi dan lock yang sama.
        self.full_clean(validate_constraints=False)
        field_name = self.target_field_name
        target = self.struktur_object
        with transaction.atomic():
            if self.is_active:
                # Kunci simpul struktur agar dua pejabat tidak aktif bersamaan.
                type(target).objects.select_for_update().get(pk=target.pk)
                previous = type(self).objects.filter(
                    **{f'{field_name}_id': target.pk, 'is_active': True}
                ).exclude(pk=self.pk)
                previous.filter(tanggal_selesai__isnull=True).update(
                    tanggal_selesai=self.tanggal_mulai,
                )
                previous.update(is_active=False, active_slot=None)
            super().save(*args, **kwargs)
            if self.is_active:
                cache_values = {'nama_pimpinan_id': self.pejabat_id}
                if self.nama_jabatan:
                    cache_values['pimpinan'] = self.nama_jabatan
                type(target).objects.filter(pk=target.pk).update(**cache_values)
            elif not type(self).objects.filter(
                **{f'{field_name}_id': target.pk, 'is_active': True}
            ).exists():
                type(target).objects.filter(
                    pk=target.pk,
                    nama_pimpinan_id=self.pejabat_id,
                ).update(nama_pimpinan_id=None)

    def __str__(self):
        status = 'aktif' if self.is_active else 'selesai'
        return f'{self.pejabat} - {self.struktur_object} ({status})'
    
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
