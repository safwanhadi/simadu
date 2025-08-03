from django import forms
from django.forms import inlineformset_factory
from calendar import monthrange, month_name
from datetime import date

from .models import JadwalDinasSDM, JenisSDMPerinstalasi, DaftarKegiatanPegawai, KehadiranKegiatan, DetailKategoriJadwalDinas
from myaccount.models import Users
from strukturorg.models import UnitInstalasi
from dokumen.models import RiwayatPenempatan
from .models import HariLibur

bootstrap_col = 'form-control col-md-12'

class HariLiburForm(forms.ModelForm):
    class Meta:
        model = HariLibur
        fields = ('tanggal', 'keterangan')
        
    def __init__(self, *args, **kwargs):
        super(HariLiburForm, self).__init__(*args, **kwargs)
        self.fields['tanggal'].widget = forms.DateInput(attrs={'type':'date'})
    

def jumlah_hari_dalam_bulan():
    tanggal = date.today()
    bulan : int = tanggal.month
    tahun : int  = tanggal.year
    hari_pertama, jumlah_hari = monthrange(tahun, bulan)
    return jumlah_hari

class SearchForm(forms.Form):
    q = forms.CharField(max_length=100)
    
    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        self.fields['q'].label = ''
        self.fields['q'].widget = forms.TextInput(attrs={'placeholder':'Text Pencarian ...'})
        

class JenisSDMPerinstalasiBasicForm(forms.ModelForm):
    pegawai = forms.ModelChoiceField(queryset=Users.objects.none())
    class Meta:
        model = JenisSDMPerinstalasi
        fields = ('pegawai', 'jenis_sdm', 'instalasi')
        
    def set_safe_queryset(self, field_name, model):
        if self.instance and self.instance.pegawai:
            self.fields[field_name].queryset = model.objects.filter(pk=self.instance.pegawai.pk)
        # Saat form create (POST request), kita set queryset agar validasi tidak error
        elif field_name in self.data:
            try:
                # Ambil id dari POST
                pk = self.data.get(field_name)
                self.fields[field_name].queryset = model.objects.filter(pk=pk)
            except (ValueError, TypeError):
                # ID tidak valid, lewati
                pass
        else:
            self.fields[field_name].queryset = model.objects.none()
            
    def __init__(self, *args, **kwargs):
        super(JenisSDMPerinstalasiBasicForm, self).__init__(*args, **kwargs)
        self.fields['pegawai'].label = 'Nama Pegawai'
        self.set_safe_queryset('pegawai', Users)
        self.fields['jenis_sdm'].label = 'Profesi'


class PengajuanJadwalForm(forms.ModelForm):
    class Meta:
        model = JenisSDMPerinstalasi
        fields = ('jenis_sdm', 'pegawai', 'unor', 'bidang', 'sub_bidang', 'instalasi', 'bulan', 'tahun', 'status')
    def __init__(self, *args, **kwargs):
        super(PengajuanJadwalForm, self).__init__(*args, **kwargs)
        self.fields['jenis_sdm'].widget = forms.HiddenInput()
        self.fields['pegawai'].widget = forms.HiddenInput()
        self.fields['unor'].widget = forms.HiddenInput()
        self.fields['bidang'].widget = forms.HiddenInput()
        self.fields['sub_bidang'].widget = forms.HiddenInput()
        self.fields['instalasi'].widget = forms.HiddenInput()
        self.fields['bulan'].widget = forms.HiddenInput()
        self.fields['tahun'].widget = forms.HiddenInput()
        self.fields['status'].widget = forms.HiddenInput()


class JenisSDMPerinstalasiForm(forms.ModelForm):
    class Meta:
        model = JenisSDMPerinstalasi
        fields = ('jenis_sdm', 'pegawai', 'unor', 'bidang', 'sub_bidang', 'instalasi', 'bulan', 'tahun')
    def __init__(self, *args, **kwargs):
        super(JenisSDMPerinstalasiForm, self).__init__(*args, **kwargs)
        self.fields['jenis_sdm'].widget = forms.HiddenInput()
        self.fields['pegawai'].widget = forms.HiddenInput()
        self.fields['unor'].widget = forms.HiddenInput()
        self.fields['bidang'].widget = forms.HiddenInput()
        self.fields['sub_bidang'].widget = forms.HiddenInput()
        self.fields['instalasi'].widget = forms.HiddenInput()
        self.fields['bulan'].widget = forms.HiddenInput()
        self.fields['tahun'].widget = forms.HiddenInput()


