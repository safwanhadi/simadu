from datetime import date
import os

from django.db import models
from django.contrib.auth.models import PermissionsMixin
from django.dispatch import receiver
from django.urls import reverse
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db.models.signals import post_save
from PIL import Image, UnidentifiedImageError
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .roles import (
    ADMIN_AKUN,
    ADMIN_DASHBOARD,
    ADMIN_DISIPLIN,
    ADMIN_DOKUMEN,
    ADMIN_GROUPS,
    ADMIN_INFORMASI,
    ADMIN_LAPORAN,
    ADMIN_LAYANAN_BERKALA,
    ADMIN_LAYANAN_PANGKAT,
    ADMIN_LAYANAN_JABATAN,
    ADMIN_LAYANAN_CUTI,
    ADMIN_LAYANAN_DIKLAT,
    ADMIN_LAYANAN_INOVASI,
    ADMIN_LAYANAN_SIP,
    ADMIN_SSO,
)

def validate_file_size(value):
    try:
        filesize = value.size
    except (FileNotFoundError, OSError):
        # Referensi file lama dapat tetap tersimpan walau fisiknya sudah tidak
        # tersedia. Kondisi ini tidak boleh menghalangi pembaruan data profil.
        return
    if filesize > 2621440:  # 2.5MB limit
        raise ValidationError(_("Ukuran maksimal file 2.5 MB"))



##################### MODIFICATION OF DJANGO USER MODEL #############################
################## THIS APP USING EMAIL BASE REGISTRATION ###########################


class MyUserManager(BaseUserManager):

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users must have an email')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        return self._create_user(email, password, first_name=first_name, last_name=last_name, **extra_fields)

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, first_name=first_name, last_name=last_name, **extra_fields)


