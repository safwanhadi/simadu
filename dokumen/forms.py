from django import forms
from django.forms import modelformset_factory, inlineformset_factory
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timezone

from strukturorg.models import (
    UnitOrganisasi, Bidang, SubBidang, UnitInstalasi
)
from myaccount.models import Users
from jenissdm.models import JenisSDM
from .models import (
    DokumenSDM,
    RiwayatPendidikan, 
    RiwayatPengangkatan,
    RiwayatBekerja,
    RiwayatPenempatan,
    RiwayatProfesi,
    RiwayatSIPProfesi,
    RiwayatPanggol,
    RiwayatJabatan,
    UjiKompetensi,
    Kompetensi,
    RiwayatGajiBerkala,
    RiwayatKinerja,
    RiwayatOrganisasi,
    RiwayatDiklat,
    RiwayatCuti,
    RiwayatHukuman,
    RiwayatPenghargaan,
    RiwayatKeluarga,
    OrangTua,
    Pasangan,
    Anak,
    JenjangJafung,
    JENIS_JABATAN,
    RiwayatInovasi,
    RiwayatPenugasan
    )


def get_date_from_string(tanggal):
    tanggal_sekarang = date.today()
    try:
        get_tanggal = datetime.strptime(tanggal, "%Y-%m-%d").date()
        return get_tanggal
    except Exception:
        return tanggal_sekarang

bootstrap_col = 'form-control col-md-12'

