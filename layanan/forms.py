from django import forms
from tinymce.widgets import TinyMCE

from .models import (
    LayananCuti, 
    JenisLayanan, 
    LayananGajiBerkala, 
    LayananUsulanDiklat,
    LayananUsulanInovasi,
    VerifikasiCuti,
    VerifikasiDiklat
    )
from dokumen.forms import (
    RiwayatDiklatForm, 
    FormRiwayatDiklatLaporan, 
    FormRiwayatDiklatProses,
    FormRiwayatDiklatSPT,
    FormAlihanRiwayatDiklat,
    FormPenugasanDiklat,
    FormUsulanRiwayatDiklat,
    
    RiwayatCutiForm,
    RiwayatPengajuanCutiForm,
)
from strukturorg.models import UnitInstalasi
from myaccount.models import Users
from dokumen.models import JENISCUTI, RiwayatCuti, RiwayatGajiBerkala, DokumenSDM, RiwayatDiklat, RiwayatInovasi
from django.forms import inlineformset_factory, BaseInlineFormSet

class TinyMCEWidget(TinyMCE): 
	def use_required_attribute(self, *args): 
		return False

bootstrap_col = 'form-control col-md-12'
# FORM LAYANAN BERKALA
class FormLayananBerkala(forms.ModelForm):
    class Meta:
        model = LayananGajiBerkala
        fields = ('pegawai', 'layanan', 'riwayat', 'status')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(FormLayananBerkala, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['riwayat'] = forms.ModelChoiceField(queryset=RiwayatGajiBerkala.objects.filter(pegawai=self.request.user))
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['layanan'].widget=forms.HiddenInput()
            self.fields['status'].widget=forms.HiddenInput()
            self.fields['riwayat'].label = 'Riwayat Kenaikan Gaji Berkala Sebelumnya'


# FORM LAYANAN CUTI
class FormLayananCutiExisting(forms.ModelForm):
    tgl_mulai_cuti = forms.DateField(required=False, widget=forms.TextInput(attrs={'type':'date', 'class':bootstrap_col}))
    tgl_akhir_cuti = forms.DateField(required=False, widget=forms.TextInput(attrs={'type':'date', 'class':bootstrap_col}))
    class Meta:
        model = LayananCuti
        fields = ('pegawai', 'layanan', 'status', 'tgl_mulai_cuti', 'tgl_akhir_cuti')
    
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(FormLayananCutiExisting, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['layanan'].widget=forms.HiddenInput()
            self.fields['status'].widget=forms.HiddenInput()
            # menghilangkan empty label: self.fields['cuti'].empty_label = None
        # id : self.fields['cuti'].widget.attrs['id'] = 'data_cuti'
            

class FormLayananCuti(forms.ModelForm):
    layanan = forms.ModelChoiceField(queryset=JenisLayanan.objects.all(), required=True)
    status = forms.CharField(required=False)
    
    class Meta:
        model = RiwayatCuti
        fields = ('pegawai', 'layanan', 'dokumen', 'jenis_cuti', 'alasan_cuti', 'tgl_mulai_cuti', 'tgl_akhir_cuti', 'lama_cuti', 'domisili_saat_cuti', 'status_cuti', 'status')

    def __init__(self, status=None, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(FormLayananCuti, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()
            self.fields['layanan'].widget = forms.HiddenInput()
            self.fields['status'].widget = forms.HiddenInput()
            self.fields['status_cuti'].widget = forms.HiddenInput()
        if status == 'tunda':
            self.fields['jenis_cuti'].widget = forms.HiddenInput()
            self.fields['tgl_mulai_cuti'].widget = forms.HiddenInput()
            self.fields['tgl_akhir_cuti'].widget = forms.HiddenInput()
            self.fields['jenis_cuti'].initial = 'Cuti Tahunan'
            self.fields['status_cuti'].initial = 'Tunda'
        if status == 'baru' or status == 'ambil-tunda':
            self.fields['status_cuti'].initial = 'Proses'
            self.fields['tgl_mulai_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
            self.fields['tgl_akhir_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})

################# cuti versi inlineform ########################
STATUS_CUTI = (
    ('tindaklanjut', 'Tindaklanjut'),
    ('tidak ditindaklanjut', 'Tidak ditindaklanjut'),
)

def get_instalasi_queryset(user):
    qs = UnitInstalasi.objects.all()
    if user.is_superuser:
        return qs
    profil = getattr(user, 'profil_admin', None)
    if profil:
        if profil.instalasi.exists():
            return qs.filter(pk__in=profil.instalasi.values_list('pk', flat=True))
        if profil.sub_bidang:
            return qs.filter(sub_bidang=profil.sub_bidang)
        if profil.bidang:
            return qs.filter(sub_bidang__bidang=profil.bidang)
    return qs.none()
    
class LayananCutiForm(forms.ModelForm):
    pegawai = forms.ModelChoiceField(queryset=Users.objects.all().exclude(is_superuser=True, is_active=False))
    class Meta:
        model = LayananCuti
        fields = ('pegawai', 'cuti_tunda', 'layanan', 'status', 'tahun')

    def __init__(self, *args, **kwargs):
        self.action = kwargs.pop("action", None)#edit or add
        self.case = kwargs.pop("case", None)#dakung/proses/dll
        self.request = kwargs.pop("request", None)
        super(LayananCutiForm, self).__init__(*args, **kwargs)
        if self.case == "tindaklanjut":
            self.fields['status'] = forms.ChoiceField(choices=STATUS_CUTI)
            self.fields['status'].label = "Pilih tindaklanjut usulan cuti"
        else:
            self.fields['status'].widget = forms.HiddenInput()
        # self.fields['layanan'].widget = forms.HiddenInput()
        # self.fields['pegawai'].widget = forms.HiddenInput()
        self.fields['cuti_tunda'].widget = forms.HiddenInput()

pengajuan_cuti_formset = inlineformset_factory(
    LayananCuti, RiwayatCuti, form=RiwayatPengajuanCutiForm, extra=1, can_delete=False
)
update_pengajuan_cuti_formset = inlineformset_factory(
    LayananCuti, RiwayatCuti, form=RiwayatPengajuanCutiForm, extra=0, can_delete=False
)


class LayananCutiFullForm(forms.ModelForm):
    class Meta:
        model = LayananCuti
        fields = '__all__'

pengajuan_cuti_fullform_formset = inlineformset_factory(
    LayananCuti, RiwayatCuti, form=RiwayatPengajuanCutiForm, extra=1, can_delete=False
)
update_pengajuan_cuti_fullform_formset = inlineformset_factory(
    LayananCuti, RiwayatCuti, form=RiwayatPengajuanCutiForm, extra=0, can_delete=False
)

class VerifikatorCutiForm(forms.ModelForm):
    class Meta:
        model = VerifikasiCuti
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(VerifikatorCutiForm, self).__init__(*args, **kwargs)
        self.fields['layanan_cuti'].widget = forms.HiddenInput()


class Verifikator1CutiForm(forms.ModelForm):
    class Meta:
        model = VerifikasiCuti
        fields = ('layanan_cuti', 'verifikator1', 'persetujuan1', 'catatan1')

    def __init__(self, *args, **kwargs):
        super(Verifikator1CutiForm, self).__init__(*args, **kwargs)
        self.fields['layanan_cuti'].widget = forms.HiddenInput()
        self.fields['verifikator1'].widget = forms.HiddenInput()
        self.fields['persetujuan1'].label = 'Apakah anda menyetujui pengajuan cuti pegawai ini?'
        self.fields['catatan1'].label = 'Catatan persetujuan cuti'


class Verifikator2CutiForm(forms.ModelForm):
    class Meta:
        model = VerifikasiCuti
        fields = ('layanan_cuti', 'verifikator2', 'persetujuan2', 'catatan2')

    def __init__(self, *args, **kwargs):
        super(Verifikator2CutiForm, self).__init__(*args, **kwargs)
        self.fields['layanan_cuti'].widget = forms.HiddenInput()
        self.fields['verifikator2'].widget = forms.HiddenInput()
        self.fields['persetujuan2'].label = 'Apakah anda menyetujui pengajuan cuti pegawai ini?'
        self.fields['catatan2'].label = 'Catatan persetujuan cuti'


class Verifikator3CutiForm(forms.ModelForm):
    class Meta:
        model = VerifikasiCuti
        fields = ('layanan_cuti', 'verifikator3', 'persetujuan3', 'catatan3', 'tanggal')
    
    def __init__(self, *args, **kwargs):
        super(Verifikator3CutiForm, self).__init__(*args, **kwargs)
        self.fields['layanan_cuti'].widget = forms.HiddenInput()
        self.fields['verifikator3'].widget = forms.HiddenInput()
        self.fields['tanggal'].widget = forms.HiddenInput()
        self.fields['persetujuan3'].label = 'Apakah anda menyetujui pengajuan cuti pegawai ini?'
        self.fields['catatan3'].label = 'Catatan persetujuan cuti'


class FormCatatanSDMUsulanLayananDiklat(forms.ModelForm):
    catatan_sdm = forms.CharField(widget=TinyMCEWidget(attrs={'required': False, 'cols': 30, 'rows': 10}))
    class Meta:
        model = LayananUsulanDiklat
        fields = ('layanan', 'catatan_sdm')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(FormCatatanSDMUsulanLayananDiklat, self).__init__(*args, **kwargs)
        self.fields['layanan'].widget=forms.HiddenInput()
        

class FormUsulanLayananDiklat(forms.ModelForm):
    justifikasi = forms.CharField(widget=TinyMCEWidget(attrs={'required': False, 'cols': 30, 'rows': 10}))
    class Meta:
        model = LayananUsulanDiklat
        fields = ('layanan', 'pembiayaan', 'biaya', 'justifikasi', 'brosur', 'tor')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(FormUsulanLayananDiklat, self).__init__(*args, **kwargs)
        self.fields['tor'].help_text = 'Wajib jika usulan pelatihan bersifat internal'
        if self.request and not self.request.user.is_superuser:
            self.fields['layanan'].widget=forms.HiddenInput()

usulan_diklat_formset = inlineformset_factory(
    LayananUsulanDiklat, #parent model
    RiwayatDiklat, #child model
    FormUsulanRiwayatDiklat, #form berasal dari riwayatdiklat
    extra=1, 
    can_delete=False
)

class FormPenugasanUsulanDiklat(forms.ModelForm):
    justifikasi = forms.CharField(widget=TinyMCEWidget(attrs={'required': False, 'cols': 30, 'rows': 10}))
    class Meta:
        model = LayananUsulanDiklat
        fields = ('layanan', 'pembiayaan', 'biaya', 'justifikasi', 'brosur', 'tor')

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super(FormPenugasanUsulanDiklat, self).__init__(*args, **kwargs)
        self.fields['layanan'].widget=forms.HiddenInput()
        self.fields['tor'].widget=forms.HiddenInput()
        
penugasan_inline_formset = inlineformset_factory(
    LayananUsulanDiklat, 
    RiwayatDiklat, 
    FormPenugasanDiklat, 
    extra=1, 
    can_delete=False
)

class FormPengalihanUsulanDiklat(forms.ModelForm):
    class Meta:
        model = LayananUsulanDiklat
        fields = ('layanan', 'pembiayaan', 'biaya', 'justifikasi')

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super(FormPengalihanUsulanDiklat, self).__init__(*args, **kwargs)
        self.fields['layanan'].widget=forms.HiddenInput()
        self.fields['pembiayaan'].widget=forms.HiddenInput()
        self.fields['biaya'].widget=forms.HiddenInput()
        self.fields['justifikasi'].widget=forms.HiddenInput()

pengalihan_diklat_formset = inlineformset_factory(
    LayananUsulanDiklat, 
    RiwayatDiklat, 
    FormAlihanRiwayatDiklat, 
    extra=1, 
    can_delete=False
)


class FormLayananDiklat(forms.ModelForm):
    justifikasi = forms.CharField(widget=TinyMCEWidget(attrs={'required': False, 'cols': 30, 'rows': 10}))
    class Meta:
        model = LayananUsulanDiklat
        fields = ('layanan', 'status', 'justifikasi', 'brosur', 'tor')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(FormLayananDiklat, self).__init__(*args, **kwargs)
        self.fields['layanan'].required = False
        if self.request and self.request.user.is_superuser:
            #tampil pada awal pengusulan (aktor superuser)
            self.fields['layanan'].widget=forms.HiddenInput()
            self.fields['status'].widget=forms.HiddenInput()
        else:
            #akan tampil pada awal pengusulan (aktor user)
            self.fields['layanan'].widget=forms.HiddenInput()
            self.fields['status'].widget=forms.HiddenInput()

# usulan_diklat_formset = inlineformset_factory(RiwayatDiklat, LayananUsulanDiklat, FormLayananDiklat, extra=1, can_delete=False)
update_diklat_formset = inlineformset_factory(LayananUsulanDiklat, RiwayatDiklat, FormUsulanRiwayatDiklat, extra=0, can_delete=False)


class FormLayananDiklatLaporan(forms.ModelForm):
    class Meta:
        model = LayananUsulanDiklat
        fields = ('status', )
    
    def __init__(self, *args, **kwargs):
        super(FormLayananDiklatLaporan, self).__init__(*args, **kwargs)
        self.fields['status'].widget=forms.HiddenInput()

laporan_diklat_formset = inlineformset_factory(
    LayananUsulanDiklat, 
    RiwayatDiklat, 
    FormRiwayatDiklatLaporan, 
    extra=0, 
    can_delete=False
)

STATUS_DIKLAT = (
    ('', 'Pilih status'),
    ('proses', 'Proses'),
    ('tidak ditindaklanjut', 'Tidak ditindaklanjut'),
)

class FormLayananDiklatProses(forms.ModelForm):
    status = forms.ChoiceField(choices=STATUS_DIKLAT, required=True)
    class Meta:
        model = LayananUsulanDiklat
        fields = ('status', )
    
    def __init__(self, *args, **kwargs):
        super(FormLayananDiklatProses, self).__init__(*args, **kwargs)
        self.fields['status'].label = ''
        self.fields['status'].help_text = 'Pilih salah satu pilihan Proses/Tidak ditindaklanjut'

proses_diklat_formset = inlineformset_factory(
    LayananUsulanDiklat, 
    RiwayatDiklat, 
    FormRiwayatDiklatProses, 
    extra=0, 
    can_delete=False
)


class FormLayananDiklatSPT(forms.ModelForm):
    spt = forms.FileField(required=True)
    class Meta:
        model = LayananUsulanDiklat
        fields = ('status', 'spt', 'bukti_lunas')
    
    def __init__(self, *args, **kwargs):
        super(FormLayananDiklatSPT, self).__init__(*args, **kwargs)
        self.fields['status'].widget=forms.HiddenInput()
        self.fields['spt'].widget.attrs['class'] = 'form-control col-md-12'
        self.fields['bukti_lunas'].widget.attrs['class'] = 'form-control col-md-12'

spt_diklat_formset = inlineformset_factory(
    LayananUsulanDiklat, 
    RiwayatDiklat, 
    FormRiwayatDiklatSPT, 
    extra=0, 
    can_delete=False
)

class VerifikatorDiklatForm(forms.ModelForm):
    class Meta:
        model = VerifikasiDiklat
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(VerifikatorDiklatForm, self).__init__(*args, **kwargs)
        self.fields['layanan_diklat'].widget = forms.HiddenInput()


class Verifikator1DiklatForm(forms.ModelForm):
    class Meta:
        model = VerifikasiDiklat
        fields = ('layanan_diklat', 'verifikator1', 'persetujuan1', 'catatan1', 'verifikator2', 'persetujuan2', 'catatan2',
                  'verifikator3', 'persetujuan3', 'catatan3', 'tanggal')

    def __init__(self, *args, **kwargs):
        super(Verifikator1DiklatForm, self).__init__(*args, **kwargs)
        self.fields['layanan_diklat'].widget = forms.HiddenInput()
        self.fields['verifikator1'].widget = forms.HiddenInput()
        self.fields['persetujuan1'].label = 'Apakah anda menyetujui pengajuan diklat pegawai ini?'
        self.fields['catatan1'].label = 'Catatan persetujuan diklat'
        self.fields['verifikator2'].widget = forms.HiddenInput()
        self.fields['persetujuan2'].widget = forms.HiddenInput()
        self.fields['catatan2'].widget = forms.HiddenInput()
        self.fields['verifikator3'].widget = forms.HiddenInput()
        self.fields['persetujuan3'].widget = forms.HiddenInput()
        self.fields['catatan3'].widget = forms.HiddenInput()
        self.fields['tanggal'].widget = forms.HiddenInput()

verifikator1_inlineformset = inlineformset_factory(
    LayananUsulanDiklat, VerifikasiDiklat, Verifikator1DiklatForm, extra=1, can_delete=False
    )

class Verifikator2DiklatForm(forms.ModelForm):
    class Meta:
        model = VerifikasiDiklat
        fields = ('layanan_diklat', 'verifikator1', 'persetujuan1', 'catatan1', 'verifikator2', 'persetujuan2', 'catatan2',
                  'verifikator3', 'persetujuan3', 'catatan3', 'tanggal')

    def __init__(self, *args, **kwargs):
        super(Verifikator2DiklatForm, self).__init__(*args, **kwargs)
        self.fields['layanan_diklat'].widget = forms.HiddenInput()
        self.fields['verifikator1'].widget = forms.HiddenInput()
        self.fields['persetujuan1'].widget = forms.HiddenInput()
        self.fields['catatan1'].widget = forms.HiddenInput()
        self.fields['verifikator2'].widget = forms.HiddenInput()
        self.fields['persetujuan2'].label = 'Apakah anda menyetujui pengajuan diklat pegawai ini?'
        self.fields['catatan2'].label = 'Catatan persetujuan diklat'
        self.fields['verifikator3'].widget = forms.HiddenInput()
        self.fields['persetujuan3'].widget = forms.HiddenInput()
        self.fields['catatan3'].widget = forms.HiddenInput()
        self.fields['tanggal'].widget = forms.HiddenInput()

verifikator2_inlineformset = inlineformset_factory(
    LayananUsulanDiklat, VerifikasiDiklat, Verifikator2DiklatForm, extra=1, can_delete=False
)

class Verifikator3DiklatForm(forms.ModelForm):
    class Meta:
        model = VerifikasiDiklat
        fields = ('layanan_diklat', 'verifikator1', 'persetujuan1', 'catatan1', 'verifikator2', 'persetujuan2', 'catatan2',
                  'verifikator3', 'persetujuan3', 'catatan3', 'tanggal')
    
    def __init__(self, *args, **kwargs):
        super(Verifikator3DiklatForm, self).__init__(*args, **kwargs)
        self.fields['layanan_diklat'].widget = forms.HiddenInput()
        self.fields['verifikator1'].widget = forms.HiddenInput()
        self.fields['persetujuan1'].widget = forms.HiddenInput()
        self.fields['catatan1'].widget = forms.HiddenInput()
        self.fields['verifikator2'].widget = forms.HiddenInput()
        self.fields['persetujuan2'].widget = forms.HiddenInput()
        self.fields['catatan2'].widget = forms.HiddenInput()
        self.fields['verifikator3'].widget = forms.HiddenInput()
        self.fields['persetujuan3'].label = 'Apakah anda menyetujui pengajuan diklat pegawai ini?'
        self.fields['catatan3'].label = 'Catatan persetujuan diklat'
        self.fields['tanggal'].widget = forms.HiddenInput()

verifikator3_inlineformset = inlineformset_factory(
    LayananUsulanDiklat, VerifikasiDiklat, Verifikator3DiklatForm, extra=1, can_delete=False
)
#BUAT FORM INOVASI NEXT PEKERJAAN...
# class BaseFormSet(BaseInlineFormSet):
#     def __init__(self, *args, **kwargs):
#         self.request = kwargs.pop("request", None)
#         super(BaseFormSet, self).__init__(*args, **kwargs)

class FormLayananUsulanInovasi(forms.ModelForm):
    class Meta:
        model = LayananUsulanInovasi
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(FormLayananUsulanInovasi, self).__init__(*args, **kwargs)
        self.fields['pegawai'].required=False
        self.fields['pegawai'].widget=forms.HiddenInput()
        self.fields['layanan'].widget=forms.HiddenInput()
        self.fields['inovasi'].widget=forms.HiddenInput()
        self.fields['status'].widget=forms.HiddenInput()

inovasi_formset = inlineformset_factory(RiwayatInovasi, LayananUsulanInovasi, form=FormLayananUsulanInovasi, extra=1, can_delete=False)
update_inovasi_formset = inlineformset_factory(RiwayatInovasi, LayananUsulanInovasi, form=FormLayananUsulanInovasi, extra=0, can_delete=False)


class FormLayananUsulanInovasiFullEdit(forms.ModelForm):
    class Meta:
        model = LayananUsulanInovasi
        fields = '__all__'

full_update_inovasi_formset = inlineformset_factory(RiwayatInovasi, LayananUsulanInovasi, form=FormLayananUsulanInovasiFullEdit, extra=0, can_delete=False)

PROSESUSULANINOVASI = (
    ('proses', 'proses'),
    ('tidak ditindaklanjut', 'tidak ditindaklanjut')
)

class FormLayananProsesUsulanInovasi(forms.ModelForm):
    status = forms.ChoiceField(choices=PROSESUSULANINOVASI)
    class Meta:
        model = LayananUsulanInovasi
        fields = ('pegawai', 'layanan', 'inovasi', 'status')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(FormLayananProsesUsulanInovasi, self).__init__(*args, **kwargs)
        self.fields['pegawai'].required=False
        self.fields['pegawai'].widget=forms.HiddenInput()
        self.fields['layanan'].widget=forms.HiddenInput()
        self.fields['inovasi'].widget=forms.HiddenInput()
        self.fields['status'].label = ''
        self.fields['status'].help_text = 'Pilih salah satu pilihan Proses/Tidak ditindaklanjut'

proses_inovasi_formset = inlineformset_factory(RiwayatInovasi, LayananUsulanInovasi, form=FormLayananProsesUsulanInovasi, extra=0, can_delete=False)


class FormLayananTindaklanjutUsulanInovasi(forms.ModelForm):
    class Meta:
        model = LayananUsulanInovasi
        fields = ('pegawai', 'layanan', 'inovasi', 'status')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(FormLayananTindaklanjutUsulanInovasi, self).__init__(*args, **kwargs)
        self.fields['pegawai'].required=False
        self.fields['pegawai'].widget=forms.HiddenInput()
        self.fields['layanan'].widget=forms.HiddenInput()
        self.fields['inovasi'].widget=forms.HiddenInput()
        self.fields['status'].widget=forms.HiddenInput()

tindaklanjut_inovasi_formset = inlineformset_factory(RiwayatInovasi, LayananUsulanInovasi, form=FormLayananTindaklanjutUsulanInovasi, extra=0, can_delete=False)