class Users(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        verbose_name='email', max_length=255, unique=True)
    first_name = models.CharField(
        verbose_name='first name', max_length=30, null=True, blank=True)
    last_name = models.CharField(
        verbose_name='last name', max_length=150, null=True, blank=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(verbose_name='staff', default=False)
    is_active = models.BooleanField(verbose_name='active', default=True)
    is_guest = models.BooleanField(verbose_name='tamu', default=False)
    is_user = models.BooleanField(verbose_name='officer', default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = MyUserManager()

    def __str__(self):
        if self.last_name is not None:
            return f'{self.first_name}_{self.last_name}'
        else:
            return f'{self.first_name}'

    def has_admin_role(self, *group_names):
        """Superuser adalah root; admin operasional ditentukan oleh grup."""
        if not self.is_active:
            return False
        if self.is_superuser:
            return True

        cached_groups = getattr(self, '_admin_group_names_cache', None)
        if cached_groups is None:
            cached_groups = set(self.groups.values_list('name', flat=True))
            self._admin_group_names_cache = cached_groups
        return bool(cached_groups.intersection(group_names))

    @property
    def is_app_admin(self):
        return self.has_admin_role(*ADMIN_GROUPS)

    @property
    def is_dashboard_admin(self):
        return self.has_admin_role(ADMIN_DASHBOARD)

    @property
    def is_dokumen_admin(self):
        return self.has_admin_role(ADMIN_DOKUMEN)

    @property
    def has_dokumen_admin_group(self):
        return self.is_superuser or any(
            group.name == ADMIN_DOKUMEN for group in self.groups.all()
        )

    @property
    def is_cuti_admin(self):
        return self.has_admin_role(ADMIN_LAYANAN_CUTI)

    @property
    def is_berkala_admin(self):
        return self.has_admin_role(ADMIN_LAYANAN_BERKALA)

    @property
    def is_pangkat_admin(self):
        return self.has_admin_role(ADMIN_LAYANAN_PANGKAT)

    @property
    def is_jabatan_admin(self):
        return self.has_admin_role(ADMIN_LAYANAN_JABATAN)

    @property
    def is_diklat_admin(self):
        return self.has_admin_role(ADMIN_LAYANAN_DIKLAT)

    @property
    def is_inovasi_admin(self):
        return self.has_admin_role(ADMIN_LAYANAN_INOVASI)

    @property
    def is_sip_admin(self):
        return self.has_admin_role(ADMIN_LAYANAN_SIP)

    @property
    def is_disiplin_admin(self):
        return self.has_admin_role(ADMIN_DISIPLIN)

    @property
    def is_informasi_admin(self):
        return self.has_admin_role(ADMIN_INFORMASI)

    @property
    def is_laporan_admin(self):
        return self.has_admin_role(ADMIN_LAPORAN)

    @property
    def is_akun_admin(self):
        return self.has_admin_role(ADMIN_AKUN)

    @property
    def is_sso_admin(self):
        return self.has_admin_role(ADMIN_SSO)
    
    @property
    def full_name(self):
        if self.last_name is not None:
            return f'{self.first_name} {self.last_name}'
        else:
            return f'{self.first_name}'   

    @property
    def full_name_2(self):
        gelar_depan = f'{self.profil_user.gelar_depan if self is not None and hasattr(self, "profil_user") else ""}'
        gelar_belakang =f'{self.profil_user.gelar_belakang if self is not None and hasattr(self, "profil_user") else ""}'
        if self.last_name is not None:
            if gelar_depan == '-' and gelar_belakang == '-':
                return f'{self.first_name} {self.last_name}'
            elif gelar_depan == '-':
                return f'{self.first_name} {self.last_name} {gelar_belakang}'
            elif gelar_belakang == '-':
                return f'{gelar_depan} {self.first_name} {self.last_name}'
            return f'{gelar_depan} {self.first_name} {self.last_name} {gelar_belakang}'
        else:
            if gelar_depan == '-' and gelar_belakang == '-':
                return f'{self.first_name}'
            elif gelar_depan == '-':
                return f'{self.first_name} {gelar_belakang}'
            elif gelar_belakang == '-':
                return f'{gelar_depan} {self.first_name}'
            return f'{gelar_depan} {self.first_name} {gelar_belakang}'        

class Gender(models.Model):
    jenis_kelamin = models.CharField(max_length=15)

    def __str__(self):
        return self.jenis_kelamin

PENDIDIKAN = (
    ('SD', 'SD'),
    ('SLTP', 'SLTP'),
    ('SLTA', 'SLTA'),
    ('DI', 'DI'),
    ('DII', 'DII'),
    ('DIII', 'DIII'),
    ('DIIIK', 'DIII Kesehatan'),
    ('DIV', 'DIV'),
    ('DIVK', 'DIV Kesehatan'),
    ('S1', 'S1'),
    ('S1K', 'S1 Kesehatan'),
    ('S1P/DIVP', 'S1 Profesi/DIV Profesi'),
    ('S2', 'S2'),
    ('S2K', 'S2 Kesehatan'),
    ('S3', 'S3'),
    ('SPES', 'Spesialis Dokter/Dokter Gigi'),
    ('SUBSPES', 'Sub Spesialis Dokter/Dokter Gigi'),
)

STATUSPERNIKAHAN = (
    ('Belum Menikah', 'Belum Menikah'),
    ('Menikah', 'Menikah'),
    ('Duda', 'Duda'),
    ('Janda', 'Janda')
)

class ProfilSDM(models.Model):
    user = models.OneToOneField(
        Users, on_delete=models.CASCADE, primary_key=True, related_name="profil_user")
    no_hp = models.CharField(max_length=20, verbose_name='No HP/Telp.')
    # jk = models.CharField(max_length=1, blank=True)
    gender = models.ForeignKey('Gender', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Jenis Kelamin')
    tmp_lahir = models.CharField(max_length=100, blank=True, verbose_name='Tempat Lahir')
    tgl_lahir = models.DateField(blank=True, null=True, verbose_name='Tanggal Lahir')
    nm_ibu = models.CharField(max_length=40, blank=True, verbose_name='Nama Ibu')
    alamat = models.CharField(max_length=200, blank=True)
    gol_darah = models.CharField(max_length=2, blank=True)
    email_pribadi = models.EmailField()
    pendidikan = models.CharField(max_length=50, blank=True, choices=PENDIDIKAN)
    gelar_depan = models.CharField(max_length=20, blank=True)
    gelar_belakang = models.CharField(max_length=25, blank=True)
    is_dokter_spesialis = models.BooleanField(default=False, verbose_name='Dokter Spesialis?')
    agama = models.CharField(max_length=12, blank=True)
    stts_nikah = models.CharField(max_length=13, blank=True, verbose_name='Status Nikah', choices=STATUSPERNIKAHAN)
    nip = models.CharField(max_length=18, blank=True, unique=True)
    no_ktp = models.CharField(max_length=16, blank=True)
    no_npwp = models.CharField(max_length=50, blank=True)
    no_jkn = models.CharField(max_length=50, blank=True)
    no_jkk_taspen = models.CharField(max_length=16, blank=True, verbose_name='Nomor JKK/Taspen')
    no_rek_gaji = models.CharField(max_length=50, blank=True, verbose_name='Rekening Gaji')
    file_ktp = models.FileField(verbose_name="KTP", upload_to="profil/ktp/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_npwp = models.FileField(verbose_name="NPWP", upload_to="profil/npwp/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_jkn = models.FileField(verbose_name="BPJS", upload_to="profil/jkn/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_taspen = models.FileField(verbose_name="BPJSTK/Taspen", upload_to="profil/jkk_taspen/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_rek = models.FileField(verbose_name="Rekening", upload_to="profil/rekening/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    foto = models.ImageField(null=True, blank=True, upload_to="profil/foto/", validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.foto:
            return

        try:
            foto_path = self.foto.path
        except (NotImplementedError, ValueError):
            return
        if not os.path.isfile(foto_path):
            return

        try:
            with Image.open(foto_path) as img:
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(foto_path)
        except (FileNotFoundError, OSError, UnidentifiedImageError):
            # Data profil tetap dapat diperbarui bila file lama hilang/rusak.
            return


class ProfilAdmin(models.Model):
    # primary_id = models.BigIntegerField(null=True)
    user = models.OneToOneField(
        Users, primary_key=True, related_name="profil_admin", on_delete=models.CASCADE)
    unor = models.ManyToManyField('strukturorg.UnitOrganisasi', blank=True)
    bidang = models.ManyToManyField('strukturorg.Bidang', blank=True)
    sub_bidang = models.ManyToManyField('strukturorg.SubBidang', blank=True)
    instalasi = models.ManyToManyField('strukturorg.UnitInstalasi', blank=True)
    is_pejabat = models.BooleanField(default=False, verbose_name='Menjabat?')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        data = None
        if self.instalasi.exists():
            data = self.instalasi.all()
        elif self.sub_bidang.exists():
            data = self.sub_bidang.all()
        elif self.bidang.exists():
            data = self.bidang.all()
        elif self.unor.exists():
            data = self.unor.all()
        return f'{self.user}-{data}'
    
    @property
    def penempatan(self):
        data = None
        if self.instalasi.exists():
            data = self.instalasi.all()
        elif self.sub_bidang.exists():
            data = self.sub_bidang.all()
        elif self.bidang.exists():
            data = self.bidang.all()
        elif self.unor.exists():
            data = self.unor.all()
        return str(data)


class AdminScopeAssignment(models.Model):
    """Batas wilayah data untuk satu peran admin operasional."""

    GLOBAL = 'global'
    INSTANSI_DAERAH = 'instansi_daerah'
    SATUAN_KERJA_INDUK = 'satuan_kerja_induk'
    UNIT_ORGANISASI = 'unit_organisasi'
    BIDANG = 'bidang'
    SUB_BIDANG = 'sub_bidang'
    UNIT_INSTALASI = 'unit_instalasi'

    TARGET_FIELDS = (
        INSTANSI_DAERAH,
        SATUAN_KERJA_INDUK,
        UNIT_ORGANISASI,
        BIDANG,
        SUB_BIDANG,
        UNIT_INSTALASI,
    )
    SCOPE_TYPES = (
        (GLOBAL, 'Seluruh organisasi'),
        (INSTANSI_DAERAH, 'Instansi daerah'),
        (SATUAN_KERJA_INDUK, 'Satuan kerja induk'),
        (UNIT_ORGANISASI, 'Unit organisasi'),
        (BIDANG, 'Bidang'),
        (SUB_BIDANG, 'Sub bidang'),
        (UNIT_INSTALASI, 'Unit instalasi'),
    )

    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name='admin_scope_assignments',
    )
    group = models.ForeignKey(
        'auth.Group',
        on_delete=models.CASCADE,
        related_name='admin_scope_assignments',
        verbose_name='Peran admin',
    )
    scope_type = models.CharField(max_length=24, choices=SCOPE_TYPES)
    instansi_daerah = models.ForeignKey(
        'strukturorg.InstansiDaerah',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='admin_scope_assignments',
    )
    satuan_kerja_induk = models.ForeignKey(
        'strukturorg.SatuanKerjaInduk',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='admin_scope_assignments',
    )
    unit_organisasi = models.ForeignKey(
        'strukturorg.UnitOrganisasi',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='admin_scope_assignments',
    )
    bidang = models.ForeignKey(
        'strukturorg.Bidang',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='admin_scope_assignments',
    )
    sub_bidang = models.ForeignKey(
        'strukturorg.SubBidang',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='admin_scope_assignments',
    )
    unit_instalasi = models.ForeignKey(
        'strukturorg.UnitInstalasi',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='admin_scope_assignments',
    )
    scope_key = models.CharField(max_length=64, editable=False)
    valid_from = models.DateField(default=date.today)
    valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('user', 'group', 'scope_type', 'scope_key')
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'group', 'scope_key'),
                name='uniq_admin_role_scope',
            ),
        ]
        verbose_name = 'Cakupan admin'
        verbose_name_plural = 'Cakupan admin'

    @property
    def scope_object(self):
        if self.scope_type == self.GLOBAL:
            return None
        return getattr(self, self.scope_type, None)

    def clean(self):
        super().clean()
        selected = [
            field_name for field_name in self.TARGET_FIELDS
            if getattr(self, f'{field_name}_id', None) is not None
        ]
        if self.scope_type == self.GLOBAL:
            if selected:
                raise ValidationError(
                    'Scope global tidak boleh memiliki target struktur.'
                )
        elif selected != [self.scope_type]:
            raise ValidationError(
                'Pilih tepat satu target struktur yang sesuai dengan jenis scope.'
            )
        if self.group_id and self.group.name not in ADMIN_GROUPS:
            raise ValidationError({
                'group': 'Scope hanya dapat diberikan untuk grup admin SIMADU.'
            })
        if self.valid_until and self.valid_until < self.valid_from:
            raise ValidationError({
                'valid_until': 'Tanggal berakhir tidak boleh sebelum tanggal mulai.'
            })

    def save(self, *args, **kwargs):
        target_id = (
            getattr(self, f'{self.scope_type}_id', None)
            if self.scope_type != self.GLOBAL else None
        )
        self.scope_key = (
            self.GLOBAL
            if self.scope_type == self.GLOBAL
            else f'{self.scope_type}:{target_id}'
        )
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        target = self.scope_object or 'Seluruh organisasi'
        return f'{self.user} - {self.group.name} - {target}'


class TelegramAccount(models.Model):
    user = models.OneToOneField(
        Users,
        related_name='telegram_account',
        on_delete=models.CASCADE,
    )
    telegram_user_id = models.BigIntegerField(unique=True)
    chat_id = models.BigIntegerField(unique=True)
    phone_number = models.CharField(max_length=20)
    telegram_username = models.CharField(max_length=64, blank=True)
    verified_at = models.DateTimeField(auto_now_add=True)
    last_reset_requested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)

    def __str__(self):
        return f'{self.user.email} - {self.telegram_user_id}'


class AccountRegistration(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = (
        (PENDING, 'Menunggu Verifikasi'),
        (APPROVED, 'Disetujui'),
        (REJECTED, 'Ditolak'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name='registration_request',
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='reviewed_account_registrations',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ('-submitted_at',)

    def __str__(self):
        return f'{self.user.email} - {self.get_status_display()}'
