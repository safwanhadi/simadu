from django import forms
from tinymce.widgets import TinyMCE
from datetime import date
from django.utils import timezone

from django.db.models import Sum, F, Q
from django.db.models.functions import Coalesce

from dokumen.models import RiwayatPanggol, RiwayatPenempatan
from .models import (
    LayananCuti, 
    JenisLayanan, 
    LayananGajiBerkala, 
    LayananUsulanDiklat,
    LayananUsulanInovasi,
    VerifikasiCuti,
    VerifikasiDiklat,
    PelimpahanTugas,
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
from dokumen.models import (
    JENISCUTI, 
    RiwayatCuti, 
    RiwayatGajiBerkala, 
    DokumenSDM, 
    RiwayatDiklat, 
    RiwayatInovasi,
    KlaimCutiTunda,
)
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


class RiwayatGajiBerkalaForm(forms.ModelForm):
    class Meta:
        model = RiwayatGajiBerkala
        fields = ('pegawai', 'dokumen', 'no_srt_gaji', 'tgl_srt_gaji', 'gaji_pkk', 'tmt_gaji', 'pangkat', 'tempat_kerja', 'masa_kerja_tahun', 'masa_kerja_bulan', 
                  'has_layanan', 'pertek', 'ket', 'file')
        
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        self.action = kwargs.pop("action", None)
        super(RiwayatGajiBerkalaForm, self).__init__(*args, **kwargs)
        self.fields['has_layanan'].widget = forms.HiddenInput()
        self.fields['tmt_gaji'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        if self.action == 'upload':
            self.fields['tgl_srt_gaji'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
            self.fields['gaji_pkk'].widget = forms.HiddenInput()
            self.fields['tmt_gaji'].widget = forms.HiddenInput()
            self.fields['masa_kerja_tahun'].widget = forms.HiddenInput()
            self.fields['masa_kerja_bulan'].widget = forms.HiddenInput()
            self.fields['pertek'].widget = forms.HiddenInput()
            self.fields['ket'].widget = forms.HiddenInput()
            self.fields['pangkat'].widget = forms.HiddenInput()
            self.fields['tempat_kerja'].widget = forms.HiddenInput()
        else:
            self.fields['tgl_srt_gaji'].empty_value = None
            self.fields['tgl_srt_gaji'].widget = forms.HiddenInput()
            self.fields['no_srt_gaji'].widget = forms.HiddenInput()
            
            
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
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-control')
        if self.case == "tindaklanjut":
            self.fields['status'] = forms.ChoiceField(choices=STATUS_CUTI)
            self.fields['status'].label = "Pilih tindaklanjut usulan cuti"
        else:
            self.fields['status'].widget = forms.HiddenInput()
        self.fields["tahun"].disabled = True
        self.fields['layanan'].widget = forms.HiddenInput()
        self.fields['pegawai'].widget = forms.HiddenInput()
        self.fields['cuti_tunda'].widget = forms.HiddenInput()

pengajuan_cuti_formset = inlineformset_factory(
    LayananCuti, RiwayatCuti, form=RiwayatPengajuanCutiForm, extra=1, can_delete=False
)
update_pengajuan_cuti_formset = inlineformset_factory(
    LayananCuti, RiwayatCuti, form=RiwayatPengajuanCutiForm, extra=0, can_delete=False
)

class PelimpahanTugasCreateForm(forms.ModelForm):
    class Meta:
        model = PelimpahanTugas
        fields = ['penerima_tugas', 'deskripsi_tugas', 'tgl_mulai', 'tgl_selesai']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.riwayat_cuti = kwargs.pop('riwayat_cuti', None)
        super().__init__(*args, **kwargs)

        # Optionally: batasi pilihan penerima_tugas hanya 1 instalasi / unit tertentu.
        # Contoh: semua pegawai 1 SubBidang / Instalasi yg sama.
        # self.fields['penerima_tugas'].queryset = Users.objects.filter(...)
        # Default tanggal mengikuti riwayat cuti
        if self.riwayat_cuti and not self.instance.pk:
            if self.riwayat_cuti.tgl_mulai_cuti and not self.initial.get("tgl_mulai"):
                self.initial["tgl_mulai"] = self.riwayat_cuti.tgl_mulai_cuti
            if self.riwayat_cuti.tgl_akhir_cuti and not self.initial.get("tgl_selesai"):
                self.initial["tgl_selesai"] = self.riwayat_cuti.tgl_akhir_cuti
    
    def clean(self):
        cleaned = super().clean()
        a = cleaned.get("tgl_mulai")
        b = cleaned.get("tgl_selesai")
        if a and b and a > b:
            raise forms.ValidationError("Tanggal mulai tidak boleh melebihi tanggal selesai.")
        return cleaned



class PelimpahanTugasPenerimaForm(forms.ModelForm):
    aksi = forms.ChoiceField(
        choices=(
            ('setuju', 'Setuju menerima tugas'),
            ('tolak', 'Tolak tugas'),
        ),
        widget=forms.RadioSelect
    )

    class Meta:
        model = PelimpahanTugas
        fields = ['aksi', 'catatan_penerima']


class PelimpahanTugasAtasanForm(forms.ModelForm):
    aksi = forms.ChoiceField(
        choices=(
            ('setuju', 'Setuju'),
            ('tolak', 'Tolak'),
        ),
        widget=forms.RadioSelect
    )

    class Meta:
        model = PelimpahanTugas
        fields = ['aksi', 'catatan_atasan']


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


class OverrideKlaimTundaForCutiForm(forms.Form):
    sumber_tunda = forms.ModelChoiceField(
        queryset=RiwayatCuti.objects.none(),
        required=True,
        label="Sumber Cuti Tunda",
        help_text="Pilih cuti tunda yang masih memiliki sisa hari.",
    )
    jumlah_hari_diklaim = forms.IntegerField(
        min_value=1,
        required=True,
        label="Jumlah hari diklaim",
    )
    catatan_admin = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Catatan admin (opsional)",
    )

    def __init__(self, *args, **kwargs):
        self.cuti_klaim: RiwayatCuti = kwargs.pop("cuti_klaim")
        self.allow_same_year: bool = kwargs.pop("allow_same_year", True)  # override tahun berjalan
        super().__init__(*args, **kwargs)

        pegawai_id = self.cuti_klaim.pegawai_id
        tahun = self.cuti_klaim.tahun_cuti

        # sumber tunda: defaultnya tahun berjalan (karena kasus override)
        qs = (
            RiwayatCuti.objects.filter(
                pegawai_id=pegawai_id,
                jenis_cuti="Cuti Tahunan",
                status_cuti="Tunda",
                status_persetujuan="disetujui",
            )
            .annotate(total_terklaim=Coalesce(Sum("klaim_keluar__jumlah_hari_diklaim"), 0))
            .filter(total_terklaim__lt=F("lama_cuti"))
            .order_by("-created_at", "-id")
        )

        if not self.allow_same_year and tahun:
            # kalau suatu saat Anda ingin memblok tahun berjalan
            qs = qs.exclude(tahun_cuti=tahun)

        self.fields["sumber_tunda"].queryset = qs

    def clean(self):
        cleaned = super().clean()

        sumber_tunda: RiwayatCuti = cleaned.get("sumber_tunda")
        jumlah: int = cleaned.get("jumlah_hari_diklaim")

        if not sumber_tunda or not jumlah:
            return cleaned

        # Pastikan pegawai sama
        if sumber_tunda.pegawai_id != self.cuti_klaim.pegawai_id:
            self.add_error("sumber_tunda", "Sumber tunda tidak sesuai dengan pegawai cuti klaim.")
            return cleaned

        # Sisa tunda aktual
        total_terklaim = sumber_tunda.klaim_keluar.aggregate(
            total=Coalesce(Sum("jumlah_hari_diklaim"), 0)
        )["total"]
        sisa_tunda = max(0, (sumber_tunda.lama_cuti or 0) - (total_terklaim or 0))

        if jumlah > sisa_tunda:
            self.add_error("jumlah_hari_diklaim", f"Jumlah klaim melebihi sisa tunda ({sisa_tunda}).")

        # Sisa kebutuhan cuti klaim (agar tidak klaim melebihi lama cuti)
        total_klaim_masuk = self.cuti_klaim.klaim_masuk.aggregate(
        total=Coalesce(Sum("jumlah_hari_diklaim"), 0)
        )["total"] or 0

        # Jika lama_cuti sudah terisi, pakai itu.
        if (self.cuti_klaim.lama_cuti or 0) > 0:
            kebutuhan_total = int(self.cuti_klaim.lama_cuti or 0)
        else:
            # Kalau lama_cuti=0, pakai periode tanggal sebagai kebutuhan
            if self.cuti_klaim.tgl_mulai_cuti and self.cuti_klaim.tgl_akhir_cuti:
                kebutuhan_total = (self.cuti_klaim.tgl_akhir_cuti - self.cuti_klaim.tgl_mulai_cuti).days + 1
            else:
                # kalau tanggal belum ada, tidak bisa validasi kebutuhan -> paksa isi dulu
                self.add_error("jumlah_hari_diklaim", "Tidak bisa menentukan kebutuhan cuti karena lama cuti 0 dan tanggal cuti belum lengkap.")
                return cleaned

        sisa_kebutuhan = max(0, kebutuhan_total - int(total_klaim_masuk))

        if jumlah > sisa_kebutuhan:
            self.add_error(
                "jumlah_hari_diklaim",
                f"Jumlah klaim melebihi kebutuhan cuti ini ({sisa_kebutuhan})."
            )

        return cleaned

    def save(self, commit: bool = True) -> KlaimCutiTunda:
        sumber_tunda = self.cleaned_data["sumber_tunda"]
        jumlah = self.cleaned_data["jumlah_hari_diklaim"]

        klaim = KlaimCutiTunda(
            sumber_tunda=sumber_tunda,
            cuti_klaim=self.cuti_klaim,
            jumlah_hari_diklaim=jumlah,
        )

        if commit:
            klaim.save()

        return klaim


class VerifikatorCutiForm(forms.ModelForm):
    class Meta:
        model = VerifikasiCuti
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(VerifikatorCutiForm, self).__init__(*args, **kwargs)
        self.fields['layanan_cuti'].widget = forms.HiddenInput()


STATUS_PERS = (
    ("", "— Pilih keputusan —"),
    ("setuju", "Setuju"),
    ("tolak", "Tolak"),
)

KEPUTUSAN_INPUT = (
    ("setuju", "Disetujui"),
    ("tunda", "Ditunda"),
    ("tolak", "Ditolak"),
)

class Verifikator1CutiForm(forms.ModelForm):
    keputusan1 = forms.ChoiceField(choices=KEPUTUSAN_INPUT, widget=forms.RadioSelect, required=True, label="Keputusan")
    catatan1 = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Catatan")
    
    class Meta:
        model = VerifikasiCuti
        fields = ("keputusan1", "catatan1")


class Verifikator2CutiForm(forms.ModelForm):
    keputusan2 = forms.ChoiceField(choices=KEPUTUSAN_INPUT, widget=forms.RadioSelect, required=True, label="Keputusan")
    catatan2 = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Catatan")
    
    class Meta:
        model = VerifikasiCuti
        fields = ('layanan_cuti', 'verifikator2', 'keputusan2', 'catatan2')

    def __init__(self, *args, **kwargs):
        super(Verifikator2CutiForm, self).__init__(*args, **kwargs)
        self.fields['layanan_cuti'].widget = forms.HiddenInput()
        self.fields['verifikator2'].widget = forms.HiddenInput()
        self.fields['keputusan2'].label = 'Apakah anda menyetujui pengajuan cuti pegawai ini?'
        self.fields['catatan2'].label = 'Catatan persetujuan cuti'


class Verifikator3CutiForm(forms.ModelForm):
    keputusan3 = forms.ChoiceField(choices=KEPUTUSAN_INPUT, widget=forms.RadioSelect, required=True, label="Keputusan")
    catatan3 = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Catatan")
    
    class Meta:
        model = VerifikasiCuti
        fields = ('layanan_cuti', 'verifikator3', 'keputusan3', 'catatan3', 'tanggal')
    
    def __init__(self, *args, **kwargs):
        super(Verifikator3CutiForm, self).__init__(*args, **kwargs)
        self.fields['tanggal'].initial = timezone.now().date()
        self.fields['layanan_cuti'].widget = forms.HiddenInput()
        self.fields['verifikator3'].widget = forms.HiddenInput()
        self.fields['tanggal'].widget = forms.HiddenInput()
        self.fields['keputusan3'].label = 'Apakah anda menyetujui pengajuan cuti pegawai ini?'
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
