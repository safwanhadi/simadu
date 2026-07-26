from django.db import models
from django.db.models import Q, Sum
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from django.template.defaultfilters import slugify
from myaccount.models import Users, Gender
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from strukturorg.services import get_active_leader

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
    is_verifikasi = models.BooleanField(default=False)
    file_srt_penyetaraan = models.FileField(verbose_name='File Penyetaraan', upload_to="pendidikan/penyetaraan/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_ijazah = models.FileField(verbose_name="Ijazah", upload_to="pendidikan/ijazah/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_transkrip = models.FileField(verbose_name="Transkrip", upload_to="pendidikan/transkrip/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_verifikasi = models.FileField(verbose_name="File Hasil Verifikasi", upload_to="pendidikan/verifikasi/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
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
    usulan = models.ForeignKey('layanan.LayananNaikPangkat', on_delete=models.SET_NULL, null=True, blank=True)
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

OPTIONAL_DOCUMENT_URLS = {'hukuman', 'penghargaan'}


class KewajibanDokumen(models.Model):
    dokumen = models.ForeignKey(
        DokumenSDM,
        on_delete=models.CASCADE,
        related_name='kewajiban_status',
    )
    status_pegawai = models.CharField(max_length=10, choices=STATUSPEGAWAI)
    wajib = models.BooleanField(
        default=True,
        help_text='Jika tidak wajib, menu tetap terlihat tetapi tidak ditandai merah saat kosong.',
    )

    class Meta:
        verbose_name = 'Kewajiban Dokumen'
        verbose_name_plural = 'Kewajiban Dokumen'
        constraints = [
            models.UniqueConstraint(
                fields=('dokumen', 'status_pegawai'),
                name='unique_kewajiban_dokumen_status',
            ),
        ]
        ordering = ('dokumen__nama', 'status_pegawai')

    def __str__(self):
        sifat = 'Wajib' if self.wajib else 'Opsional'
        return f'{self.dokumen} - {self.get_status_pegawai_display()} ({sifat})'


@receiver(post_save, sender=DokumenSDM)
def create_default_document_requirements(sender, instance, created, **kwargs):
    """Dokumen baru berlaku umum; pangkat/golongan khusus PNS secara default."""
    if not created:
        return
    statuses = ['PNS'] if instance.url == 'panggol' else [
        value for value, _label in STATUSPEGAWAI
    ]
    KewajibanDokumen.objects.bulk_create([
        KewajibanDokumen(
            dokumen=instance,
            status_pegawai=status,
            wajib=instance.url not in OPTIONAL_DOCUMENT_URLS,
        )
        for status in statuses
    ])

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
    
    @property
    def desk_status_pegawai(self):
        if self.status_pegawai == 'PNS':
            return "Pegawai Negeri Sipil (PNS)"
        elif self.status_pegawai == 'CPNS':
            return "Calon Pegawai Negeri Sipil (CPNS)"
        elif self.status_pegawai == 'PPPK':
            return "Pegawai Pemerintah dengan Perjanjian Kerja (PPPK)"
        else:
            return self.status_pegawai
        
    
    def __str__(self):
        return self.status_pegawai


class RiwayatPenempatan(models.Model):
    """
    Model untuk mencatat riwayat penempatan pegawai.
    Direfaktor untuk efisiensi dan keamanan data, dengan tetap mempertahankan
    nama properti original untuk kompatibilitas.
    """
    # 1. FIELDS (Tetap Sama)
    # ==============================================================================
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='riwayat_penempatan')
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    #instansi diluar sistem
    instansi_sebelumnya = models.CharField(max_length=200, blank=True, verbose_name='Instansi')
    bidang_sebelumnya = models.CharField(max_length=200, blank=True, verbose_name='Bidang atau yang setara')
    seksi_sebelumnya = models.CharField(max_length=200, blank=True, verbose_name='Seksi atau yang setara')
    unit_sebelumnya = models.CharField(max_length=200, blank=True, verbose_name='Unit atau yang setara')
    #instansi di dalam sistem
    penempatan_level1 = models.ForeignKey('strukturorg.UnitOrganisasi', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Instansi (Level 1)')
    penempatan_level2 = models.ForeignKey('strukturorg.Bidang', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Bidang (Level 2)')
    penempatan_level3 = models.ForeignKey('strukturorg.SubBidang', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Seksi/Subbagian (Level 3)')
    penempatan_level4 = models.ForeignKey('strukturorg.UnitInstalasi', on_delete=models.CASCADE, null=True, blank=True, verbose_name='Unit/Instalasi (Level 4)')
    no_sk = models.CharField(max_length=50, blank=True, verbose_name='Nomor SK')
    tgl_sk = models.DateField(null=True, blank=True, verbose_name='Tanggal SK')
    file = models.FileField(upload_to="penempatan/", verbose_name="SK Penempatan", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    status = models.BooleanField(default=True, verbose_name="Status Penempatan Aktif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 2. META & VALIDATION (Perbaikan)
    # ==============================================================================
    class Meta:
        indexes = [
            models.Index(fields=['pegawai', 'status']),
        ]
        verbose_name = "Riwayat Penempatan"
        verbose_name_plural = "Riwayat Penempatan"

    # 3. HELPER PROPERTY (Logika Internal Baru)
    # ==============================================================================
    @property
    def _penempatan_aktif(self):
        """Helper privat untuk mendapatkan objek dan level penempatan yang aktif."""
        if self.penempatan_level4: return self.penempatan_level4, 'level4'
        if self.penempatan_level3: return self.penempatan_level3, 'level3'
        if self.penempatan_level2: return self.penempatan_level2, 'level2'
        if self.penempatan_level1: return self.penempatan_level1, 'level1'
        return None, None

    # 4. PUBLIC PROPERTIES (Nama & Output Sama Seperti Asli, Implementasi Baru)
    # ==============================================================================
    def __str__(self):
        obj, _ = self._penempatan_aktif
        nama_penempatan = str(obj) if obj else "Penempatan Tidak Diketahui"
        return f'{self.pegawai.full_name} - {nama_penempatan}'

    @property
    def unor(self):
        obj, level = self._penempatan_aktif
        if not obj: return None
        try:
            if level == 'level4': return obj.sub_bidang.bidang.unor
            if level == 'level3': return obj.bidang.unor
            if level == 'level2': return obj.unor
            if level == 'level1': return obj
        except AttributeError:
            return None
        
    @property
    def pimpinan(self):
        unor_obj = self.unor
        if unor_obj:
            return f'{unor_obj.pimpinan} {unor_obj.unor}'
        return "N/A"
    
    @property
    def unor_pimpinan(self):
        unor_obj = getattr(self, "unor", None)

        # Kalau ingin konsisten: selalu kembalikan struktur lengkap
        result = {
            "pimpinan": getattr(unor_obj, "pimpinan", None) if unor_obj else None,
            "unor": getattr(unor_obj, "unor", None) if unor_obj else None,
            "nama_pimpinan": "N/A",
            "nip": "N/A",
            "panggol": "N/A",
        }

        if not unor_obj:
            return result

        user = get_active_leader(unor_obj)
        if not user:
            return result

        result["nama_pimpinan"] = getattr(user, "full_name_2", "N/A")

        # Profil user (OneToOne) yang aman
        profil = getattr(user, "profil_user", None)
        if profil:
            result["nip"] = getattr(profil, "nip", "N/A")

        # Pangkat/gol terakhir -> cukup 1 query
        panggol_qs = getattr(user, "riwayatpanggol_set", None)
        if panggol_qs:
            panggol_last = panggol_qs.select_related("panggol").order_by("-id").first()
            if panggol_last and panggol_last.panggol:
                result['panggol'] = f'{panggol_last.panggol.pangkat} ({panggol_last.panggol.golongan}/{panggol_last.panggol.ruang})'

        return result

    @property
    def penempatan(self) -> str:
        obj, level = self._penempatan_aktif
        if not obj: return "N/A"
        try:
            if level == 'level4': return obj.instalasi
            if level == 'level3': return obj.sub_bidang
            if level == 'level2': return obj.bidang
            if level == 'level1': return obj.unor
        except AttributeError:
            return "Data Penempatan Tidak Lengkap"
        return "N/A"

    @property
    def jabatan_atasan(self) -> dict:
        obj, level = self._penempatan_aktif
        if not obj: return {}
        
        data = {}
        try:
            if level == 'level4':
                data = {'jabatan_atasan1': obj.sub_bidang.pimpinan, 'instansi1': obj.sub_bidang.sub_bidang, 'jabatan_atasan2': obj.sub_bidang.bidang.pimpinan, 'instansi2': obj.sub_bidang.bidang.bidang}
            elif level == 'level3':
                data = {'jabatan_atasan1': obj.bidang.pimpinan, 'instansi1': obj.bidang.bidang, 'jabatan_atasan2': obj.bidang.unor.pimpinan, 'instansi2': obj.bidang.unor.unor}
            elif level == 'level2':
                data = {'jabatan_atasan1': obj.unor.pimpinan, 'instansi1': obj.unor.unor, 'jabatan_atasan2': obj.unor.satker_induk.pimpinan, 'instansi2': obj.unor.satker_induk.satuan_kerja}
            elif level == 'level1':
                data = {'jabatan_atasan1': obj.satker_induk.pimpinan, 'instansi1': obj.satker_induk.satuan_kerja, 'jabatan_atasan2': obj.satker_induk.instansi_daerah.pimpinan, 'instansi2': obj.satker_induk.instansi_daerah.instansi}
        except AttributeError:
            # Jika struktur tidak lengkap, kembalikan dict kosong agar tidak error
            return {}
        return data

    @property
    def nama_atasan(self) -> dict:
        obj, level = self._penempatan_aktif
        if not obj: return {}

        data = {'nama_atasan1': 'N/A', 'nip_atasan1': 'N/A', 'nama_atasan2': 'N/A', 'nip_atasan2': 'N/A'}
        try:
            atasan1, atasan2 = None, None
            if level == 'level4':
                atasan1 = get_active_leader(obj.sub_bidang)
                atasan2 = get_active_leader(obj.sub_bidang.bidang)
            elif level == 'level3':
                atasan1 = get_active_leader(obj.bidang)
                atasan2 = get_active_leader(obj.bidang.unor)
            elif level == 'level2':
                atasan1 = get_active_leader(obj.unor)
                atasan2 = get_active_leader(obj.unor.satker_induk)
            elif level == 'level1':
                atasan1 = get_active_leader(obj.satker_induk)
                atasan2 = get_active_leader(obj.satker_induk.instansi_daerah)

            if atasan1:
                data['nama_atasan1'] = getattr(atasan1, 'full_name_2', 'N/A')
                profil1 = getattr(atasan1, 'profil_user', None)
                if profil1: data['nip_atasan1'] = getattr(profil1, 'nip', 'N/A')
            
            if atasan2:
                data['nama_atasan2'] = getattr(atasan2, 'full_name_2', 'N/A')
                profil2 = getattr(atasan2, 'profil_user', None)
                if profil2: data['nip_atasan2'] = getattr(profil2, 'nip', 'N/A')
        except AttributeError:
            pass # Kembalikan data default jika ada struktur yang hilang
            
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
    has_layanan = models.BooleanField(default=False)
    is_final = models.BooleanField(default=False)
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
    usulan = models.ForeignKey('layanan.LayananNaikJabatan', on_delete=models.SET_NULL, null=True, blank=True)  
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
    ('diatas', 'Diatas Ekspektasi'),
    ('sesuai', 'Sesuai Ekspektasi'),
    ('dibawah', 'Dibawah Ekspektasi')
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
        if self.kuadran_kinerja:
            return self.kuadran_kinerja.predikat
        periode = self.periode_kinerja_akhir or self.periode_kinerja_awal
        return f'Kinerja {periode}' if periode else 'Riwayat Kinerja'


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
)

STATUS_PELAKSANAAN_CUTI = (
    ('Belum', 'Belum dilaksanakan'),
    ('Berlangsung', 'Sedang berlangsung'),
    ('Selesai', 'Selesai'),
    ('Tunda', 'Ditunda'),
    ('Batal', 'Tidak dilaksanakan'),
)
    
class RiwayatCuti(models.Model):
    no_urut_dokumen = models.IntegerField(default=0)
    pegawai = models.ForeignKey(Users, on_delete=models.CASCADE)
    dokumen = models.ForeignKey('DokumenSDM', on_delete=models.SET_NULL, null=True)
    usulan = models.OneToOneField('layanan.LayananCuti', on_delete=models.CASCADE, null=True, blank=True, related_name='cuti_usulan')
    jenis_cuti = models.CharField(max_length=50, choices=JENISCUTI)
    alasan_cuti = models.CharField(max_length=255, blank=True)
    tgl_mulai_cuti = models.DateField(null=True, blank=True)
    tgl_akhir_cuti = models.DateField(null=True, blank=True)
    lama_cuti = models.SmallIntegerField(null=True, default=0)   
    domisili_saat_cuti = models.CharField(max_length=250, blank=True)
    tahun_cuti = models.SmallIntegerField(null=True)
    no_surat = models.CharField(max_length=50, blank=True)
    tgl_surat = models.DateField(null=True, blank=True)
    file_pengajuan = models.FileField(upload_to="cuti/pengajuan/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    file_pendukung = models.FileField(verbose_name="Dokumen Pendukung", upload_to="cuti/pendukung/", blank=True, help_text="Dapat berupa surat ket. penyerahan tugas", validators=[validate_file_size])
    file = models.FileField(verbose_name='Surat Cuti', upload_to="cuti/surat/", blank=True, validators=[validate_file_size], help_text='Ukuran maksimal file 2.5MB')
    status_cuti = models.CharField(
        max_length=12,
        choices=STATUS_PELAKSANAAN_CUTI,
        default='Belum',
        verbose_name='Status Pelaksanaan Cuti',
    )
    pakai_tunda_saja = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def tentukan_status_pelaksanaan(self, pada=None):
        """Tentukan status pelaksanaan tanpa mencampurnya dengan proses pengajuan."""
        if self.status_cuti in ('Tunda', 'Batal'):
            return self.status_cuti
        if self.usulan_id and self.usulan.status not in ('disetujui', 'selesai'):
            return 'Belum'
        if not self.tgl_mulai_cuti or not self.tgl_akhir_cuti:
            return self.status_cuti

        if pada is None:
            sekarang = timezone.now()
            pada = (
                timezone.localtime(sekarang).date()
                if timezone.is_aware(sekarang)
                else sekarang.date()
            )
        if pada < self.tgl_mulai_cuti:
            return 'Belum'
        if pada <= self.tgl_akhir_cuti:
            return 'Berlangsung'
        return 'Selesai'

    @property
    def status_pelaksanaan_aktual(self):
        return self.tentukan_status_pelaksanaan()

    @property
    def status_pelaksanaan_display(self):
        return dict(STATUS_PELAKSANAAN_CUTI).get(
            self.status_pelaksanaan_aktual,
            self.status_pelaksanaan_aktual,
        )

    # ==== Tambahan helper untuk cuti tunda ====
    @property
    def total_hari_tunda_terklaim(self) -> int:
        """
        Total hari dari record cuti TUNDA ini yang sudah diklaim
        melalui KlaimCutiTunda.
        """
        if self.status_cuti != 'Tunda':
            return 0
        return self.klaim_keluar.filter(
            cuti_klaim__status_cuti__in=('Belum', 'Berlangsung', 'Selesai'),
        ).filter(
            Q(cuti_klaim__usulan__status__in=(
                'pengajuan', 'tindaklanjut', 'disetujui', 'selesai',
            ))
            | Q(cuti_klaim__usulan__isnull=True)
        ).aggregate(
            total=Sum('jumlah_hari_diklaim')
        ).get('total') or 0

    @property
    def sisa_hari_tunda(self) -> int:
        """
        Sisa hari hak tunda yang masih bisa diklaim.
        """
        if self.status_cuti != 'Tunda':
            return 0
        return max(0, (self.lama_cuti or 0) - self.total_hari_tunda_terklaim)

    def __str__(self):
        return f'{self.pegawai} - {self.jenis_cuti} ({self.tahun_cuti})'
    
    @property
    def file_size(self):
        return self.file.size
    
    @property
    def file_pendukung_size(self):
        return self.file_pendukung.size

    @property
    def file_pengajuan_size(self):
        return self.file_pengajuan.size


class KlaimCutiTunda(models.Model):
    """
    Menghubungkan cuti TUNDA tahun sebelumnya
    dengan cuti TAHUNAN tahun berjalan yang mengklaim hak tersebut.
    """
    sumber_tunda = models.ForeignKey(
        RiwayatCuti,
        on_delete=models.CASCADE,
        related_name='klaim_keluar',
        limit_choices_to={'status_cuti': 'Tunda'},
    )
    cuti_klaim = models.ForeignKey(
        RiwayatCuti,
        on_delete=models.CASCADE,
        related_name='klaim_masuk',
        help_text='Cuti tahunan yang memakai hak tunda',
    )
    jumlah_hari_diklaim = models.PositiveSmallIntegerField()
    is_admin_override = models.BooleanField(default=False)
    admin_override_by = models.ForeignKey(
        Users,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='klaim_tunda_override'
    )
    admin_override_at = models.DateTimeField(null=True, blank=True)
    catatan_admin = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Klaim Cuti Tunda'
        verbose_name_plural = 'Klaim Cuti Tunda'

    def clean(self):
        super().clean()
        if self.jumlah_hari_diklaim is not None and self.jumlah_hari_diklaim <= 0:
            raise ValidationError('Jumlah hari yang diklaim harus lebih dari 0.')
        if self.sumber_tunda_id and self.cuti_klaim_id:
            if self.sumber_tunda_id == self.cuti_klaim_id:
                raise ValidationError('Sumber cuti tunda tidak boleh sama dengan cuti yang mengklaim.')
            if self.sumber_tunda.pegawai_id != self.cuti_klaim.pegawai_id:
                raise ValidationError('Sumber cuti tunda dan cuti klaim harus milik pegawai yang sama.')
            if (
                self.sumber_tunda.status_cuti != 'Tunda'
                or (
                    self.sumber_tunda.usulan_id
                    and self.sumber_tunda.usulan.status not in ('disetujui', 'selesai')
                )
            ):
                raise ValidationError('Sumber cuti tunda harus sudah disetujui.')

    def __str__(self):
        return f'Klaim {self.jumlah_hari_diklaim} hari dari {self.sumber_tunda_id} ke {self.cuti_klaim_id}'
    
    
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
    berlaku_sd_str = models.DateField(
        null=True,
        blank=True,
        verbose_name='STR berlaku s/d',
    )
    str_seumur_hidup = models.BooleanField(
        default=False,
        verbose_name='STR berlaku seumur hidup',
    )
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
