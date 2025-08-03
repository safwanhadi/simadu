from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.template.defaultfilters import slugify
from myaccount.models import Users, Gender
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_file_size(value):
    try:
        filesize = value.size
        if filesize > 2621440:  # 2.5MB limit
            raise ValidationError(_("Ukuran maksimal file 2.5 MB"))
    except Exception:
        return None

# sebagai refrensi jika butuh from pytanggalmerah import TanggalMerah
# sebagai refrensi jika butuh import holidays

# Create your models here.

class DokumenSDM(models.Model):
    nama = models.CharField(max_length=255)
    icon = models.CharField(max_length=50, blank=True)
    update = models.BooleanField(default=False)
    periode_max = models.IntegerField(default=0)
    periode_min = models.IntegerField(default=0)
    url = models.CharField(max_length=100, blank=True)
    view = models.BooleanField(default=False)
    url_param = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.nama

LEVELPEND = (
    ('SD', 'SD'),
    ('SLTP', 'SLTP'),
    ('SLTA', 'SLTA'),
    ('DI', 'DI'),
    ('DII', 'DII'),
    ('DIII', 'DIII'),
    ('DIV', 'DIV'),
    ('S1', 'S1'),
    ('S2', 'S2'),
    ('S3', 'S3'),
    ('Profesi', 'Profesi'),
    ('Spesialis', 'Spesialis'),
    ('Subspesialis', 'Subspesialis'),
)