class RiwayatPendidikanForm(forms.ModelForm):
    class Meta:
        model = RiwayatPendidikan
        fields = ('pegawai', 'dokumen', 'level_pend', 'pendidikan', 
                  'nama_sek', 'tgl_lulus', 'no_ijazah', 'gelar_depan', 'gelar_belakang', 'file_ijazah', 'file_transkrip')
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatPendidikanForm, self).__init__(*args, **kwargs)
        self.fields['level_pend'].widget.attrs['class'] = bootstrap_col
        self.fields['level_pend'].label = "Level Pendidikan"
        self.fields['tgl_lulus'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['nama_sek'].label = "Nama Sekolah/Universitas"
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()


class UrutkanDokumenSDMForm(forms.ModelForm):
    class Meta:
        model = DokumenSDM
        fields = ('nama', )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(UrutkanDokumenSDMForm, self).__init__(*args, **kwargs)
        self.fields['nama'].widget=forms.HiddenInput()


class UrutkanRiwayatPendidikanForm(forms.ModelForm):
    class Meta:
        model = RiwayatPendidikan
        fields = ('no_urut_dokumen', 'level_pend', 'pendidikan')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(UrutkanRiwayatPendidikanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['level_pend'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['pendidikan'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_pendidikan = inlineformset_factory(DokumenSDM, RiwayatPendidikan, UrutkanRiwayatPendidikanForm, extra=0, can_delete=False)

class RiwayatPengangkatanForm(forms.ModelForm):
    class Meta:
        model = RiwayatPengangkatan
        fields = ('pegawai', 'dokumen', 'status_pegawai', 'no_srt_putusan', 'tgl_srt_putusan', 'tmt_pegawai', 'pejabat_pelantik',
                  'no_srt_spmt', 'tgl_srt_spmt', 'no_srt_latsar', 'tgl_srt_latsar', 'karpeg', 'file_sk', 'file_spmt', 'file_latsar', 'file_karpeg')
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatPengangkatanForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
        self.fields['tgl_srt_putusan'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tmt_pegawai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_srt_spmt'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_srt_latsar'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        

class UrutkanRiwayaPengangkatanForm(forms.ModelForm):
    class Meta:
        model = RiwayatPengangkatan
        fields = ('no_urut_dokumen', 'status_pegawai', 'tgl_srt_putusan')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayaPengangkatanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['status_pegawai'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_srt_putusan'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_pengangkatan = inlineformset_factory(DokumenSDM, RiwayatPengangkatan, UrutkanRiwayaPengangkatanForm, extra=0, can_delete=False)


class RiwayatBekerjaForm(forms.ModelForm):
    class Meta:
        model = RiwayatBekerja
        fields = ('pegawai', 'dokumen', 'nama_instansi', 'jabatan', 'no_sk', 'tgl_sk', 'tgl_mulai', 'tgl_selesai', 'file')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatBekerjaForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
        self.fields['tgl_sk'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_mulai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_selesai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        
class UrutkanRiwayatBekerjaForm(forms.ModelForm):
    class Meta:
        model = RiwayatBekerja
        fields = ('no_urut_dokumen', 'nama_instansi', 'jabatan')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatBekerjaForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['nama_instansi'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['jabatan'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_bekerja = inlineformset_factory(DokumenSDM, RiwayatBekerja, UrutkanRiwayatBekerjaForm, extra=0, can_delete=False)


class RiwayatPenempatanForm(forms.ModelForm):
    class Meta:
        model = RiwayatPenempatan
        fields = ('pegawai', 'dokumen', 'penempatan_level1', 'penempatan_level2', 'penempatan_level3', 'penempatan_level4', 'no_sk', 'tgl_sk', 'status', 'file')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatPenempatanForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget.attrs['hidden'] = 'hidden'
            self.fields['dokumen'].widget.attrs['hidden'] = 'hidden'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
        self.fields['tgl_sk'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['status'].label = 'Centang jika pegawai aktif dan berada diinstalasi ini'

class UrutkanRiwayatPenempatanForm(forms.ModelForm):
    class Meta:
        model = RiwayatPenempatan
        fields = ('no_urut_dokumen', 'penempatan_level4', 'penempatan_level3')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatPenempatanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['penempatan_level4'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['penempatan_level3'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_penempatan = inlineformset_factory(DokumenSDM, RiwayatPenempatan, UrutkanRiwayatPenempatanForm, extra=0, can_delete=False)

class RiwayatPenempatanLainnyaForm(forms.ModelForm):
    class Meta:
        model = RiwayatPenempatan
        fields = ('pegawai', 'dokumen', 'instansi_sebelumnya', 'bidang_sebelumnya', 'seksi_sebelumnya', 'unit_sebelumnya', 'no_sk', 'tgl_sk', 'status', 'file')

    def __init__(self, *args, **kwargs):
        self.pegawai=kwargs.pop("pegawai", None)
        super(RiwayatPenempatanLainnyaForm, self).__init__(*args, **kwargs)
        if self.pegawai and not self.pegawai.is_superuser:
            self.fields['pegawai'].widget.attrs['hidden'] = 'hidden'
            self.fields['dokumen'].widget.attrs['hidden'] = 'hidden'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
            self.fields['status'].widget = forms.HiddenInput()
        self.fields['tgl_sk'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})

class UrutkanRiwayatPenempatanLainnyaForm(forms.ModelForm):
    class Meta:
        model = RiwayatPenempatan
        fields = ('no_urut_dokumen', 'seksi_sebelumnya', 'bidang_sebelumnya')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatPenempatanLainnyaForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['seksi_sebelumnya'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['bidang_sebelumnya'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_penempatan_lainnya = inlineformset_factory(DokumenSDM, RiwayatPenempatan, UrutkanRiwayatPenempatanLainnyaForm, extra=0, can_delete=False)

class RiwayatProfesiForm(forms.ModelForm):
    class Meta:
        model = RiwayatProfesi
        fields = ('pegawai', 'dokumen', 'profesi', 'no_str', 'tgl_str', 'file_str')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatProfesiForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()
        self.fields['tgl_str'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})

class UrutkanRiwayatProfesiForm(forms.ModelForm):
    class Meta:
        model = RiwayatProfesi
        fields = ('no_urut_dokumen', 'profesi', 'tgl_str')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatProfesiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['profesi'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_str'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_profesi = inlineformset_factory(DokumenSDM, RiwayatProfesi, UrutkanRiwayatProfesiForm, extra=0, can_delete=False)


class RiwayatSIPProfesiForm(forms.ModelForm):
    class Meta:
        model = RiwayatSIPProfesi
        fields = ('riwayat_profesi', 'no_sip', 'tgl_sip', 'berlaku_sd', 'file_sip')

    def __init__(self, *args, **kwargs):
        super(RiwayatSIPProfesiForm, self).__init__(*args, **kwargs)
        self.fields['tgl_sip'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['berlaku_sd'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        initial = kwargs.get('initial')
        if initial and initial.get('riwayat_profesi') or self.instance:
            self.fields['riwayat_profesi'].widget = forms.HiddenInput()

profesi_formset = inlineformset_factory(RiwayatProfesi, RiwayatSIPProfesi, RiwayatSIPProfesiForm, fields='__all__', extra=1)
profesi_update_formset = inlineformset_factory(RiwayatProfesi, RiwayatSIPProfesi, RiwayatSIPProfesiForm, fields='__all__', extra=0)


class UrutkanRiwayatProfesiForm(forms.ModelForm):
    class Meta:
        model = RiwayatProfesi
        fields = ('no_str', )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(UrutkanRiwayatProfesiForm, self).__init__(*args, **kwargs)
        self.fields['no_str'].widget=forms.HiddenInput()


class UrutkanRiwayatSIPProfesiForm(forms.ModelForm):
    class Meta:
        model = RiwayatSIPProfesi
        fields = ('no_urut_dokumen', 'no_sip', 'tgl_sip')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatSIPProfesiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['no_sip'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_sip'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_sip = inlineformset_factory(RiwayatProfesi, RiwayatSIPProfesi, UrutkanRiwayatSIPProfesiForm, extra=0, can_delete=False)


class RiwayatPanggolForm(forms.ModelForm):
    class Meta:
        model = RiwayatPanggol
        fields = ('pegawai', 'dokumen', 'panggol', 'masa_kerja_tahun', 'masa_kerja_bulan', 'tmt_gol', 'no_sk', 'tgl_sk', 
                  'no_pertek_bkn', 'tgl_pertek_bkn', 'file')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatPanggolForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget.attrs['hidden'] = 'hidden'
            self.fields['dokumen'].widget.attrs['hidden'] = 'hidden'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
        self.fields['tmt_gol'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_sk'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_pertek_bkn'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})

class UrutkanRiwayatPanggolForm(forms.ModelForm):
    class Meta:
        model = RiwayatPanggol
        fields = ('no_urut_dokumen', 'panggol', 'tmt_gol')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatPanggolForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['panggol'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tmt_gol'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_panggol = inlineformset_factory(DokumenSDM, RiwayatPanggol, UrutkanRiwayatPanggolForm, extra=0, can_delete=False)


class UjiKompetensiForm(forms.ModelForm):
    class Meta:
        model = UjiKompetensi
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(UjiKompetensiForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()


class KompetensiForm(forms.ModelForm):
    class Meta:
        model = Kompetensi
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop('request', None)
        super(KompetensiForm, self).__init__(*args, **kwargs)
        self.fields['tgl_sert_komp'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['berlaku_sd'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        if not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()

class UrutkanKompetensiForm(forms.ModelForm):
    class Meta:
        model = Kompetensi
        fields = ('no_urut_dokumen', 'kompetensi', 'tgl_sert_komp')

    def __init__(self, *args, **kwargs):
        super(UrutkanKompetensiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['kompetensi'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_sert_komp'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_kompetensi = inlineformset_factory(DokumenSDM, Kompetensi, UrutkanKompetensiForm, extra=0, can_delete=False)


class RiwayatJabatanForm(forms.ModelForm):
    kompetensi = forms.ModelMultipleChoiceField(queryset=Kompetensi.objects.all())
    class Meta:
        model = RiwayatJabatan
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop('request', None)
        super(RiwayatJabatanForm, self).__init__(*args, **kwargs)
        self.fields['kompetensi'].widget.attrs['class'] = 'jabatan'
        self.fields['kompetensi'].required = False
        self.fields['tmt_jabatan'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tmt_pelantikan'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_srt_pemberhentian'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_sk'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()
            self.fields['kompetensi'] = forms.ModelMultipleChoiceField(queryset=Kompetensi.objects.filter(pegawai=self.request.user))
            self.fields['kompetensi'].widget.attrs['class'] = 'jabatan'
            self.fields['kompetensi'].required = False

    def save(self, commit=True):
        jafung = super().save(commit=False)
        if self.cleaned_data['kompetensi']:
            jafung.kompetensi.set(self.cleaned_data['kompetensi'])
        jafung.save()
        return jafung

class UrutkanRiwayatJabatanForm(forms.ModelForm):
    class Meta:
        model = RiwayatJabatan
        fields = ('no_urut_dokumen', 'nama_jabatan', 'detail_nama_jabatan')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatJabatanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['nama_jabatan'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['detail_nama_jabatan'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_jabatan = inlineformset_factory(DokumenSDM, RiwayatJabatan, UrutkanRiwayatJabatanForm, extra=0, can_delete=False)


class RiwayatJabatanAdminForm(forms.ModelForm):
    class Meta:
        model = RiwayatJabatan
        fields = '__all__'

    kompetensi = forms.ModelMultipleChoiceField(queryset=Kompetensi.objects.all())


class RiwayatGajiBerkalaForm(forms.ModelForm):
    no_srt_gaji = forms.CharField(required=True)
    tgl_srt_gaji = forms.CharField(required=True)
    class Meta:
        model = RiwayatGajiBerkala
        fields = ('pegawai', 'dokumen', 'no_srt_gaji', 'tgl_srt_gaji', 'gaji_pkk', 'tmt_gaji', 'pangkat', 'tempat_kerja', 'masa_kerja_tahun', 'masa_kerja_bulan', 
                  'pertek', 'ket', 'file')
        
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        self.action = kwargs.pop("action", None)
        super(RiwayatGajiBerkalaForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()
            self.fields['pangkat'] = forms.ModelChoiceField(queryset=RiwayatPanggol.objects.filter(pegawai=self.request.user))
            self.fields['tempat_kerja'] = forms.ModelChoiceField(queryset=RiwayatPenempatan.objects.filter(pegawai=self.request.user))
        self.fields['tgl_srt_gaji'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tmt_gaji'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        if self.action == 'upload':
            self.fields['no_srt_gaji'].widget = forms.HiddenInput()
            self.fields['tgl_srt_gaji'].widget = forms.HiddenInput()
            self.fields['gaji_pkk'].widget = forms.HiddenInput()
            self.fields['tmt_gaji'].widget = forms.HiddenInput()
            self.fields['masa_kerja_tahun'].widget = forms.HiddenInput()
            self.fields['masa_kerja_bulan'].widget = forms.HiddenInput()
            self.fields['pertek'].widget = forms.HiddenInput()
            self.fields['ket'].widget = forms.HiddenInput()
            self.fields['pangkat'].widget = forms.HiddenInput()
            self.fields['tempat_kerja'].widget = forms.HiddenInput()


class UrutkanRiwayatGajiBerkalaForm(forms.ModelForm):
    class Meta:
        model = RiwayatGajiBerkala
        fields = ('no_urut_dokumen', 'gaji_pkk', 'tmt_gaji')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatGajiBerkalaForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['gaji_pkk'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tmt_gaji'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_berkala = inlineformset_factory(DokumenSDM, RiwayatGajiBerkala, UrutkanRiwayatGajiBerkalaForm, extra=0, can_delete=False)


class RiwayatKinerjaForm(forms.ModelForm):
    class Meta:
        model = RiwayatKinerja
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatKinerjaForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()
        self.fields['periode_kinerja_awal'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['periode_kinerja_akhir'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class UrutkanRiwayatKinerjaForm(forms.ModelForm):
    class Meta:
        model = RiwayatKinerja
        fields = ('no_urut_dokumen', 'hasil_kinerja', 'prilaku_kinerja')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatKinerjaForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['hasil_kinerja'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['prilaku_kinerja'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_kinerja = inlineformset_factory(DokumenSDM, RiwayatKinerja, UrutkanRiwayatKinerjaForm, extra=0, can_delete=False)


class RiwayatOrganisasiForm(forms.ModelForm):
    class Meta:
        model = RiwayatOrganisasi
        fields = ('pegawai', 'dokumen', 'nama_org', 'jabatan', 'no_anggota', 'tgl_gabung', 'tgl_keluar', 'file')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatOrganisasiForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
        self.fields['tgl_gabung'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_keluar'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class UrutkanRiwayatOrganisasiForm(forms.ModelForm):
    class Meta:
        model = RiwayatOrganisasi
        fields = ('no_urut_dokumen', 'nama_org', 'jabatan')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatOrganisasiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['nama_org'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['jabatan'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_organisasi = inlineformset_factory(DokumenSDM, RiwayatOrganisasi, UrutkanRiwayatOrganisasiForm, extra=0, can_delete=False)


class FormUsulanRiwayatDiklat(forms.ModelForm):
    pegawai = forms.ModelMultipleChoiceField(
        queryset=Users.objects.filter(is_active=True), 
        widget=forms.SelectMultiple(attrs={'class': 'pegawai'}),
        required=False
    )
    class Meta:
        model = RiwayatDiklat
        fields = ('pegawai', 'dokumen', 'jenis_diklat', 'nama_diklat', 'penyelenggara', 'metode', 'usulan', 'tgl_mulai', 'tgl_selesai', 'skp')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(FormUsulanRiwayatDiklat, self).__init__(*args, **kwargs)
        self.fields['jenis_diklat'].help_text = 'jenis diklat: Seminar/Workshop/Pelatihan/Pertemuan Ilmiah/FGD, dll.'
        self.fields['tgl_mulai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_selesai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['usulan'].widget=forms.HiddenInput()
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].label = ''#form disembunyikan menggunakan jquery di template
            self.fields['dokumen'].widget=forms.HiddenInput()
        elif self.request and self.request.user.is_superuser:
            self.fields['pegawai'].widget.attrs['class'] = 'select2'
            
            
class FormPenugasanDiklat(forms.ModelForm):
    pegawai = forms.ModelMultipleChoiceField(
        queryset=Users.objects.filter(is_active=True), 
        widget=forms.SelectMultiple(attrs={'class': 'select2'})
    )
    class Meta:
        model = RiwayatDiklat
        fields = ('pegawai', 'dokumen', 'jenis_diklat', 'nama_diklat', 'penyelenggara', 'metode', 'tgl_mulai', 'tgl_selesai', 'skp')

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(FormPenugasanDiklat, self).__init__(*args, **kwargs)
        if request.user.is_superuser:
            self.fields['pegawai'].queryset = Users.objects.filter(riwayatpenempatan__status=True
            ).distinct()
        elif request is not None and request.user.is_staff:
            penempatan_admin = request.user.riwayatpenempatan_set.filter(status=True).last()
            penempatan = penempatan_admin.penempatan if hasattr(penempatan_admin, 'penempatan') else None
            self.fields['pegawai'].queryset = Users.objects.filter(
                riwayatpenempatan__penempatan_level3__sub_bidang=penempatan, riwayatpenempatan__status=True
            ).distinct()|Users.objects.filter(
                riwayatpenempatan__penempatan_level2__bidang=penempatan, riwayatpenempatan__status=True
            ).distinct()
        self.fields['jenis_diklat'].help_text = 'jenis diklat: Seminar/Workshop/Pelatihan/Pertemuan Ilmiah/FGD, dll.'
        self.fields['tgl_mulai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_selesai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['dokumen'].widget=forms.HiddenInput()


class FormAlihanRiwayatDiklat(forms.ModelForm):
    pegawai = forms.ModelMultipleChoiceField(queryset=Users.objects.filter(is_active=True), widget=forms.SelectMultiple(attrs={'class': 'select2'}))
    class Meta:
        model = RiwayatDiklat
        fields = ('pegawai', 'dokumen', 'jenis_diklat', 'nama_diklat', 'penyelenggara', 'metode', 'tgl_mulai', 'tgl_selesai', 'skp')

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(FormAlihanRiwayatDiklat, self).__init__(*args, **kwargs)
        if request is not None and request.user.is_staff and not request.user.is_superuser:
            penempatan_admin = request.user.riwayatpenempatan_set.filter(status=True).last()
            self.fields['pegawai'].queryset = Users.objects.filter(
                riwayatpenempatan__penempatan_level3__sub_bidang=penempatan_admin.penempatan, riwayatpenempatan__status=True
            ).distinct()|Users.objects.filter(
                riwayatpenempatan__penempatan_level2__bidang=penempatan_admin.penempatan, riwayatpenempatan__status=True
            ).distinct()
        elif request is not None and request.user.is_superuser:
            self.fields['pegawai'].queryset = Users.objects.filter(is_active=True)
        else:
            self.fields['pegawai'].queryset = Users.objects.none()
        self.fields['dokumen'].widget=forms.HiddenInput()
        self.fields['jenis_diklat'].widget=forms.HiddenInput()
        self.fields['nama_diklat'].widget=forms.HiddenInput()
        self.fields['penyelenggara'].widget=forms.HiddenInput()
        self.fields['metode'].widget=forms.HiddenInput()
        self.fields['tgl_mulai'].widget=forms.HiddenInput()
        self.fields['tgl_selesai'].widget=forms.HiddenInput()
        self.fields['skp'].widget=forms.HiddenInput()


class UrutkanRiwayatDiklatForm(forms.ModelForm):
    class Meta:
        model = RiwayatDiklat
        fields = ('no_urut_dokumen', 'nama_diklat', 'tgl_sertifikat')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatDiklatForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['nama_diklat'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_sertifikat'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_diklat = inlineformset_factory(DokumenSDM, RiwayatDiklat, UrutkanRiwayatDiklatForm, extra=0, can_delete=False)


class FormRiwayatDiklatLaporan(forms.ModelForm):
    class Meta:
        model = RiwayatDiklat
        fields = ('pegawai', 'no_sertifikat', 'tgl_sertifikat', 'jam_pelajaran', 'kategori_kompetensi', 'kompetensi', 'periode_berlaku_sertifikat', 'file', 'file_laporan')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(FormRiwayatDiklatLaporan, self).__init__(*args, **kwargs)
        self.fields['tgl_sertifikat'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['file'].required = True
        self.fields['file_laporan'].required = True
        self.fields['tgl_sertifikat'].required = True
        self.fields['no_sertifikat'].required = True
        self.fields['pegawai'].widget.attrs['class']='pegawai'
        self.fields['pegawai'].label = ''
        self.fields['kompetensi'].widget.attrs['class']='select2'

    def save(self, commit=True):
        instance = super().save(commit=False)
        pegawai = self.cleaned_data.get('pegawai')
        instance.no_sertifikat = self.cleaned_data.get('no_sertifikat')
        instance.tgl_sertifikat = self.cleaned_data.get('tgl_sertifikat')
        instance.kompetensi = self.cleaned_data.get('kompetensi')
        instance.periode_berlaku_sertifikat = self.cleaned_data.get('periode_berlaku_sertifikat')
        if instance.tgl_sertifikat is not None:
            berlaku_sd = self.cleaned_data.get('tgl_sertifikat') + relativedelta(months=int(self.cleaned_data.get('periode_berlaku_sertifikat')))
        instance.kategori_kompetensi = self.cleaned_data.get('kategori_kompetensi')
        instance.save()
        if instance.kategori_kompetensi:
            dok = DokumenSDM.objects.filter(url='kompetensi').first()
            for sdm in pegawai:
                if self.instance:
                    data = Kompetensi.objects.filter(pegawai=sdm, kompetensi=instance.kompetensi, no_sert_komp=instance.no_sertifikat)
                    if data:
                        data.update(dokumen=dok, kompetensi=instance.kompetensi, tgl_sert_komp=instance.tgl_sertifikat, masa_berlaku=instance.periode_berlaku_sertifikat, berlaku_sd=berlaku_sd)
                    else:
                        data_kompetensi = Kompetensi(pegawai=sdm, dokumen=dok, kompetensi=instance.kompetensi, no_sert_komp=instance.no_sertifikat, 
                            tgl_sert_komp=instance.tgl_sertifikat, masa_berlaku=instance.periode_berlaku_sertifikat, berlaku_sd=berlaku_sd)
                        data_kompetensi.save()
                else:
                    data_kompetensi = Kompetensi(pegawai=sdm, dokumen=dok, kompetensi=instance.kompetensi, no_sert_komp=instance.no_sertifikat, 
                            tgl_sert_komp=instance.tgl_sertifikat, masa_berlaku=instance.periode_berlaku_sertifikat, berlaku_sd=berlaku_sd)
                    data_kompetensi.save()
        return instance


class RiwayatDiklatForm(forms.ModelForm):
    class Meta:
        model = RiwayatDiklat
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # widget & rules
        date_widget = forms.TextInput(attrs={'type': 'date', 'class': bootstrap_col})
        for f in ('tgl_mulai', 'tgl_selesai', 'tgl_sertifikat'):
            self.fields[f].widget = date_widget

        self.fields['dokumen'].required = False
        self.fields['dokumen'].widget = forms.HiddenInput()

        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.MultipleHiddenInput()
            self.fields['pegawai'].initial = [self.request.user.pk]
            self.fields['no_urut_dokumen'].widget = forms.HiddenInput()

    def save(self, commit=True):
        # ambil instance TANPA menyimpan relasi M2M dulu
        instance = super().save(commit=False)

        # --- tambahkan logika khusus Anda di sini (jika betul‑betul perlu) ---
        if instance.tgl_sertifikat and instance.periode_berlaku_sertifikat:
            # contoh kalkulasi tanggal berlaku sampai
            instance.berlaku_sd = (
                instance.tgl_sertifikat +
                relativedelta(months=int(instance.periode_berlaku_sertifikat))
            )

        # 1) SIMPAN dulu agar dapat id
        if commit:
            instance.save()

        # 2) Tangani relasi M2M *setelah* instance punya pk
        #    cleaned_data['pegawai'] berisi QuerySet/iterable Users
        pegawai_qs = self.cleaned_data.get('pegawai')
        if pegawai_qs is not None:
            instance.pegawai.set(pegawai_qs)

        # 3) Simpan relasi M2M lain yang mungkin dimiliki oleh ModelForm
        if commit:
            self.save_m2m()

        return instance

    
class FormRiwayatDiklatSPT(forms.ModelForm):
    class Meta:
        model = RiwayatDiklat
        fields = ('pegawai', 'dokumen', 'jenis_diklat', 'nama_diklat', 'penyelenggara', 'metode', 'tgl_mulai', 'tgl_selesai', 'skp')
        
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(FormRiwayatDiklatSPT, self).__init__(*args, **kwargs) 
        if self.request is not None and self.request.user.is_superuser:
            self.fields['pegawai'].widget.attrs['class']='pegawai'
            # self.fields['pegawai'].widget.attrs['class']='select2'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].required = False
            self.fields['dokumen'].widget=forms.HiddenInput()
            self.fields['jenis_diklat'].widget=forms.HiddenInput()
            self.fields['nama_diklat'].widget=forms.HiddenInput()
            self.fields['penyelenggara'].widget=forms.HiddenInput()
            self.fields['metode'].widget=forms.HiddenInput()
            self.fields['tgl_mulai'].widget=forms.HiddenInput()
            self.fields['tgl_selesai'].widget=forms.HiddenInput()
            self.fields['skp'].widget=forms.HiddenInput()
        else:
            self.fields['dokumen'].required = False
            self.fields['dokumen'].widget=forms.HiddenInput()
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['jenis_diklat'].widget=forms.HiddenInput()
            self.fields['nama_diklat'].widget=forms.HiddenInput()
            self.fields['penyelenggara'].widget=forms.HiddenInput()
            self.fields['metode'].widget=forms.HiddenInput()
            self.fields['tgl_mulai'].widget=forms.HiddenInput()
            self.fields['tgl_selesai'].widget=forms.HiddenInput()
            self.fields['skp'].widget=forms.HiddenInput()   
        

class FormRiwayatDiklatProses(forms.ModelForm):
    class Meta:
        model = RiwayatDiklat
        fields = ('pegawai', 'dokumen', 'jenis_diklat', 'nama_diklat', 'penyelenggara')

    def __init__(self, case=None, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(FormRiwayatDiklatProses, self).__init__(*args, **kwargs)
        #semua field riwayat diklat dihidden
        self.fields['pegawai'].widget.attrs['class']='pegawai'
        self.fields['pegawai'].label=''
        self.fields['dokumen'].widget=forms.HiddenInput()
        self.fields['jenis_diklat'].widget=forms.HiddenInput() 
        self.fields['nama_diklat'].widget=forms.HiddenInput() 
        self.fields['penyelenggara'].widget=forms.HiddenInput()


class RiwayatCutiForm(forms.ModelForm):
    class Meta:
        model = RiwayatCuti
        fields = ('pegawai', 'dokumen', 'jenis_cuti', 'tgl_mulai_cuti', 'tgl_akhir_cuti', 'lama_cuti', 'domisili_saat_cuti', 
                'no_surat', 'status_cuti', 'tgl_surat', 'file')
        
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatCutiForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget.attrs['hidden'] = 'hidden'
            self.fields['dokumen'].widget.attrs['hidden'] = 'hidden'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
        self.fields['tgl_mulai_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_akhir_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_surat'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        
        
class RiwayatCutiTundaForm(forms.ModelForm):
    class Meta:
        model = RiwayatCuti
        fields = ('pegawai', 'dokumen', 'jenis_cuti', 'tgl_mulai_cuti', 'tgl_akhir_cuti', 'alasan_cuti', 'lama_cuti', 'domisili_saat_cuti', 
                   'status_cuti')
        
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatCutiTundaForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget.attrs['hidden'] = 'hidden'
            self.fields['dokumen'].widget.attrs['hidden'] = 'hidden'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
            self.fields['status_cuti'].widget=forms.HiddenInput()
            self.fields['jenis_cuti'].widget=forms.HiddenInput()
        self.fields['tgl_mulai_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_akhir_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class UrutkanRiwayatCutiForm(forms.ModelForm):
    class Meta:
        model = RiwayatCuti
        fields = ('no_urut_dokumen', 'jenis_cuti')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatCutiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['jenis_cuti'].widget.attrs['class'] = 'form-control col-md-6'

urutkan_dokumen_cuti = inlineformset_factory(DokumenSDM, RiwayatCuti, UrutkanRiwayatCutiForm, extra=0, can_delete=False)


class RiwayatPengajuanCutiForm(forms.ModelForm):
    class Meta:
        model = RiwayatCuti
        fields = ('pegawai', 'dokumen', 'jenis_cuti', 'alasan_cuti', 'tgl_mulai_cuti', 'tgl_akhir_cuti', 'lama_cuti', 'domisili_saat_cuti', 'status_cuti')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)#is_superuser or not
        self.status = kwargs.pop("status", None)#status pengambilan cuti, pengajuan cuti tunda/baru/ambi-tunda
        self.action = kwargs.pop("action", None)#aksi seperti add/edit
        self.case = kwargs.pop("case", None)# case dapat berupa tindaklanjut/tidak ditindaklanjut/selesai, dll
        super(RiwayatPengajuanCutiForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            for field in self.fields.values():
                field.disabled = True
        self.fields['tgl_mulai_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_akhir_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        if self.request and not self.request.user.is_superuser:
            # self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
        if self.status == 'tunda' and self.action == 'add':
            self.fields['jenis_cuti'].widget = forms.HiddenInput()
            self.fields['tgl_mulai_cuti'].widget = forms.HiddenInput()
            self.fields['tgl_akhir_cuti'].widget = forms.HiddenInput()
            self.fields['status_cuti'].widget = forms.HiddenInput()
            self.fields['jenis_cuti'].initial = 'Cuti Tahunan'
            self.fields['status_cuti'].initial = 'Tunda'
        elif self.status == 'baru' and self.action == 'add':
            self.fields['status_cuti'].widget = forms.HiddenInput()
            self.fields['status_cuti'].initial = 'Proses'
        elif self.status == 'ambil-tunda' and self.action == 'add':
            self.fields['jenis_cuti'].widget = forms.HiddenInput()
            self.fields['alasan_cuti'].widget = forms.HiddenInput()
            self.fields['lama_cuti'].widget = forms.HiddenInput()
            self.fields['domisili_saat_cuti'].widget = forms.HiddenInput()
            self.fields['status_cuti'].initial = 'Proses'
        elif self.action == 'edit':
            self.fields['jenis_cuti'].widget = forms.HiddenInput()
            self.fields['status_cuti'].widget = forms.HiddenInput()
        if self.case == 'tindaklanjut':
            self.fields['jenis_cuti'].widget = forms.HiddenInput()
            self.fields['tgl_mulai_cuti'].widget = forms.HiddenInput()
            self.fields['tgl_akhir_cuti'].widget = forms.HiddenInput()
            self.fields['alasan_cuti'].widget = forms.HiddenInput()
            self.fields['lama_cuti'].widget = forms.HiddenInput()
            self.fields['domisili_saat_cuti'].widget = forms.HiddenInput()
            self.fields['status_cuti'].widget = forms.HiddenInput()
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
            

class RiwayatCutiUploadDakungForm(forms.ModelForm):
    class Meta:
        model = RiwayatCuti
        fields = ('pegawai', 'dokumen', 'file_pengajuan', 'file_pendukung')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatCutiUploadDakungForm, self).__init__(*args, **kwargs)
        self.fields['file_pengajuan'].widget.attrs['class'] = bootstrap_col
        self.fields['file_pendukung'].widget.attrs['class'] = bootstrap_col
        self.fields['pegawai'].widget=forms.HiddenInput()
        self.fields['dokumen'].widget=forms.HiddenInput()

    # def clean(self):
    #     file_pendukung = self.cleaned_data.get('file_pendukung')
    #     file_pengajuan = self.cleaned_data.get('file_pengajuan')
    #     file_size = 2.5 * 1024 * 1024
    #     print('file pendukung: ', file_pendukung.size)
    #     print('file_pengajuan: ', file_pengajuan.size)
    #     if file_pendukung.size > file_size or file_pengajuan.size > file_size:  # 5 MB limit
    #         raise forms.ValidationError("Ukuran file tidak boleh melebihi 2,5 MB")
    #     return file_pendukung


class RiwayatCutiUploadSuratForm(forms.ModelForm):
    class Meta:
        model = RiwayatCuti
        fields = ('pegawai', 'dokumen', 'no_surat', 'tgl_surat', 'file')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatCutiUploadSuratForm, self).__init__(*args, **kwargs)
        self.fields['file'].widget.attrs['class'] = bootstrap_col
        self.fields['tgl_surat'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['pegawai'].widget=forms.HiddenInput()
        self.fields['dokumen'].widget=forms.HiddenInput()


class RiwayatHukumanForm(forms.ModelForm):
    class Meta:
        model = RiwayatHukuman
        fields = ('pegawai', 'dokumen', 'jenis_hukuman', 'no_srt_kep', 'tgl_srt_kep', 'hukuman_ke', 'ket', 'file')
    
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatHukumanForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
        self.fields['tgl_srt_kep'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class UrutkanRiwayatHukumanForm(forms.ModelForm):
    class Meta:
        model = RiwayatHukuman
        fields = ('no_urut_dokumen', 'jenis_hukuman', 'tgl_srt_kep')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatHukumanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['jenis_hukuman'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_srt_kep'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_hukuman = inlineformset_factory(DokumenSDM, RiwayatHukuman, UrutkanRiwayatHukumanForm, extra=0, can_delete=False)


class RiwayatPenghargaanForm(forms.ModelForm):
    class Meta:
        model = RiwayatPenghargaan
        fields = ('pegawai', 'dokumen', 'jenis_penghargaan', 'tahun_perolehan', 'no_srt_kep', 'tgl_srt_kep', 'file')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatPenghargaanForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
        self.fields['tgl_srt_kep'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class UrutkanRiwayatPenghargaanForm(forms.ModelForm):
    class Meta:
        model = RiwayatPenghargaan
        fields = ('no_urut_dokumen', 'jenis_penghargaan', 'tgl_srt_kep')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatPenghargaanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['jenis_penghargaan'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_srt_kep'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_penghargaan = inlineformset_factory(DokumenSDM, RiwayatPenghargaan, UrutkanRiwayatPenghargaanForm, extra=0, can_delete=False)


class RiwayatKeluargaForm(forms.ModelForm):
    class Meta:
        model = RiwayatKeluarga
        fields = ('pegawai', 'dokumen', 'no_kk', 'file')
    
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatKeluargaForm, self).__init__(*args, **kwargs)
        initial = kwargs.get('initial')
        if initial and initial.get('pegawai'):
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()


class UrutkanRiwayatKeluargaForm(forms.ModelForm):
    class Meta:
        model = RiwayatKeluarga
        fields = ('no_urut_dokumen', 'pegawai', 'no_kk')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatKeluargaForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['pegawai'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['no_kk'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_keluarga = inlineformset_factory(DokumenSDM, RiwayatKeluarga, UrutkanRiwayatKeluargaForm, extra=0, can_delete=False)


class RiwayatKeluargaOrangTuaForm(forms.ModelForm):
    class Meta:
        model = OrangTua
        fields = ('keluarga', 'nama', 'status_hidup', 'pekerjaan', 'jk', 'nik', 'agama', 'tlp', 'alamat')
        
    def __init__(self, *args, **kwargs):
        super(RiwayatKeluargaOrangTuaForm, self).__init__(*args, **kwargs)
        self.fields['keluarga'].required = False
        self.fields['keluarga'].widget = forms.HiddenInput()
            

class RiwayatKeluargaPasanganForm(forms.ModelForm):
    class Meta:
        model = Pasangan
        fields = ('keluarga', 'nama', 'status_hidup', 'pasangan_ke', 'tempat_lahir', 'tgl_lahir', 'akte_meninggal', 'tgl_meninggal', 'akte_menikah', 'tgl_menikah', 'tgl_cerai', 'pekerjaan', 'jk', 'nik',
                  'karsu_karis', 'agama', 'tlp', 'alamat', 'masuk_daftar_gaji')
        
    def __init__(self, *args, **kwargs):
        super(RiwayatKeluargaPasanganForm, self).__init__(*args, **kwargs)
        self.fields['keluarga'].required = False
        self.fields['keluarga'].widget = forms.HiddenInput()
        self.fields['tgl_lahir'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_meninggal'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_menikah'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class RiwayatKeluargaAnakForm(forms.ModelForm):
    class Meta:
        model = Anak
        fields = ('keluarga', 'nama', 'status_hidup', 'tempat_lahir', 'tgl_lahir', 'akte_meninggal', 'tgl_meninggal', 'pekerjaan', 'jk', 'nik', 'agama', 'tlp', 'alamat', 'masuk_daftar_gaji')
        
    def __init__(self, *args, **kwargs):
        super(RiwayatKeluargaAnakForm, self).__init__(*args, **kwargs)
        self.fields['keluarga'].widget = forms.HiddenInput()
        self.fields['tgl_lahir'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_meninggal'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        

class RiwayatInovasiFullForm(forms.ModelForm):
    class Meta:
        model = RiwayatInovasi
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatInovasiFullForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['dokumen'].widget = forms.HiddenInput()
            self.fields['pegawai'].widget = forms.HiddenInput()


class RiwayatInovasiForm(forms.ModelForm):
    class Meta:
        model = RiwayatInovasi
        fields = ('pegawai', 'dokumen', 'bidang', 'judul', 'desk', 'makalah',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatInovasiForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()


class RiwayatInovasiTLForm(forms.ModelForm):
    class Meta:
        model = RiwayatInovasi
        fields = ('pegawai', 'dokumen', 'bidang', 'judul')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatInovasiTLForm, self).__init__(*args, **kwargs)
        self.fields['dokumen'].widget = forms.HiddenInput()
        self.fields['pegawai'].widget = forms.HiddenInput()
        self.fields['bidang'].widget = forms.HiddenInput()
        self.fields['judul'].widget = forms.HiddenInput()        


class RiwayatInovasiSKForm(forms.ModelForm):
    class Meta:
        model = RiwayatInovasi
        fields = ('pegawai', 'dokumen', 'bidang', 'judul', 'no_sk', 'tanggal', 'file_sk')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatInovasiSKForm, self).__init__(*args, **kwargs)
        self.fields['dokumen'].widget = forms.HiddenInput()
        self.fields['tanggal'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['bidang'].widget = forms.HiddenInput()
        self.fields['judul'].widget = forms.HiddenInput()
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()


class UrutkanRiwayatInovasiForm(forms.ModelForm):
    class Meta:
        model = RiwayatInovasi
        fields = ('no_urut_dokumen', 'judul', 'no_sk')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatInovasiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['judul'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['no_sk'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_inovasi = inlineformset_factory(DokumenSDM, RiwayatInovasi, UrutkanRiwayatInovasiForm, extra=0, can_delete=False)


class RiwayatPenugasanForm(forms.ModelForm):
    class Meta:
        model=RiwayatPenugasan
        fields = ('pegawai', 'dokumen', 'jabatan', 'panggol', 'nama_keg', 'tempat_keg', 'peran', 'lama_keg', 'tgl_mulai', 'tgl_selesai', 'anggaran', 'sumber_angg', 'file_spt')

    def __init__(self, *args, **kwargs):
        user=kwargs.pop("user", None)
        initial_values = kwargs.pop('initial_values', {})
        super(RiwayatPenugasanForm, self).__init__(*args, **kwargs)
        for field, value in initial_values.items():
            self.fields[field].initial = value
        if user and not user.is_superuser:
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
            self.fields['jabatan'] = forms.ModelChoiceField(queryset=RiwayatJabatan.objects.filter(pegawai=user))
            self.fields['panggol'] = forms.ModelChoiceField(queryset=RiwayatPanggol.objects.filter(pegawai=user))
        self.fields['sumber_angg'].label=""
        self.fields['anggaran'].label="Centang jika ada anggaran yang digunakan"
        self.fields['sumber_angg'].widget.attrs['style']="display:none"
        self.fields['sumber_angg'].widget.attrs['placeholder']="Sumber Anggaran"
        self.fields['tgl_mulai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_selesai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})

    
class UrutkanRiwayatPenugasanForm(forms.ModelForm):
    class Meta:
        model = RiwayatPenugasan
        fields = ('no_urut_dokumen', 'nama_keg', 'tempat_keg')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatPenugasanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['nama_keg'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tempat_keg'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_penugasan = inlineformset_factory(DokumenSDM, RiwayatPenugasan, UrutkanRiwayatPenugasanForm, extra=0, can_delete=False)