class JenisSDMPerinstalasiCustomForm(forms.ModelForm):
    tanggal = forms.CharField(widget=forms.TextInput(attrs={type:'date'}), required=False)
    class Meta:
        model = JenisSDMPerinstalasi
        fields = ('jenis_sdm', 'pegawai', 'unor', 'bidang', 'sub_bidang', 'instalasi', 'bulan', 'tahun')
    def __init__(self, *args, **kwargs):
        super(JenisSDMPerinstalasiCustomForm, self).__init__(*args, **kwargs)
        self.fields['pegawai'].widget = forms.HiddenInput()
        self.fields['jenis_sdm'].widget = forms.HiddenInput()
        self.fields['unor'].widget = forms.HiddenInput()
        self.fields['bidang'].widget = forms.HiddenInput()
        self.fields['sub_bidang'].widget = forms.HiddenInput()
        self.fields['instalasi'].widget = forms.HiddenInput()
        self.fields['bulan'].widget = forms.HiddenInput()
        self.fields['tahun'].widget = forms.HiddenInput()
        

class JadwalDinasForm(forms.ModelForm):
    class Meta:
        model = JadwalDinasSDM
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(JadwalDinasForm, self).__init__(*args, **kwargs)
        self.fields['tanggal'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['kategori_jadwal'].widget.attrs['class'] = bootstrap_col
        self.fields['kategori_jadwal'].queryset = DetailKategoriJadwalDinas.objects.all()


jadwal_formset = inlineformset_factory(
    JenisSDMPerinstalasi, 
    JadwalDinasSDM, 
    JadwalDinasForm, 
    extra=1, 
    can_delete=True
)
update_jadwal_formset = inlineformset_factory(
    JenisSDMPerinstalasi, 
    JadwalDinasSDM, 
    JadwalDinasForm, 
    extra=0,
    can_delete=True
)

def pegawai_list(tanggal):
    data_user = Users.objects.filter(
        jenissdmperinstalasi__jadwaldinassdm__tanggal__day = tanggal.day,
        jenissdmperinstalasi__jadwaldinassdm__tanggal__month = tanggal.month,
        jenissdmperinstalasi__jadwaldinassdm__tanggal__year = tanggal.year,
    ).exclude(is_superuser=True, is_active=False)
    return data_user

def instalasi(pegawai):
    instalasi = pegawai.riwayatpenempatan_set.filter(status=True).first()
    return instalasi
    
class SalinJadwalForm(forms.Form):
    instalasi = forms.ModelChoiceField(queryset=RiwayatPenempatan.objects.none())
    sumber = forms.ModelChoiceField(queryset=Users.objects.none(), label="Salin dari Pegawai")
    tujuan = forms.ModelChoiceField(queryset=Users.objects.none(), label="Salin ke Pegawai")
    bulan = forms.IntegerField()
    tahun = forms.IntegerField()
    
    def set_safe_queryset(self, field_name, model):
        if self.instance and self.instance[field_name]:
            self.fields[field_name].queryset = model.objects.filter(pk=self.instance[field_name].pk)
        # Saat form create (POST request), kita set queryset agar validasi tidak error
        elif field_name in self.data:
            try:
                # Ambil id dari POST
                pk = self.data.get(field_name)
                self.fields[field_name].queryset = model.objects.filter(pk=pk)
            except (ValueError, TypeError):
                # ID tidak valid, lewati
                pass
        else:
            self.fields[field_name].queryset = model.objects.none()

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super(SalinJadwalForm, self).__init__(*args, **kwargs)
        self.fields['instalasi'].widget=forms.HiddenInput()
        self.fields['sumber'].widget = forms.HiddenInput()
        self.fields['tujuan'].widget = forms.HiddenInput()
        self.fields['bulan'].widget = forms.HiddenInput()
        self.fields['tahun'].widget = forms.HiddenInput()
        self.set_safe_queryset('sumber', Users)
        self.set_safe_queryset('tujuan', Users)
        self.set_safe_queryset('instalasi', RiwayatPenempatan)
            
        
    def clean(self):
        cleaned = super().clean()
        if cleaned.get("sumber") == cleaned.get("tujuan"):
            raise forms.ValidationError("Pegawai sumber dan tujuan tidak boleh sama.")
        return cleaned


class SalinJadwalInstalasiForm(forms.Form):
    instalasi = forms.ModelChoiceField(
        queryset=UnitInstalasi.objects.all(),
        label="Instalasi"
    )
    bulan_sumber = forms.ChoiceField(
        label="Bulan Sumber",
        choices=[(i, month_name[i]) for i in range(1, 13)]
    )
    tahun_sumber = forms.IntegerField(label="Tahun Sumber", initial=date.today().year)

    bulan = forms.ChoiceField(
        label="Bulan Tujuan",
        choices=[(i, month_name[i]) for i in range(1, 13)]
    )
    tahun = forms.IntegerField(label="Tahun Tujuan", initial=date.today().year)
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(SalinJadwalInstalasiForm, self).__init__(*args, **kwargs)
        if self.user.is_staff and hasattr(self.user, 'profil_admin') and self.user.profil_admin.instalasi.exists():
            self.fields['instalasi'].queryset = UnitInstalasi.objects.filter(pk__in=self.user.profil_admin.instalasi.values_list('pk', flat=True))
        elif self.user.is_staff and hasattr(self.user, 'profil_admin') and self.user.profil_admin.sub_bidang:
            self.fields['instalasi'].queryset = UnitInstalasi.objects.filter(sub_bidang=self.user.profil_admin.sub_bidang)
        elif self.user.is_staff and hasattr(self.user, 'profil_admin') and self.user.profil_admin.bidang:
            self.fields['instalasi'].queryset = UnitInstalasi.objects.filter(sub_bidang__bidang=self.user.profil_admin.bidang)

    def clean(self):
        cleaned = super().clean()
        if (
            cleaned.get("bulan_sumber") == cleaned.get("bulan")
            and cleaned.get("tahun_sumber") == cleaned.get("tahun")
        ):
            raise forms.ValidationError("Bulan dan tahun sumber tidak boleh sama dengan tujuan.")
        return cleaned


STATUS_CHOICES = [
    ('disetujui', 'Setujui Pengajuan'),
    ('ditolak', 'Tolak Pengajuan')
]

class PersetujuanForm(forms.Form):
    alasan = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Alasan penolakan (jika ada)'}), label='Alasan Penolakan (opsional, jika ingin menolak jadwal):')


class DaftarKegiatanPegawaiForm(forms.ModelForm):
    class Meta:
        model = DaftarKegiatanPegawai
        fields = ('pegawai', 'jenis_sdm', 'unor', 'bidang', 'sub_bidang', 'instalasi', 'bulan', 'tahun', 'kegiatan')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.tanggal = kwargs.pop('tanggal', None)
        super(DaftarKegiatanPegawaiForm, self).__init__(*args, **kwargs)
        if self.request and self.request.user.is_superuser:
            self.fields['pegawai'].queryset = pegawai_list(self.tanggal)
        else:
            self.fields['pegawai'].initial = Users.objects.filter(pk=self.request.user.pk)
            self.fields['pegawai'].widget = forms.HiddenInput()
        if self.instance and self.instance.pk:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['pegawai'].queryset = Users.objects.filter(pk=self.instance.pegawai.pk)
            self.fields['kegiatan'].widget = forms.HiddenInput()
        self.fields['jenis_sdm'].widget = forms.HiddenInput()
        self.fields['unor'].widget = forms.HiddenInput()
        self.fields['bidang'].widget = forms.HiddenInput()
        self.fields['sub_bidang'].widget = forms.HiddenInput()
        self.fields['instalasi'].widget = forms.HiddenInput()
        self.fields['bulan'].widget = forms.HiddenInput()
        self.fields['tahun'].widget = forms.HiddenInput()
        
    def save(self, commit=True):
        instance = super(DaftarKegiatanPegawaiForm, self).save(commit=False)
        pegawai = self.cleaned_data.get('pegawai')
        instance.jenis_sdm = pegawai.jenissdmperinstalasi_set.last().jenis_sdm if pegawai.jenissdmperinstalasi_set.exists() else None
        instance.unor = pegawai.jenissdmperinstalasi_set.last().unor if pegawai.jenissdmperinstalasi_set.exists() else None
        instance.bidang = pegawai.jenissdmperinstalasi_set.last().bidang if pegawai.jenissdmperinstalasi_set.exists() else None
        instance.sub_bidang = pegawai.jenissdmperinstalasi_set.last().sub_bidang if pegawai.jenissdmperinstalasi_set.exists() else None
        instance.instalasi = pegawai.jenissdmperinstalasi_set.last().instalasi if pegawai.jenissdmperinstalasi_set.exists() else None
        instance.bulan = self.tanggal.month
        instance.tahun = self.tanggal.year
        instance.save()
        return instance


class KehadiranKegiatanForm(forms.ModelForm):
    class Meta:
        model = KehadiranKegiatan
        fields = ('pegawai', 'tanggal', 'ket', 'status_ketepatan', 'alasan', 'hadir')

    def __init__(self, *args, **kwargs):
        super(KehadiranKegiatanForm, self).__init__(*args, **kwargs)
        self.fields['tanggal'].widget = forms.TextInput(attrs={'type':'datetime-local', 'class':bootstrap_col})
        self.fields['ket'].widget = forms.TextInput(attrs={'type':'text', 'class':bootstrap_col, 'style':"width:300px"})
        self.fields['alasan'].widget.attrs['class'] = bootstrap_col
        self.fields['hadir'].widget.attrs['class'] = bootstrap_col
        self.fields['status_ketepatan'].label = 'Terlambat?'
        self.fields['status_ketepatan'].widget.attrs['class'] = bootstrap_col

kehadiran_formset = inlineformset_factory(DaftarKegiatanPegawai, KehadiranKegiatan, KehadiranKegiatanForm, extra=1, can_delete=True)
update_kehadiran_formset = inlineformset_factory(DaftarKegiatanPegawai, KehadiranKegiatan, KehadiranKegiatanForm, extra=0, )


class FormCopyJadwalSDM(forms.ModelForm):
    jadwaldinassdm = forms.ModelMultipleChoiceField(queryset=JenisSDMPerinstalasi.objects.all())
    class Meta:
        model = JenisSDMPerinstalasi
        fields = ('jadwaldinassdm',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.bulan = kwargs.pop('bulan', None)
        self.tahun = kwargs.pop('tahun', None)
        self.unor = kwargs.pop('unor', None)
        self.bidang = kwargs.pop('bidang', None)
        self.sub_bidang = kwargs.pop('sub_bidang', None)
        self.instalasi = kwargs.pop('instalasi', None)
        super(FormCopyJadwalSDM, self).__init__(*args, **kwargs)
        if self.request and self.request.user.is_superuser:
            self.fields['jadwaldinassdm'] = forms.ModelMultipleChoiceField(queryset=JenisSDMPerinstalasi.objects.filter(jadwaldinassdm__isnull=True, bulan=self.bulan, tahun=self.tahun))
        elif self.request and self.request.user.is_staff and self.instalasi:
            self.fields['jadwaldinassdm'] = forms.ModelMultipleChoiceField(queryset=JenisSDMPerinstalasi.objects.filter(jadwaldinassdm__isnull=True, bulan=self.bulan, tahun=self.tahun, instalasi=self.instalasi))
        elif self.request and self.request.user.is_staff and self.sub_bidang:
            self.fields['jadwaldinassdm'] = forms.ModelMultipleChoiceField(queryset=JenisSDMPerinstalasi.objects.filter(jadwaldinassdm__isnull=True, bulan=self.bulan, tahun=self.tahun, sub_bidang=self.sub_bidang))
        elif self.request and self.request.user.is_staff and self.bidang:
            self.fields['jadwaldinassdm'] = forms.ModelMultipleChoiceField(queryset=JenisSDMPerinstalasi.objects.filter(jadwaldinassdm__isnull=True, bulan=self.bulan, tahun=self.tahun, bidang=self.bidang))
        elif self.request and self.request.user.is_staff and self.unor:
            self.fields['jadwaldinassdm'] = forms.ModelMultipleChoiceField(queryset=JenisSDMPerinstalasi.objects.filter(jadwaldinassdm__isnull=True, bulan=self.bulan, tahun=self.tahun, unor=self.unor))
        self.fields['jadwaldinassdm'].widget.attrs['class'] = 'sdm'
        self.fields['jadwaldinassdm'].label = ''
        
        
class UploadFingerprintForm(forms.Form):
    file = forms.FileField(
        label = 'Upload File Fingerprint',
        help_text = 'Upload file fingerprint dalam format excel (.xlsx) Pastikan file sesuai dengan template yang telah disediakan.',
        widget = forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx'}),
        error_messages={
            'invalid': 'Format file tidak valid. Pastikan file yang diupload adalah file Excel (.xlsx).',
            'required': 'File fingerprint harus diupload.'
        }
    )
    
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        
        if file:
            if not file.name.endswith('.xlsx'):
                raise forms.ValidationError('File harus dalam format Excel (.xlsx).')
            if file.size > 5 * 1024 * 1024:  # 5 MB
                raise forms.ValidationError('Ukuran file terlalu besar. Maksimal 5 MB.')
            
            