class RiwayatPendidikan(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    level_pend = models.CharField(max_length=25, choices=LEVELPEND)
    pendidikan = models.CharField(max_length=50)
    nama_sek = models.CharField(max_length=100)
    tgl_lulus = models.DateField(null=True, blank=True)
    no_ijazah = models.CharField(max_length=100)
    gelar_depan = models.CharField(max_length=10, blank=True)
    gelar_belakang = models.CharField(max_length=15, blank=True)
    #Penyetaraan, apabila ijazah yang dimiliki adalah ijazah luar negeri
    no_srt_penyetaraan_ijazah = models.CharField(max_length=50, blank=True)
    file_srt_penyetaraan = models.FileField(verbose_name='File Penyetaraan', upload_to="pendidikan/penyetaraan/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_ijazah = models.FileField(verbose_name="Ijazah", upload_to="pendidikan/ijazah/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_transkrip = models.FileField(verbose_name="Transkrip", upload_to="pendidikan/transkrip/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai} - {self.pendidikan}'
    
    


class AkreditasiProdi(models.Model):
    pendidikan = models.ForeignKey(RiwayatPendidikan, on_delete=models.CASCADE)
    no_sertifikat = models.CharField(max_length=50)
    berlaku_sd = models.DateField()
    file_akreditasi = models.FileField(verbose_name='Sert. Akreditasi', upload_to="pendidikan/akreditasi/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pendidikan.pendidikan


class PangkatGolongan(models.Model):
    golongan = models.CharField(max_length=5)
    ruang = models.CharField(max_length=1)
    pangkat = models.CharField(max_length=50)

    def __str__(self):
        panggol = None
        if self.ruang != '-':
            panggol = f'{self.pangkat}({self.golongan}/{self.ruang})'
        else:
            panggol = f'{self.pangkat}({self.golongan})'
        return panggol


class RiwayatPanggol(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    panggol = models.ForeignKey('PangkatGolongan', on_delete=models.SET_NULL, null=True)
    masa_kerja_tahun = models.IntegerField()
    masa_kerja_bulan = models.IntegerField()
    tmt_gol = models.DateField(blank=True, null=True)
    no_sk = models.CharField(max_length=50)
    tgl_sk = models.DateField(blank=True, null=True)
    no_pertek_bkn = models.CharField(max_length=50, blank=True)
    tgl_pertek_bkn = models.DateField(blank=True, null=True)
    file = models.FileField(verbose_name="SK", upload_to="panggol/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai} - {self.panggol}'
    

JENIS_JABATAN = (
    ('Struktural', 'Struktural'),
    ('Fungsional', 'Fungsional'),
    ('Pelaksana', 'Pelaksana')
)

ESELON = (
    ('Non Eselon', 'Non Eselon'),
    ('IV.b', 'IV.b'),
    ('IV.a', 'IV.a'),
    ('III.b', 'III.b'),
    ('III.a', 'III.a'),
    ('II.b', 'II.b'),
    ('II.a', 'II.a'),
)

KATEGORIJAFUNG=(
    ('Keahlian', 'Keahlian'),
    ('Keterampilan', 'Keterampilan')
)

JAFUNG = (
    ('Pemula', 'Pemula'),
    ('Terampil', 'Terampil'),
    ('Mahir', 'Mahir'),
    ('Penyelia', 'Penyelia'),
    ('Ahli Pertama', 'Ahli Pertama'),
    ('Ahli Muda', 'Ahli Muda'),
    ('Ahli Madya', 'Ahli Madya'),
    ('Ahli Utama', 'Ahli Utama')
)

JABATAN_STRUKTURAL = (
    ('Pengawas', 'Pengawas'),
    ('Administrator', 'Administrator'),
    ('JPT Pratama', 'JPT Pratama'),
    ('JPT Madya', 'JPT Madya'),
)

STATUSPEGAWAI=(
    ('Magang', 'Magang'),
    ('Kontrak', 'Kontrak'),
    ('Mitra', 'Mitra'),
    ('PPPK', 'PPPK'),
    ('CPNS', 'CPNS'),
    ('PNS', 'PNS')
)

class JenjangStruktural(models.Model):
    eselon = models.CharField(max_length=10, choices=ESELON)
    jenjang = models.CharField(max_length=30, choices=JABATAN_STRUKTURAL, blank=True)
    
    def __str__(self):
        return f'{self.jenjang} ({self.eselon})'
    

class JenjangJafung(models.Model):
    kategori = models.CharField(max_length=30, choices=KATEGORIJAFUNG)
    jabatan = models.CharField(max_length=50, choices=JAFUNG, blank=True)
    koefesien = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.jabatan
    
    
class RiwayatPengangkatan(models.Model):#Pengangkatan CPNS, PNS ataupun Kontrak
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    status_pegawai = models.CharField(max_length=10, choices=STATUSPEGAWAI, default="PNS")
    no_srt_putusan = models.CharField(max_length=50)
    tgl_srt_putusan = models.DateField()
    tmt_pegawai = models.DateField(blank=True, null=True)
    pejabat_pelantik = models.CharField(max_length=100, blank=True)
    no_srt_spmt = models.CharField(max_length=50, blank=True)
    tgl_srt_spmt = models.DateField(blank=True, null=True)
    no_srt_latsar = models.CharField(max_length=50, blank=True)
    tgl_srt_latsar = models.DateField(blank=True, null=True)
    karpeg = models.CharField(max_length=50, blank=True)
    file_sk = models.FileField(verbose_name='SK', upload_to="pengangkatan/sk/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_spmt = models.FileField(verbose_name='SPMT', upload_to="pengangkatan/spmt/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_latsar = models.FileField(verbose_name='Sertifikat Latsar', upload_to="pengangkatan/latsar/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')#utk PNS
    file_karpeg = models.FileField(verbose_name='Salinan Karpeg', upload_to="pengangkatan/karpeg/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')#utk PNS
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.status_pegawai
    
    
class RiwayatPenempatan(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    # instansisebelumnya
    instansi_sebelumnya = models.CharField(max_length=200, blank=True, verbose_name='Instansi')
    bidang_sebelumnya = models.CharField(max_length=200, blank=True, verbose_name='Bidang atau yang setara', help_text='Biarkan kosong jika tidak ada')
    seksi_sebelumnya = models.CharField(max_length=200, blank=True, verbose_name='Seksi atau yang setara', help_text='Biarkan kosong jika tidak ada')
    unit_sebelumnya = models.CharField(max_length=200, blank=True, verbose_name='Unit atau yang setara', help_text='Biarkan kosong jika tidak ada')
    # instansi saat ini
    penempatan_level1 = models.ForeignKey('strukturorg.UnitOrganisasi', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Instansi') #pilih salah satu antara level1 s/d level4 tergantung posisi jabatan
    penempatan_level2 = models.ForeignKey('strukturorg.Bidang', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Bidang', help_text='Biar kosong jika tidak ada')
    penempatan_level3 = models.ForeignKey('strukturorg.SubBidang', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Seksi/Subbagian', help_text='Biarkan kosong jika tidak ada')
    penempatan_level4 = models.ForeignKey('strukturorg.UnitInstalasi', on_delete=models.CASCADE, null=True, blank=True, verbose_name='Unit/Instalasi', help_text='Biarkan kosong jika tidak ada')
    no_sk = models.CharField(max_length=50, blank=True, verbose_name='Nomor SK')
    tgl_sk = models.DateField(null=True, blank=True, verbose_name='Tanggal SK')
    file = models.FileField(upload_to="penempatan/", verbose_name="SK Penempatan", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    status = models.BooleanField(default=True) #aktif ditempat penempatan terakhir
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['pegawai', 'status']),
        ]

    def __str__(self):
        data = None
        if self.penempatan_level1:
            if self.penempatan_level4:
                data = f'{self.pegawai.full_name}-{self.penempatan_level4}'
            elif self.penempatan_level3:
                data = f'{self.pegawai.full_name}-{self.penempatan_level3}'
            elif self.penempatan_level2:
                data = f'{self.pegawai.full_name}-{self.penempatan_level2}'
            elif self.penempatan_level1:
                data = f'{self.pegawai.full_name}-{self.penempatan_level1}'
        else:
            if self.unit_sebelumnya:
                data = f'{self.pegawai.full_name}-{self.unit_sebelumnya}'
            elif self.seksi_sebelumnya:
                data = f'{self.pegawai.full_name}-{self.seksi_sebelumnya}'
            elif self.bidang_sebelumnya:
                data = f'{self.pegawai.full_name}-{self.bidang_sebelumnya}'
            elif self.instansi_sebelumnya:
                data = f'{self.pegawai.full_name}-{self.instansi_sebelumnya}'
        return str(data)

    @property
    def unor(self):
        data = None
        if self.penempatan_level1:
            data = self.penempatan_level1
        elif self.penempatan_level2:
            data = self.penempatan_level2.unor
        elif self.penempatan_level3:
            data = self.penempatan_level3.bidang.unor
        elif self.penempatan_level4:
            data = self.penempatan_level4.sub_bidang.bidang.unor
        return str(data)
    
    @property
    def penempatan(self) -> str:
        data = None
        if self.penempatan_level4:
            data = self.penempatan_level4.instalasi
        elif self.penempatan_level3:
            data = self.penempatan_level3.sub_bidang
        elif self.penempatan_level2:
            data = self.penempatan_level2.bidang
        elif self.penempatan_level1:
            data = self.penempatan_level1.unor
        return str(data)
    
    @property
    def pimpinan(self):
        data = None
        if self.penempatan_level1:
            data = f'{self.penempatan_level1.pimpinan} {self.penempatan_level1.unor}'
        elif self.penempatan_level2:
            data = f'{self.penempatan_level2.unor.pimpinan} {self.penempatan_level2.unor}'
        elif self.penempatan_level3:
            data = f'{self.penempatan_level3.bidang.unor.pimpinan} {self.penempatan_level3.bidang.unor}'
        elif self.penempatan_level4:
            data = f'{self.penempatan_level4.sub_bidang.bidang.unor.pimpinan} {self.penempatan_level4.sub_bidang.bidang.unor}'
        return str(data)

    @property
    def jabatan_atasan(self) -> dict:
        data = {}
        if self.penempatan_level4:
            data = {
                'jabatan_atasan1': self.penempatan_level4.sub_bidang.pimpinan,
                'instansi1':  self.penempatan_level4.sub_bidang.sub_bidang,
                'jabatan_atasan2': self.penempatan_level4.sub_bidang.bidang.pimpinan,
                'instansi2': self.penempatan_level4.sub_bidang.bidang.bidang
            }
            data.update(data)
        elif self.penempatan_level3:
            data = {
                'jabatan_atasan1':self.penempatan_level3.bidang.pimpinan,
                'instansi1': self.penempatan_level3.bidang.bidang,
                'jabatan_atasan2': self.penempatan_level3.bidang.unor.pimpinan,
                'instansi2': self.penempatan_level3.bidang.unor.unor
            }
            data.update(data)
        elif self.penempatan_level2:
            data = {
                'jabatan_atasan1':self.penempatan_level2.unor.pimpinan,
                'instansi1': self.penempatan_level2.unor.unor,
                'jabatan_atasan2':self.penempatan_level2.unor.satker_induk.pimpinan,
                'instansi2': self.penempatan_level2.unor.satker_induk.satuan_kerja
            }
            data.update(data)
        elif self.penempatan_level1:
            data = {
                'jabatan_atasan1': self.penempatan_level1.satker_induk.pimpinan,
                'instansi1': self.penempatan_level1.satker_induk.satuan_kerja,
                'jabatan_atasan2':self.penempatan_level1.satker_induk.instansi_daerah.pimpinan,
                'instansi2':  self.penempatan_level1.satker_induk.instansi_daerah.instansi
            }
            data.update(data)
        return data
    
    @property
    def nama_atasan(self):
        data = None
        if self.penempatan_level4:
            data ={
                'nama_atasan1': self.penempatan_level4.sub_bidang.nama_pimpinan.full_name_2 if self.penempatan_level4 is not None and hasattr(self.penempatan_level4.sub_bidang, "nama_pimpinan") else "N/A",
                'nip_atasan1': self.penempatan_level4.sub_bidang.nama_pimpinan.profil_user.nip if self.penempatan_level4 is not None and hasattr(self.penempatan_level4.sub_bidang, 'nama_pimpinan') \
                    and hasattr(self.penempatan_level4.sub_bidang.nama_pimpinan, 'profil_user') else "N/A",
                'nama_atasan2': self.penempatan_level4.sub_bidang.bidang.nama_pimpinan.full_name_2 if self.penempatan_level4 is not None and hasattr(self.penempatan_level4.sub_bidang, 'bidang') and\
                     hasattr(self.penempatan_level4.sub_bidang.bidang, 'nama_pimpinan') else "N/A",
                'nip_atasan2': self.penempatan_level4.sub_bidang.bidang.nama_pimpinan.profil_user.nip if self.penempatan_level4 is not None and hasattr(self.penempatan_level4.sub_bidang, 'bidang') and\
                     hasattr(self.penempatan_level4.sub_bidang.bidang, 'nama_pimpinan') and hasattr(self.penempatan_level4.sub_bidang.bidang.nama_pimpinan, 'profil_user') else "N/A"
            }
            return data
        elif self.penempatan_level3:
            data ={
                'nama_atasan1': f'{self.penempatan_level3.bidang.nama_pimpinan.full_name_2 if self.penempatan_level3 is not None and hasattr(self.penempatan_level3.bidang, "nama_pimpinan") else "N/A"}',
                'nip_atasan1': self.penempatan_level3.bidang.nama_pimpinan.profil_user.nip if self.penempatan_level3 is not None and hasattr(self.penempatan_level3.bidang, 'nama_pimpinan') \
                    and hasattr(self.penempatan_level3.bidang.nama_pimpinan, 'profil_user') else "N/A",
                'nama_atasan2': self.penempatan_level3.bidang.unor.nama_pimpinan.full_name_2 if self.penempatan_level3 is not None and hasattr(self.penempatan_level3.bidang, 'unor') and\
                     hasattr(self.penempatan_level3.bidang.unor, 'nama_pimpinan') else "N/A",
                'nip_atasan2': self.penempatan_level3.bidang.unor.nama_pimpinan.profil_user.nip if self.penempatan_level3 is not None and hasattr(self.penempatan_level3.bidang, 'unor') and\
                     hasattr(self.penempatan_level3.bidang.unor, 'nama_pimpinan') and hasattr(self.penempatan_level3.bidang.unor.nama_pimpinan, 'profil_user') else "N/A"
            }
            return data
        elif self.penempatan_level2:
            data ={
                'nama_atasan1': self.penempatan_level2.unor.nama_pimpinan.full_name_2 if self.penempatan_level2 is not None and hasattr(self.penempatan_level2.unor, "nama_pimpinan") and hasattr(self.penempatan_level2.unor.nama_pimpinan, "full_name_2") else "N/A",
                'nip_atasan1': self.penempatan_level2.unor.nama_pimpinan.profil_user.nip if self.penempatan_level2 is not None and hasattr(self.penempatan_level2.unor, 'nama_pimpinan') \
                    and hasattr(self.penempatan_level2.unor.nama_pimpinan, 'profil_user') else "N/A",
                'nama_atasan2': self.penempatan_level2.unor.satker_induk.nama_pimpinan.full_name_2 if self.penempatan_level2 is not None and hasattr(self.penempatan_level2.unor, 'satker_induk') and\
                     hasattr(self.penempatan_level2.unor.satker_induk, 'nama_pimpinan') else "N/A",
                'nip_atasan2': self.penempatan_level2.unor.satker_induk.nama_pimpinan.profil_user.nip if self.penempatan_level2 is not None and hasattr(self.penempatan_level2.unor, 'satker_induk') and\
                     hasattr(self.penempatan_level2.unor.satker_induk, 'nama_pimpinan') and hasattr(self.penempatan_level2.unor.satker_induk.nama_pimpinan, 'profil_user') else "N/A"
            }
            return data
        elif self.penempatan_level1:
            data ={
                'nama_atasan1':f'{self.penempatan_level1.satker_induk.nama_pimpinan.full_name_2 if self.penempatan_level1 is not None and hasattr(self.penempatan_level1.satker_induk, "nama_pimpinan") and hasattr(self.penempatan_level1.satker_induk.nama_pimpinan, "full_name_2") else "N/A"}',
                'nip_atasan1': self.penempatan_level1.satker_induk.nama_pimpinan.profil_user.nip if self.penempatan_level1 is not None and hasattr(self.penempatan_level1.satker_induk, 'nama_pimpinan')\
                    and hasattr(self.penempatan_level1.satker_induk.nama_pimpinan, 'profil_user') else "N/A",
                'nama_atasan2': self.penempatan_level1.satker_induk.instansi_daerah.nama_pimpinan.full_name_2 if self.penempatan_level1 is not None and hasattr(self.penempatan_level1.satker_induk, 'instansi_daerah') and\
                     hasattr(self.penempatan_level1.satker_induk.instansi_daerah, 'nama_pimpinan') and hasattr(self.penempatan_level1.satker_induk.instansi_daerah.nama_pimpinan, 'full_name') else "N/A",
                'nip_atasan2': self.penempatan_level1.satker_induk.instansi_daerah.nama_pimpinan.profil_user.nip if self.penempatan_level1 is not None and hasattr(self.penempatan_level1.satker_induk, 'instansi_daerah') and\
                     hasattr(self.penempatan_level1.satker_induk.instansi_daerah, 'nama_pimpinan') and hasattr(self.penempatan_level1.satker_induk.instansi_daerah.nama_pimpinan, 'profil_user') else "N/A"
            }
            return data
        return data


class RiwayatGajiBerkala(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True, related_name='gaji_berkala')
    no_srt_gaji = models.CharField(max_length=100, blank=True)
    tgl_srt_gaji = models.DateField(null=True, blank=True, verbose_name='Tgl Surat Gaji')
    gaji_pkk = models.FloatField(default="0.0", verbose_name='Gaji Pokok')
    tmt_gaji = models.DateField(null=True, blank=True, verbose_name='TMT Gaji Berkala')
    pertek = models.CharField(max_length=100, blank=True)
    pangkat = models.ForeignKey(RiwayatPanggol, on_delete=models.SET_NULL, null=True, blank=True)
    tempat_kerja = models.ForeignKey(RiwayatPenempatan, on_delete=models.SET_NULL, null=True, blank=True)
    masa_kerja_tahun = models.SmallIntegerField(default=0)
    masa_kerja_bulan = models.SmallIntegerField(default=0)
    ket = models.TextField(blank=True)
    file = models.FileField(verbose_name='SK', upload_to="berkala/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f'{self.pegawai} ({self.dokumen.nama} - {self.tmt_gaji})'


class RiwayatSKP(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    nilai_skp = models.FloatField(blank=True, null=True)
    orientasi_pel = models.FloatField(blank=True, null=True)
    integritas = models.FloatField(blank=True, null=True)
    komitemen = models.FloatField(blank=True, null=True)
    disiplin = models.FloatField(blank=True, null=True)
    kerjasama = models.FloatField(blank=True, null=True)
    kepemimpinan = models.FloatField(blank=True, null=True)
    jumlah = models.FloatField(blank=True, null=True)
    perilaku = models.FloatField(blank=True, null=True)
    prestasi_kerja = models.FloatField(blank=True, null=True)
    jab_atasan_penilai = models.CharField(max_length=100)
    nama_atasan_penilai = models.CharField(max_length=50)
    unor_atasan_penilai = models.CharField(max_length=50)
    nip_atasan_penilai = models.CharField(max_length=20)
    status_atasan_penilai = models.CharField(max_length=10)
    tmt_gol_atasan_penilai = models.DateField(null=True, blank=True)
    jab_penilai = models.CharField(max_length=100)
    nama_penilai = models.CharField(max_length=50)
    unor_penilai = models.CharField(max_length=50)
    nip_penilai = models.CharField(max_length=20)
    status_penilai = models.CharField(max_length=10)
    tmt_gol_penilai = models.DateField(null=True, blank=True)
    file = models.FileField(verbose_name='SKP', upload_to="skp/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.dokumen} - {self.nilai_skp}'


class PredikatKinerja(models.Model):
    predikat = models.CharField(max_length=20)
    prosentase = models.FloatField()

    def __str__(self):
        return f'{self.predikat} - {self.prosentase}%'


# class RiwayatKonversiAK(models.Model):
#     pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
#     dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
#     jenjang = models.ForeignKey(JenjangJabatanFungsional, on_delete=models.CASCADE)
#     periode_awal = models.DateField(blank=True)
#     peridoe_akhir = models.DateField(blank=True)
#     predikat = models.ForeignKey(RiwayatKinerja, on_delete=models.SET_NULL, null=True)

#     @property
#     def periode(self):
#         data = 1
#         if self.periode_awal == self.peridoe_akhir:
#             data = data
#         elif self.periode_awal < self.peridoe_akhir and self.periode_awal.year == self.peridoe_akhir.year:
#             periode_awal = self.periode_awal.month
#             periode_akhir = self.peridoe_akhir.month
#             listofdata = list(range(periode_awal, periode_akhir+1))
#             data = len(listofdata)
#         else:
#             data = 0
#         return data

#     @property
#     def angka_kredit(self):
#         if ak != 0 and self.predikat.prosentase and self.jenjang.koefesien:
#             #Rumus (ak = (perode penilaian/jumlah bulan dalam satu tahun)*prosentase predikat kinerja * koefesien dalam setahun)
#             ak = (self.periode/12)*self.predikat.prosentase*self.jenjang.koefesien
#         else:
#             ak = "Cek kembali periode penilaian atau prosentase predikat atau koefesien jenjang"
#         return ak


# class DetailPenetapanAK(models.Model):
#     detail = models.CharField(max_length=100)

#     def __str__(self):
#         return self.detail
    

# class RiwayatPAK(models.Model):
#     pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
#     dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
#     penetapan_ak = models.ForeignKey(DetailPenetapanAK, on_delete=models.SET_NULL, null=True)


class UjiKompetensi(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    kompetensi = models.ForeignKey('jenissdm.ListKompetensi', on_delete=models.SET_NULL, null=True, blank=True, related_name='ujikom_kompetensi')
    no_sert_ujikomp = models.CharField(max_length=50, verbose_name='No Sertifikat Kompetensi', blank=True)
    tgl_sert_ujikomp = models.DateField(blank=True, null=True, verbose_name='Tgl Sertifikiat Kompetensi')
    masa_berlaku = models.IntegerField(null=True)
    kategori_kompetensi = models.BooleanField(default=True)
    file_sert = models.FileField(verbose_name="File Sertifikat", upload_to="jabatan/uji_komp/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai}-{self.kompetensi}'


class Kompetensi(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='pegawai_old')
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True, blank=True)
    kompetensi = models.ForeignKey('jenissdm.ListKompetensi', on_delete=models.SET_NULL, null=True, blank=True, related_name='kompetensi_sdm')
    no_sert_komp = models.CharField(max_length=50, verbose_name='No Sertifikat Kompetensi')
    tgl_sert_komp = models.DateField(blank=True, null=True, verbose_name='Tgl Sertifikat Kompetensi')
    masa_berlaku = models.IntegerField(null=True)
    berlaku_sd = models.DateField(blank=True)
    file_sert = models.FileField(verbose_name="File Sertifikat", upload_to="jabatan/kompetensi/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai}-{self.kompetensi}'


class RiwayatJabatan(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE, null=True, blank=True)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True, blank=True)
    unor = models.ForeignKey('strukturorg.UnitOrganisasi', on_delete=models.SET_NULL, null=True, blank=True) #pilih salah satu antara unor/bidang/subbidang tergantung posisi jabatan
    bidang = models.ForeignKey('strukturorg.Bidang', on_delete=models.SET_NULL, null=True, blank=True)
    sub_bidang = models.ForeignKey('strukturorg.SubBidang', on_delete=models.SET_NULL, null=True, blank=True)
    instalasi = models.ForeignKey('strukturorg.UnitInstalasi', on_delete=models.SET_NULL, null=True, blank=True)
    jns_jabatan = models.CharField(max_length=50, choices=JENIS_JABATAN, default='Fungisonal', verbose_name='Jenis Jabatan')
    jenjang_jabatan = models.ForeignKey(JenjangJafung, on_delete=models.SET_NULL, null=True, blank=True)
    kompetensi = models.ManyToManyField(Kompetensi, blank=True)
    nama_jabatan = models.ForeignKey('jenissdm.JenisSDM', on_delete=models.SET_NULL, null=True)
    detail_nama_jabatan = models.CharField(max_length=100, blank=True)
    tmt_jabatan = models.DateField(blank=True, null=True)
    tmt_pelantikan = models.DateField(blank=True, null=True)
    no_sk = models.CharField(max_length=50, null=True, blank=True)
    tgl_sk = models.DateField(blank=True, null=True)
    file = models.FileField(verbose_name="SK", upload_to="jabatan/sk_fungsional/", blank=True, null=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    no_srt_pemberhentian = models.CharField(max_length=50, blank=True)
    tgl_srt_pemberhentian = models.DateField(blank=True, null=True)
    file_pemberhentian = models.FileField(verbose_name="SK Pemberhentian/Pembebasan", upload_to="jabatan/sk_fungs_pemberhentian/", blank=True, null=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.pegawai} - {self.jenjang_jabatan}'
    

class RiwayatPAK(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    no_srt = models.CharField(max_length=50, blank=True)
    tgl_srt = models.DateField(blank=True)
    ak = models.IntegerField()
    file = models.FileField(verbose_name='File PAK', upload_to='pak/', blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.ak)
    
HASILKINERJA = (
    ('Diatas Ekspektasi', 'Diatas Ekspektasi'),
    ('Sesuai Ekspektasi', 'Sesuai Ekspektasi'),
    ('Dibawah Ekspektasi', 'Dibawah Ekspektasi')
)


class RiwayatKinerja(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='nama_pengguna')
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    hasil_kinerja = models.CharField(max_length=30, blank=True, choices=HASILKINERJA)
    prilaku_kinerja = models.CharField(max_length=30, blank=True, choices=HASILKINERJA)
    kuadran_kinerja = models.ForeignKey(PredikatKinerja, on_delete=models.SET_NULL, null=True, verbose_name='Predikat Kinerja')
    periode_kinerja_awal = models.DateField(blank=True, null=True)
    periode_kinerja_akhir = models.DateField(blank=True, null=True)
    # status_periode_kinerja = models.CharField(max_length=50, verbose_name='Periode Waktu Penilaian')# (bulanan, triwulan, semester, tahunan)
    nama_penilai = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, related_name='nama_penilai')
    file = models.FileField(upload_to='kinerja/', blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.kuadran_kinerja.predikat


class RiwayatPenghargaan(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    jenis_penghargaan = models.CharField(max_length=100)
    tahun_perolehan = models.SmallIntegerField()
    no_srt_kep = models.CharField(max_length=50, blank=True)
    tgl_srt_kep = models.DateField(blank=True, null=True)
    file = models.FileField(verbose_name='SK', upload_to="penghargaan/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.jenis_penghargaan
    
JENIS_HUKUMAN = (
    ('Teguran Lisan', 'Teguran Lisan'),
    ('Teguran Tertulis', 'Teguran Tertulis'),
    ('Pemotongan Penghasilan', 'Pemotongan Penghasilan'),
    ('PHK', 'PHK')
)
class RiwayatHukuman(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    jenis_hukuman = models.CharField(max_length=100, choices=JENIS_HUKUMAN)
    no_srt_kep = models.CharField(max_length=50, blank=True)
    tgl_srt_kep = models.DateField(blank=True, null=True)
    hukuman_ke = models.CharField(max_length=2, blank=True)
    ket = models.TextField(blank=True)
    file = models.FileField(verbose_name='SK', upload_to="hukuman/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.jenis_hukuman


JENISCUTI=(
    ('Cuti Tahunan', 'Cuti Tahunan'),
    ('Cuti Alasan Penting', 'Cuti Alasan Penting'),
    ('Cuti melahirkan', 'Cuti Melahirkan'),
    ('Cuti Sakit', 'Cuti Sakit'),
    ('Cuti Besar', 'Cuti Besar'),
    ('Cuti Diluar Tanggungan Negara', 'Cuti Diluar Tanggungan Negara'),
    ('Cuti Tertunda', 'Cuti Tertunda')
)

STATUSCUTI = (
    ('Tunda', 'Tunda'),
    ('Proses', 'Proses'),
    ('Selesai', 'Selesai')
)
    
class RiwayatCuti(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    usulan = models.ForeignKey('layanan.LayananCuti', on_delete=models.CASCADE, null=True, blank=True)
    jenis_cuti = models.CharField(max_length=50, choices=JENISCUTI)
    alasan_cuti = models.CharField(max_length=255, blank=True)
    tgl_mulai_cuti = models.DateField(null=True, blank=True)
    tgl_akhir_cuti = models.DateField(null=True, blank=True)
    lama_cuti = models.SmallIntegerField(null=True, default=0)   
    domisili_saat_cuti = models.CharField(max_length=250, blank=True)
    # tahun_cuti = models.SmallIntegerField(null=True)
    no_surat = models.CharField(max_length=50, blank=True)
    tgl_surat = models.DateField(null=True, blank=True)
    file_pengajuan = models.FileField(upload_to="cuti/pengajuan/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_pendukung = models.FileField(verbose_name="Dokumen Pendukung", upload_to="cuti/pendukung/", blank=True, help_text="Dapat berupa surat ket. penyerahan tugas", validators=[validate_file_size])
    file = models.FileField(verbose_name='Surat Cuti', upload_to="cuti/surat/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    status_cuti = models.CharField(max_length=10, choices=STATUSCUTI, default='Proses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # @property
    # def lama_cuti(self):
    #     t = TanggalMerah(cache_path=None, cache_time=600)
    #     durasi = self.tgl_mulai_cuti - self.tgl_akhir_cuti
    #     libur = holidays.CountryHoliday('IDN')
    #     if self.jenis_cuti == 'Cuti Alasan Penting':
    #         return durasi
    #     else:
    #         if t.is_sunday():
    #             return durasi - 1
    #         elif t.is_holiday():
    #             return durasi - 1

    def __str__(self):
        return f'{self.pegawai.first_name} - {self.jenis_cuti} - ({self.lama_cuti})'
    
    @property
    def file_size(self):
        return self.file.size
    
    @property
    def file_pendukung_size(self):
        return self.file_pendukung.size

    @property
    def file_pengajuan_size(self):
        return self.file_pengajuan.size
    
    
METODE = (
    ("Daring", "Daring"),
    ("Luring", "Luring"),
    ("Hybrid", "Hybrid")
)
class RiwayatDiklat(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ManyToManyField(Users, blank=True)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    jenis_diklat = models.CharField(max_length=100, help_text='Contoh: Workshop/Seminar/Pelatihan/Simposium/ dll')#workshop/seminar/pelatihan/simposium/ dll
    nama_diklat = models.CharField(max_length=250)
    penyelenggara = models.CharField(max_length=50)
    metode = models.CharField(max_length=10, blank=True, choices=METODE)
    no_sertifikat = models.CharField(max_length=50, blank=True)
    tgl_sertifikat = models.DateField(blank=True, null=True)
    skp = models.FloatField(null=True, blank=True, default=0.0)
    tgl_mulai = models.DateField(null=True, blank=True)
    tgl_selesai = models.DateField(null=True, blank=True)
    jam_pelajaran = models.CharField(max_length=2, blank=True)
    kategori_kompetensi = models.BooleanField(default=False, verbose_name='Masukkan Sebagai Kompetensi')
    kompetensi = models.ForeignKey('jenissdm.ListKompetensi', on_delete=models.SET_NULL, null=True, blank=True, related_name='diklat_kompetensi')
    periode_berlaku_sertifikat = models.SmallIntegerField(null=True, blank=True, default=0)
    usulan = models.ForeignKey('layanan.LayananUsulanDiklat', on_delete=models.SET_NULL, null=True, blank=True)
    is_usulan = models.BooleanField(default=False)
    file = models.FileField(verbose_name='Sertifikat', upload_to="diklat/sertifikat/", blank=True, null=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_laporan = models.FileField(verbose_name='Laporan Pelatihan', upload_to="diklat/laporan/", blank=True, null=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nama_diklat
    
    @property
    def lama_diklat(self):
        lama = relativedelta(self.tgl_selesai, self.tgl_mulai)
        return lama.days
    
    
class RiwayatOrganisasi(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    nama_org = models.CharField(max_length=50)
    jabatan = models.CharField(max_length=50)
    no_anggota = models.CharField(max_length=30, blank=True)
    tgl_gabung = models.DateField(null=True, blank=True)
    tgl_keluar = models.DateField(null=True, blank=True)
    file = models.FileField(verbose_name='Sertifikat', upload_to="organisasi/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.nama_org


class RiwayatProfesi(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    profesi = models.ForeignKey('jenissdm.JenisSDM', on_delete=models.SET_NULL, null=True, blank=True)
    no_str = models.CharField(max_length=50, blank=True, verbose_name='No STR')
    tgl_str = models.DateField(null=True, blank=True, verbose_name='tanggal STR')
    file_str = models.FileField(verbose_name='STR', upload_to="profesi/str/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.profesi} {self.pegawai}'
    

class RiwayatSIPProfesi(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    riwayat_profesi = models.ForeignKey(RiwayatProfesi, on_delete=models.CASCADE)
    no_sip = models.CharField(max_length=50, blank=True, verbose_name='No SIP')
    tgl_sip =models.DateField(null=True, blank=True, verbose_name='Tanggal SIP')
    berlaku_sd = models.DateField(null=True, blank=True, verbose_name='Berlaku s/d')
    file_sip = models.FileField(verbose_name='File SIP', upload_to="profesi/sip/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
class RiwayatBekerja(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    nama_instansi = models.CharField(max_length=50)
    jabatan = models.CharField(max_length=50)
    no_sk = models.CharField(max_length=50, blank=True)
    tgl_sk = models.DateField(null=True, blank=True)
    tgl_mulai = models.DateField(null=True, blank=True)
    tgl_selesai = models.DateField(null=True, blank=True)
    file = models.FileField(verbose_name='SK', upload_to="bekerja/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.nama_instansi
    
STATUSKELUARGA=(
    ('Orang Tua', 'Orang Tua'),
    ('Pasangan', 'Pasangan'),
    ('Anak', 'Anak')
)

PEKERJAAN=(
    ('PNS/TNI/POLRI', 'PNS/TNI/POLRI'),
    ('Wirausaha', 'Wirausaha'),
    ('Swasta', 'Swasta'),
    ('Tani', 'Tani'),
    ('Nelayan', 'Nelayan'),
    ('Lainnya', 'Lainnya')
)

STATUSANAK=(
    ('Anak Kandung', 'Anak Kandung'),
    ('Anak Tiri', 'Anak Tiri'),
    ('Anak Angkat', 'Anak Angkat')
)

class RiwayatKeluarga(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    no_kk = models.CharField(max_length=25, null=True, blank=True)
    file = models.FileField(verbose_name='KK', upload_to="keluarga/kk/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.dokumen} {self.pegawai}'
    
    
class OrangTua(models.Model):
    keluarga = models.ForeignKey('RiwayatKeluarga', on_delete=models.SET_NULL, null=True)
    status_hidup = models.BooleanField(default=True)
    nama = models.CharField(max_length=50)
    status_klg = models.CharField(max_length=15, choices=STATUSKELUARGA, blank=True)
    slug_status = models.CharField(max_length=25, blank=True)
    pekerjaan = models.CharField(max_length=50, choices=PEKERJAAN)
    jk = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True, blank=True)
    nik = models.CharField(max_length=16, blank=True)
    agama = models.CharField(max_length=10, blank=True)
    tlp = models.CharField(max_length=15, blank=True)
    alamat = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.nama
    

class Pasangan(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    keluarga = models.ForeignKey('RiwayatKeluarga', on_delete=models.SET_NULL, null=True)
    status_hidup = models.BooleanField(default=True)
    nama = models.CharField(max_length=50)
    status_klg = models.CharField(max_length=15, choices=STATUSKELUARGA, blank=True)
    slug_status = models.CharField(max_length=25, blank=True)
    pasangan_ke = models.CharField(max_length=1, blank=True)
    tempat_lahir = models.CharField(max_length=100, blank=True)
    tgl_lahir = models.DateField(null=True, blank=True)
    akte_meninggal = models.CharField(max_length=50, blank=True)
    tgl_meninggal = models.DateField(null=True, blank=True)
    akte_menikah = models.CharField(max_length=50, blank=True)
    tgl_menikah = models.DateField(null=True, blank=True)
    akte_cerai = models.CharField(max_length=50, blank=True)
    tgl_cerai = models.DateField(null=True, blank=True)
    pekerjaan = models.CharField(max_length=50, choices=PEKERJAAN)
    jk = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True, blank=True)
    nik = models.CharField(max_length=16, blank=True)
    karsu_karis = models.CharField(max_length=50, blank=True)
    agama = models.CharField(max_length=10, blank=True)
    tlp = models.CharField(max_length=15, blank=True)
    alamat = models.TextField(blank=True)
    masuk_daftar_gaji = models.BooleanField(default=False)
    file_akte_nikah = models.FileField(upload_to='keluarga/akte/', blank=True, null=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.nama
    
    
class Anak(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    keluarga = models.ForeignKey('RiwayatKeluarga', on_delete=models.SET_NULL, null=True)
    nama = models.CharField(max_length=50)
    status_klg = models.CharField(max_length=15, choices=STATUSKELUARGA, blank=True)
    slug_status = models.CharField(max_length=25, blank=True)
    tempat_lahir = models.CharField(max_length=100, blank=True)
    tgl_lahir = models.DateField(null=True, blank=True)
    status_hidup = models.BooleanField(default=True)
    akte_meninggal = models.CharField(max_length=50, blank=True)
    tgl_meninggal = models.DateField(null=True, blank=True)
    pekerjaan = models.CharField(max_length=50, choices=PEKERJAAN)
    jk = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True, blank=True)
    nik = models.CharField(max_length=16, blank=True)
    # status_anak = models.CharField(max_length=50, blank=True, choices=STATUSANAK)
    agama = models.CharField(max_length=10, blank=True)
    tlp = models.CharField(max_length=15, blank=True)
    alamat = models.TextField(blank=True)
    masuk_daftar_gaji = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.nama
    

@receiver(pre_save, sender=OrangTua)
def slugify_status_klg(sender, instance, *args, **kwargs):
    instance.slug_status = slugify(instance.status_klg)

@receiver(pre_save, sender=Pasangan)
def slugify_status_klg(sender, instance, *args, **kwargs):
    instance.slug_status = slugify(instance.status_klg)

@receiver(pre_save, sender=Anak)
def slugify_status_klg(sender, instance, *args, **kwargs):
    instance.slug_status = slugify(instance.status_klg)


class BidangInovasi(models.Model):
    bidang = models.CharField(max_length=100)

    def __str__(self):
        return self.bidang


class RiwayatInovasi(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    bidang = models.ForeignKey(BidangInovasi, on_delete=models.SET_NULL, null=True) #keperawatan, medis, teknologi, administrasi, kefarmasian, kesehatan lainnya, umum lainnya
    judul = models.CharField(max_length=200)
    desk = models.TextField(blank=True)#berisi penjelasan singkat/abstrak inovasi
    makalah = models.FileField(upload_to='inovasi/makalah/', blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    no_sk = models.CharField(max_length=100, blank=True)
    tanggal = models.DateField(blank=True, null=True)
    file_sk = models.FileField(upload_to='inovasi/sk/', blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f'{self.pegawai.full_name}-{self.judul}'


PERAN = (
    ('Panitia', 'Panitia'),
    ('Narasumber', 'Narasumber'),
    ('Peserta', 'Peserta'),
    ('Moderator', 'Moderator'),
    ('MC', 'MC')
)

SUMBER_ANGGARAN = (
    ('RS Mandalika', 'RS Mandalika'),
    ('Vendor', 'Vendor'),
    ('Mandiri', 'Mandiri')
)
class RiwayatPenugasan(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    jabatan = models.ForeignKey(RiwayatJabatan, on_delete=models.SET_NULL, null=True)
    panggol = models.ForeignKey(RiwayatPanggol, on_delete=models.SET_NULL, null=True, blank=True)
    nama_keg = models.CharField(max_length=250)
    tempat_keg = models.CharField(max_length=200, blank=True)
    peran = models.CharField(max_length=50, blank=True, choices=PERAN)
    lama_keg = models.SmallIntegerField(null=True, blank=True)
    tgl_mulai = models.DateField(blank=True)
    tgl_selesai = models.DateField(blank=True)
    anggaran = models.BooleanField(default=False)
    sumber_angg = models.CharField(max_length=50, blank=True, choices=SUMBER_ANGGARAN)
    file_spt = models.FileField(upload_to='spt/', blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.pegawai}-{self.nama_keg}'