from django.db import models
from django.contrib.auth.models import PermissionsMixin
from django.dispatch import receiver
from django.urls import reverse
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db.models.signals import post_save
from PIL import Image
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_file_size(value):
    filesize = value.size
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
    ('DIV', 'DIV'),
    ('S1', 'S1'),
    ('S2', 'S2'),
    ('S3', 'S3')
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
        if self.foto:
            img = Image.open(self.foto.path)

            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.foto.path)


class ProfilAdmin(models.Model):
    user = models.OneToOneField(
        Users, on_delete=models.CASCADE, primary_key=True, related_name="profil_admin")
    unor = models.ForeignKey('strukturorg.UnitOrganisasi', on_delete=models.SET_NULL, null=True, blank=True)
    bidang = models.ForeignKey('strukturorg.Bidang', on_delete=models.SET_NULL, null=True, blank=True)
    sub_bidang = models.ForeignKey('strukturorg.SubBidang', on_delete=models.SET_NULL, null=True, blank=True)
    instalasi = models.ManyToManyField('strukturorg.UnitInstalasi', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        data = None
        if self.instalasi.exists():
            data = self.instalasi.all()
        elif self.sub_bidang is not None:
            data = self.sub_bidang.sub_bidang
        elif self.bidang is not None:
            data = self.bidang.bidang
        elif self.unor is not None:
            data = self.unor.unor
        return f'{self.user}-{data}'
    
    @property
    def penempatan(self):
        data = None
        if self.instalasi is not None:
            data = self.instalasi.instalasi
        elif self.sub_bidang is not None:
            data = self.sub_bidang.sub_bidang
        elif self.bidang is not None:
            data = self.bidang.bidang
        elif self.unor is not None:
            data = self.unor.unor
        return str(data)