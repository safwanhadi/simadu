from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory, inlineformset_factory
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta, timezone

from layanan.services import CheckCuti
from layanan.cuti_calendar import (
    PolaKerjaTidakDitemukan,
    get_pola_kerja_aktif,
    hitung_tanggal_akhir_cuti_tahunan,
)
from layanan.access.sip import (
    filter_users_for_sip_role,
    is_sip_admin,
    is_sip_structural_officer,
)
from layanan.access.promotion import (
    filter_users_for_jabatan_role,
    filter_users_for_pangkat_role,
    is_jabatan_admin,
    is_pangkat_admin,
    is_promotion_structural_officer,
)
from layanan.access.berkala import (
    filter_users_for_berkala_role,
    is_berkala_admin,
    is_berkala_structural_officer,
)
from layanan.access.inovasi import (
    filter_users_for_inovasi_role,
    is_inovasi_admin,
    is_inovasi_structural_officer,
)
from layanan.access.documents import (
    filter_document_users,
    is_document_scope_admin,
    is_document_scope_manager,
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
    RiwayatPAK,
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


class SecureEmployeeModelForm(forms.ModelForm):
    """Cegah pegawai biasa memindahkan dokumen ke akun pegawai lain."""

    can_select_other_employees = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = getattr(self, 'request', None)
        actor = request.user if request is not None else None
        if (
            actor is not None
            and getattr(actor, 'is_authenticated', False)
            and not self.can_select_other_employees
            and 'pegawai' in self.fields
        ):
            self.fields['pegawai'].queryset = filter_document_users(
                Users.objects.filter(is_active=True), actor
            )

    def clean(self):
        cleaned_data = super().clean()
        request = getattr(self, 'request', None)
        actor = request.user if request is not None else getattr(self, 'document_user', None)
        if (
            actor is not None
            and actor.is_authenticated
            and not self.can_select_other_employees
            and 'pegawai' in self.fields
        ):
            employee_field = self._meta.model._meta.get_field('pegawai')
            selected = cleaned_data.get('pegawai')
            if is_document_scope_manager(actor):
                selected_users = (
                    selected
                    if employee_field.many_to_many
                    else Users.objects.filter(pk=getattr(selected, 'pk', None))
                )
                allowed_ids = set(
                    filter_document_users(
                        Users.objects.filter(is_active=True), actor
                    ).values_list('pk', flat=True)
                )
                if any(user.pk not in allowed_ids for user in selected_users):
                    self.add_error(
                        'pegawai',
                        'Pegawai berada di luar assignment scope Anda.',
                    )
            elif employee_field.many_to_many:
                cleaned_data['pegawai'] = Users.objects.filter(pk=actor.pk)
            else:
                cleaned_data['pegawai'] = actor
        return cleaned_data


class RiwayatPendidikanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPendidikan
        fields = ('pegawai', 'dokumen', 'level_pend', 'pendidikan', 
                  'nama_sek', 'tgl_lulus', 'no_ijazah', 'gelar_depan', 'gelar_belakang', 'is_verifikasi', 'file_verifikasi','file_ijazah', 'file_transkrip')
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatPendidikanForm, self).__init__(*args, **kwargs)
        self.fields['level_pend'].widget.attrs['class'] = bootstrap_col
        self.fields['level_pend'].label = "Level Pendidikan"
        self.fields['tgl_lulus'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['nama_sek'].label = "Nama Sekolah/Universitas"
        self.fields['no_ijazah'].label = "Nomor Ijazah"
        self.fields['is_verifikasi'].label = "Apakah ijazah sudah terverifikasi?"
        self.fields['file_verifikasi'].label = "Upload File Hasil Verifikasi Ijazah (jika sudah terverifikasi)"
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
            self.fields.pop('is_verifikasi', None)
            self.fields.pop('file_verifikasi', None)


class UrutkanDokumenSDMForm(SecureEmployeeModelForm):
    class Meta:
        model = DokumenSDM
        fields = ('nama', )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(UrutkanDokumenSDMForm, self).__init__(*args, **kwargs)
        self.fields['nama'].widget=forms.HiddenInput()
        self.fields['nama'].disabled = True


class UrutkanRiwayatPendidikanForm(SecureEmployeeModelForm):
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

class RiwayatPengangkatanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPengangkatan
        fields = ('pegawai', 'dokumen', 'status_pegawai', 'no_srt_putusan', 'tgl_srt_putusan', 'tmt_pegawai', 'pejabat_pelantik',
                  'no_srt_spmt', 'tgl_srt_spmt', 'no_srt_latsar', 'tgl_srt_latsar', 'karpeg', 'file_sk', 'file_spmt', 'file_latsar', 'file_karpeg')
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatPengangkatanForm, self).__init__(*args, **kwargs)
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
        self.fields['tgl_srt_putusan'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tmt_pegawai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_srt_spmt'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_srt_latsar'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        

class UrutkanRiwayaPengangkatanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPengangkatan
        fields = ('no_urut_dokumen', 'status_pegawai', 'tgl_srt_putusan')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayaPengangkatanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['status_pegawai'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_srt_putusan'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_pengangkatan = inlineformset_factory(DokumenSDM, RiwayatPengangkatan, UrutkanRiwayaPengangkatanForm, extra=0, can_delete=False)


class RiwayatBekerjaForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatBekerja
        fields = ('pegawai', 'dokumen', 'nama_instansi', 'jabatan', 'no_sk', 'tgl_sk', 'tgl_mulai', 'tgl_selesai', 'file')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatBekerjaForm, self).__init__(*args, **kwargs)
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
        self.fields['tgl_sk'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_mulai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_selesai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        
class UrutkanRiwayatBekerjaForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatBekerja
        fields = ('no_urut_dokumen', 'nama_instansi', 'jabatan')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatBekerjaForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['nama_instansi'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['jabatan'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_bekerja = inlineformset_factory(DokumenSDM, RiwayatBekerja, UrutkanRiwayatBekerjaForm, extra=0, can_delete=False)


class RiwayatPenempatanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPenempatan
        fields = ('pegawai', 'dokumen', 'penempatan_level1', 'penempatan_level2', 'penempatan_level3', 'penempatan_level4', 'no_sk', 'tgl_sk', 'status', 'file')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatPenempatanForm, self).__init__(*args, **kwargs)
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget.attrs['hidden'] = 'hidden'
            self.fields['dokumen'].widget.attrs['hidden'] = 'hidden'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
        self.fields['tgl_sk'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['status'].label = 'Centang jika pegawai aktif dan berada diinstalasi ini'
        
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        # Mengambil 4 field penempatan
        lv1 = cleaned_data.get('penempatan_level1')
        lv2 = cleaned_data.get('penempatan_level2')
        lv3 = cleaned_data.get('penempatan_level3')
        lv4 = cleaned_data.get('penempatan_level4')

        penempatan_fields = [lv1, lv2, lv3, lv4]
        filled_count = sum(1 for field in penempatan_fields if field)

        if status and filled_count < 1:
            raise forms.ValidationError(
                'Untuk penempatan aktif, harap isi minimal satu level penempatan.'
            )
        return cleaned_data

class UrutkanRiwayatPenempatanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPenempatan
        fields = ('no_urut_dokumen', 'penempatan_level4', 'penempatan_level3')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatPenempatanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['penempatan_level4'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['penempatan_level3'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_penempatan = inlineformset_factory(DokumenSDM, RiwayatPenempatan, UrutkanRiwayatPenempatanForm, extra=0, can_delete=False)

class RiwayatPenempatanLainnyaForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPenempatan
        fields = ('pegawai', 'dokumen', 'instansi_sebelumnya', 'bidang_sebelumnya', 'seksi_sebelumnya', 'unit_sebelumnya', 'no_sk', 'tgl_sk', 'status', 'file')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.pegawai = kwargs.pop('pegawai', None)
        if self.pegawai is None and self.request is not None:
            self.pegawai = self.request.user
        self.document_user = self.pegawai
        super(RiwayatPenempatanLainnyaForm, self).__init__(*args, **kwargs)
        if self.pegawai and not is_document_scope_manager(self.pegawai):
            self.fields['pegawai'].widget.attrs['hidden'] = 'hidden'
            self.fields['dokumen'].widget.attrs['hidden'] = 'hidden'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
            self.fields['status'].widget = forms.HiddenInput()
        self.fields['tgl_sk'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})

class UrutkanRiwayatPenempatanLainnyaForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPenempatan
        fields = ('no_urut_dokumen', 'seksi_sebelumnya', 'bidang_sebelumnya')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatPenempatanLainnyaForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['seksi_sebelumnya'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['bidang_sebelumnya'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_penempatan_lainnya = inlineformset_factory(DokumenSDM, RiwayatPenempatan, UrutkanRiwayatPenempatanLainnyaForm, extra=0, can_delete=False)

class RiwayatProfesiForm(SecureEmployeeModelForm):
    can_select_other_employees = True

    class Meta:
        model = RiwayatProfesi
        fields = (
            'pegawai', 'dokumen', 'profesi', 'no_str',
            'tgl_str', 'berlaku_sd_str', 'str_seumur_hidup', 'file_str',
        )

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatProfesiForm, self).__init__(*args, **kwargs)
        if self.request:
            actor = self.request.user
            self.fields['pegawai'].queryset = filter_users_for_sip_role(
                Users.objects.filter(is_active=True), actor
            )
        if self.request and not (
            is_sip_admin(self.request.user)
            or is_sip_structural_officer(self.request.user)
        ):
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()
        self.fields['tgl_str'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['berlaku_sd_str'].widget = forms.TextInput(
            attrs={'type': 'date', 'class': bootstrap_col}
        )
        self.fields['str_seumur_hidup'].help_text = (
            'Centang jika STR sudah menggunakan ketentuan berlaku seumur hidup. '
            'Tanggal berlaku sampai akan dikosongkan otomatis.'
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('str_seumur_hidup'):
            cleaned_data['berlaku_sd_str'] = None
            self.instance.berlaku_sd_str = None
        return cleaned_data

class UrutkanRiwayatProfesiForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatProfesi
        fields = ('no_urut_dokumen', 'profesi', 'tgl_str')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatProfesiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['profesi'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_str'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_profesi = inlineformset_factory(DokumenSDM, RiwayatProfesi, UrutkanRiwayatProfesiForm, extra=0, can_delete=False)


class RiwayatSIPProfesiForm(SecureEmployeeModelForm):
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


class UrutkanRiwayatProfesiForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatProfesi
        fields = ('no_str', )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(UrutkanRiwayatProfesiForm, self).__init__(*args, **kwargs)
        self.fields['no_str'].widget=forms.HiddenInput()


class UrutkanRiwayatSIPProfesiForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatSIPProfesi
        fields = ('no_urut_dokumen', 'no_sip', 'tgl_sip')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatSIPProfesiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['no_sip'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_sip'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_sip = inlineformset_factory(RiwayatProfesi, RiwayatSIPProfesi, UrutkanRiwayatSIPProfesiForm, extra=0, can_delete=False)


class RiwayatPanggolForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPanggol
        fields = ('pegawai', 'dokumen', 'panggol', 'masa_kerja_tahun', 'masa_kerja_bulan', 'tmt_gol', 'no_sk', 'tgl_sk', 
                  'no_pertek_bkn', 'tgl_pertek_bkn', 'file')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatPanggolForm, self).__init__(*args, **kwargs)
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget.attrs['hidden'] = 'hidden'
            self.fields['dokumen'].widget.attrs['hidden'] = 'hidden'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
        self.fields['tmt_gol'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_sk'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_pertek_bkn'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})

class UrutkanRiwayatPanggolForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPanggol
        fields = ('no_urut_dokumen', 'panggol', 'tmt_gol')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatPanggolForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['panggol'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tmt_gol'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_panggol = inlineformset_factory(DokumenSDM, RiwayatPanggol, UrutkanRiwayatPanggolForm, extra=0, can_delete=False)


class UjiKompetensiForm(SecureEmployeeModelForm):
    class Meta:
        model = UjiKompetensi
        fields = (
            'pegawai', 'kompetensi', 'no_sert_ujikomp',
            'tgl_sert_ujikomp', 'masa_berlaku',
            'kategori_kompetensi', 'file_sert',
        )
        widgets = {
            'pegawai': forms.Select(attrs={'class': f'{bootstrap_col} select2'}),
            'kompetensi': forms.Select(attrs={'class': f'{bootstrap_col} select2'}),
            'no_sert_ujikomp': forms.TextInput(attrs={'class': bootstrap_col}),
            'tgl_sert_ujikomp': forms.DateInput(attrs={'class': bootstrap_col, 'type': 'date'}),
            'masa_berlaku': forms.NumberInput(attrs={'class': bootstrap_col, 'min': 0}),
            'file_sert': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(UjiKompetensiForm, self).__init__(*args, **kwargs)
        self.fields['masa_berlaku'].required = False
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['pegawai'].required = False


class KompetensiForm(SecureEmployeeModelForm):
    class Meta:
        model = Kompetensi
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop('request', None)
        super(KompetensiForm, self).__init__(*args, **kwargs)
        self.fields['tgl_sert_komp'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['berlaku_sd'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        if not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()

class UrutkanKompetensiForm(SecureEmployeeModelForm):
    class Meta:
        model = Kompetensi
        fields = ('no_urut_dokumen', 'kompetensi', 'tgl_sert_komp')

    def __init__(self, *args, **kwargs):
        super(UrutkanKompetensiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['kompetensi'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_sert_komp'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_kompetensi = inlineformset_factory(DokumenSDM, Kompetensi, UrutkanKompetensiForm, extra=0, can_delete=False)


class RiwayatJabatanForm(SecureEmployeeModelForm):
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
        if self.request and not self.request.user.is_dokumen_admin:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()
            self.fields['kompetensi'] = forms.ModelMultipleChoiceField(queryset=Kompetensi.objects.filter(pegawai=self.request.user))
            self.fields['kompetensi'].widget.attrs['class'] = 'jabatan'
            self.fields['kompetensi'].required = False

class UrutkanRiwayatJabatanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatJabatan
        fields = ('no_urut_dokumen', 'nama_jabatan', 'detail_nama_jabatan')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatJabatanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['nama_jabatan'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['detail_nama_jabatan'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_jabatan = inlineformset_factory(DokumenSDM, RiwayatJabatan, UrutkanRiwayatJabatanForm, extra=0, can_delete=False)


class RiwayatJabatanAdminForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatJabatan
        fields = '__all__'

    kompetensi = forms.ModelMultipleChoiceField(queryset=Kompetensi.objects.all(), required=False)


class RiwayatGajiBerkalaForm(SecureEmployeeModelForm):
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
        if self.request:
            allowed_users = filter_document_users(
                Users.objects.filter(is_active=True), self.request.user
            )
            self.fields['pegawai'].queryset = allowed_users
            self.fields['pangkat'].queryset = RiwayatPanggol.objects.filter(
                pegawai__in=allowed_users
            )
            self.fields['tempat_kerja'].queryset = RiwayatPenempatan.objects.filter(
                pegawai__in=allowed_users
            )
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()
            self.fields['pangkat'] = forms.ModelChoiceField(queryset=RiwayatPanggol.objects.filter(pegawai=self.request.user))
            self.fields['tempat_kerja'] = forms.ModelChoiceField(queryset=RiwayatPenempatan.objects.filter(pegawai=self.request.user))
        self.fields['tgl_srt_gaji'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tmt_gaji'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})

    def clean(self):
        cleaned_data = super().clean()
        pegawai = cleaned_data.get('pegawai')
        pangkat = cleaned_data.get('pangkat')
        tempat_kerja = cleaned_data.get('tempat_kerja')
        if pegawai and pangkat and pangkat.pegawai_id != pegawai.pk:
            self.add_error('pangkat', 'Pangkat harus milik pegawai yang dipilih.')
        if (
            pegawai
            and tempat_kerja
            and tempat_kerja.pegawai_id != pegawai.pk
        ):
            self.add_error(
                'tempat_kerja',
                'Penempatan harus milik pegawai yang dipilih.',
            )
        return cleaned_data


class UrutkanRiwayatGajiBerkalaForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatGajiBerkala
        fields = ('no_urut_dokumen', 'gaji_pkk', 'tmt_gaji')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatGajiBerkalaForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['gaji_pkk'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tmt_gaji'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_berkala = inlineformset_factory(DokumenSDM, RiwayatGajiBerkala, UrutkanRiwayatGajiBerkalaForm, extra=0, can_delete=False)


class RiwayatKinerjaForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatKinerja
        fields = (
            'pegawai', 'hasil_kinerja', 'prilaku_kinerja', 'kuadran_kinerja',
            'periode_kinerja_awal', 'periode_kinerja_akhir',
            'nama_penilai', 'file',
        )
        widgets = {
            'pegawai': forms.Select(attrs={'class': f'{bootstrap_col} select2'}),
            'hasil_kinerja': forms.Select(attrs={'class': bootstrap_col}),
            'prilaku_kinerja': forms.Select(attrs={'class': bootstrap_col}),
            'kuadran_kinerja': forms.Select(attrs={'class': f'{bootstrap_col} select2'}),
            'periode_kinerja_awal': forms.DateInput(attrs={'type': 'date', 'class': bootstrap_col}),
            'periode_kinerja_akhir': forms.DateInput(attrs={'type': 'date', 'class': bootstrap_col}),
            'nama_penilai': forms.Select(attrs={'class': f'{bootstrap_col} select2'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatKinerjaForm, self).__init__(*args, **kwargs)
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['pegawai'].required = False

    def clean(self):
        cleaned_data = super().clean()
        awal = cleaned_data.get('periode_kinerja_awal')
        akhir = cleaned_data.get('periode_kinerja_akhir')
        if awal and akhir and akhir < awal:
            self.add_error('periode_kinerja_akhir', 'Periode akhir tidak boleh sebelum periode awal.')
        return cleaned_data


class RiwayatPAKForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPAK
        fields = ('pegawai', 'no_srt', 'tgl_srt', 'ak', 'file')
        widgets = {
            'pegawai': forms.Select(attrs={'class': f'{bootstrap_col} select2'}),
            'no_srt': forms.TextInput(attrs={'class': bootstrap_col}),
            'tgl_srt': forms.DateInput(attrs={'type': 'date', 'class': bootstrap_col}),
            'ak': forms.NumberInput(attrs={'class': bootstrap_col, 'min': 0}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['tgl_srt'].required = True
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['pegawai'].required = False


class UrutkanRiwayatKinerjaForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatKinerja
        fields = ('no_urut_dokumen', 'hasil_kinerja', 'prilaku_kinerja')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatKinerjaForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['hasil_kinerja'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['prilaku_kinerja'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_kinerja = inlineformset_factory(DokumenSDM, RiwayatKinerja, UrutkanRiwayatKinerjaForm, extra=0, can_delete=False)


class RiwayatOrganisasiForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatOrganisasi
        fields = ('pegawai', 'dokumen', 'nama_org', 'jabatan', 'no_anggota', 'tgl_gabung', 'tgl_keluar', 'file')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatOrganisasiForm, self).__init__(*args, **kwargs)
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
        self.fields['tgl_gabung'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_keluar'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class UrutkanRiwayatOrganisasiForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatOrganisasi
        fields = ('no_urut_dokumen', 'nama_org', 'jabatan')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatOrganisasiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['nama_org'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['jabatan'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_organisasi = inlineformset_factory(DokumenSDM, RiwayatOrganisasi, UrutkanRiwayatOrganisasiForm, extra=0, can_delete=False)


class FormUsulanRiwayatDiklat(SecureEmployeeModelForm):
    can_select_other_employees = True
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
        if self.request:
            from layanan.access.diklat import (
                filter_users_for_diklat_admin,
                is_diklat_admin,
            )
            if is_diklat_admin(self.request.user):
                self.fields['pegawai'].queryset = filter_users_for_diklat_admin(
                    Users.objects.filter(is_active=True),
                    self.request.user,
                )
            else:
                self.fields['pegawai'].queryset = Users.objects.filter(
                    pk=self.request.user.pk,
                )
        self.fields['jenis_diklat'].help_text = 'jenis diklat: Seminar/Workshop/Pelatihan/Pertemuan Ilmiah/FGD, dll.'
        self.fields['tgl_mulai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_selesai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['usulan'].widget=forms.HiddenInput()
        if self.request and not self.request.user.is_dokumen_admin:
            self.fields['pegawai'].label = ''#form disembunyikan menggunakan jquery di template
            self.fields['dokumen'].widget=forms.HiddenInput()
        elif self.request and self.request.user.is_dokumen_admin:
            self.fields['pegawai'].widget.attrs['class'] = 'select2'
            
            
class FormPenugasanDiklat(SecureEmployeeModelForm):
    can_select_other_employees = True
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
        if request is not None:
            from layanan.access.diklat import (
                filter_users_for_diklat_admin,
                filter_users_for_diklat_supervisor,
            )
            base = Users.objects.filter(is_active=True)
            self.fields['pegawai'].queryset = (
                filter_users_for_diklat_admin(base, request.user)
                | filter_users_for_diklat_supervisor(base, request.user)
            ).distinct()
        self.fields['jenis_diklat'].help_text = 'jenis diklat: Seminar/Workshop/Pelatihan/Pertemuan Ilmiah/FGD, dll.'
        self.fields['tgl_mulai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_selesai'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['dokumen'].widget=forms.HiddenInput()


class FormAlihanRiwayatDiklat(SecureEmployeeModelForm):
    can_select_other_employees = True
    pegawai = forms.ModelMultipleChoiceField(queryset=Users.objects.filter(is_active=True), widget=forms.SelectMultiple(attrs={'class': 'select2'}))
    class Meta:
        model = RiwayatDiklat
        fields = ('pegawai', 'dokumen', 'jenis_diklat', 'nama_diklat', 'penyelenggara', 'metode', 'tgl_mulai', 'tgl_selesai', 'skp')

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(FormAlihanRiwayatDiklat, self).__init__(*args, **kwargs)
        if request is not None:
            from layanan.access.diklat import (
                filter_users_for_diklat_admin,
                filter_users_for_diklat_supervisor,
            )
            base = Users.objects.filter(is_active=True)
            self.fields['pegawai'].queryset = (
                filter_users_for_diklat_admin(base, request.user)
                | filter_users_for_diklat_supervisor(base, request.user)
            ).distinct()
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


class UrutkanRiwayatDiklatForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatDiklat
        fields = ('no_urut_dokumen', 'nama_diklat', 'tgl_sertifikat')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatDiklatForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['nama_diklat'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_sertifikat'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_diklat = inlineformset_factory(DokumenSDM, RiwayatDiklat, UrutkanRiwayatDiklatForm, extra=0, can_delete=False)


class FormRiwayatDiklatLaporan(SecureEmployeeModelForm):
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


class RiwayatDiklatForm(SecureEmployeeModelForm):
    can_select_other_employees = True
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

        if self.request:
            from layanan.access.diklat import (
                filter_users_for_diklat_role,
                is_diklat_admin,
                is_diklat_structural_officer,
            )
            self.fields['pegawai'].queryset = filter_users_for_diklat_role(
                Users.objects.filter(is_active=True),
                self.request.user,
            )
            if not (
                is_diklat_admin(self.request.user)
                or is_diklat_structural_officer(self.request.user)
            ):
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

    
class FormRiwayatDiklatSPT(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatDiklat
        fields = ('pegawai', 'dokumen', 'jenis_diklat', 'nama_diklat', 'penyelenggara', 'metode', 'tgl_mulai', 'tgl_selesai', 'skp')
        
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(FormRiwayatDiklatSPT, self).__init__(*args, **kwargs) 
        if self.request is not None and self.request.user.is_dokumen_admin:
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
        

class FormRiwayatDiklatProses(SecureEmployeeModelForm):
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


class RiwayatCutiForm(SecureEmployeeModelForm):
    can_select_other_employees = True
    class Meta:
        model = RiwayatCuti
        fields = ('pegawai', 'dokumen', 'jenis_cuti', 'tgl_mulai_cuti', 'tgl_akhir_cuti', 'lama_cuti', 'domisili_saat_cuti', 
                'no_surat', 'status_cuti', 'tgl_surat', 'file')
        
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatCutiForm, self).__init__(*args, **kwargs)
        if self.request:
            from layanan.access.cuti import (
                filter_users_for_leave_role,
                is_leave_admin,
                is_leave_structural_officer,
            )
            self.fields['pegawai'].queryset = filter_users_for_leave_role(
                Users.objects.filter(is_active=True),
                self.request.user,
            )
        if self.request and not (
            is_leave_admin(self.request.user)
            or is_leave_structural_officer(self.request.user)
        ):
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['pegawai'].initial = self.request.user.pk
            self.fields['dokumen'].widget.attrs['hidden'] = 'hidden'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
        self.fields['tgl_mulai_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_akhir_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_surat'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        
        
class RiwayatCutiTundaForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatCuti
        fields = ('pegawai', 'dokumen', 'jenis_cuti', 'tgl_mulai_cuti', 'tgl_akhir_cuti', 'alasan_cuti', 'lama_cuti', 'domisili_saat_cuti', 
                   'status_cuti')
        
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatCutiTundaForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_dokumen_admin:
            self.fields['pegawai'].widget.attrs['hidden'] = 'hidden'
            self.fields['dokumen'].widget.attrs['hidden'] = 'hidden'
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
            self.fields['status_cuti'].widget=forms.HiddenInput()
            self.fields['jenis_cuti'].widget=forms.HiddenInput()
        self.fields['tgl_mulai_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_akhir_cuti'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class UrutkanRiwayatCutiForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatCuti
        fields = ('no_urut_dokumen', 'jenis_cuti')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatCutiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['jenis_cuti'].widget.attrs['class'] = 'form-control col-md-6'

urutkan_dokumen_cuti = inlineformset_factory(DokumenSDM, RiwayatCuti, UrutkanRiwayatCutiForm, extra=0, can_delete=False)


bootstrap_col = 'form-control'

class CutiTundaMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj: RiwayatCuti) -> str:
        """
        Label yang muncul di checkbox pilihan cuti tunda.
        Misal: "Tahun 2023 – Tunda 7 hari (sisa 3 hari)"
        """
        tahun = obj.tahun_cuti or "-"
        total = obj.lama_cuti or 0
        sisa = obj.sisa_hari_tunda  # property dari model

        return f"Tahun {tahun} – Tunda {total} hari (sisa {sisa} hari)"
    
class RiwayatPengajuanCutiForm(SecureEmployeeModelForm):
    JENIS_CUTI_DIGITAL = (
        'Cuti Tahunan',
        'Cuti Alasan Penting',
        'Cuti melahirkan',
        'Cuti Sakit',
        'Cuti Besar',
        'Cuti Diluar Tanggungan Negara',
    )

    pakai_tunda_saja = forms.BooleanField(required=False, label="Ambil cuti tunda saja")
    # field tambahan untuk klaim cuti tunda
    cuti_tunda_dipilih = CutiTundaMultipleChoiceField(
        queryset=RiwayatCuti.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Gunakan Cuti Tunda",
        help_text="Pilih cuti tunda tahun sebelumnya (maksimal 2 tahun) yang ingin diklaim.",
    )

    class Meta:
        model = RiwayatCuti
        fields = (
            'jenis_cuti', 'alasan_cuti',
            'tgl_mulai_cuti', 'tgl_akhir_cuti', 'lama_cuti',
            'domisili_saat_cuti',
        )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.tahun_pengajuan = kwargs.pop("tahun_pengajuan", None)
        self.check_cuti = kwargs.pop("check_cuti", None) # instance CheckCuti / view
        self.target_pegawai = kwargs.pop("target_pegawai", None)
        super(RiwayatPengajuanCutiForm, self).__init__(*args, **kwargs)
        self.fields['jenis_cuti'].choices = [
            choice
            for choice in self.fields['jenis_cuti'].choices
            if not choice[0] or choice[0] in self.JENIS_CUTI_DIGITAL
        ]
        exclude_from_form_control = ['cuti_tunda_dipilih']

        for name, field in self.fields.items():
            if name in exclude_from_form_control:
                continue
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-control')

        if self.instance and self.instance.pk:
            for field in self.fields.values():
                field.disabled = True

        self.fields['tgl_mulai_cuti'].widget = forms.TextInput(
            attrs={'type': 'date', 'class': bootstrap_col}
        )
        self.fields['tgl_akhir_cuti'].widget = forms.TextInput(
            attrs={'type': 'date', 'class': bootstrap_col}
        )

        # === SET QUERYSET CUTI TUNDA ELIGIBLE ===
        if (
            self.request
            and self.tahun_pengajuan
            and self.check_cuti
            and self.target_pegawai
        ):
            self.fields['cuti_tunda_dipilih'].queryset = self.check_cuti.get_cuti_tunda_eligible(
                user=self.target_pegawai,
                tahun_pengajuan=self.tahun_pengajuan,
            )
        else:
            self.fields['cuti_tunda_dipilih'].queryset = RiwayatCuti.objects.none()
        if not self.fields['cuti_tunda_dipilih'].queryset.exists():
            self.fields['cuti_tunda_dipilih'].help_text = "Tidak ada cuti tunda yang dapat diklaim."
            
    def clean_lama_cuti(self):
        lama = self.cleaned_data.get("lama_cuti")
        if lama is None:
            raise forms.ValidationError("Lama cuti wajib diisi.")
        if lama <= 0:
            raise forms.ValidationError("Lama cuti harus lebih dari 0 hari.")
        return lama

    def clean(self):
        cleaned = super().clean()
        jenis_cuti = cleaned.get('jenis_cuti')
        tgl_mulai = cleaned.get('tgl_mulai_cuti')
        tgl_akhir = cleaned.get('tgl_akhir_cuti')
        lama = cleaned.get("lama_cuti")

        if not self.request or not self.request.user.is_authenticated:
            return cleaned
        
        # kalau user isi tgl akhir, pastikan konsisten
        if tgl_mulai and tgl_akhir and tgl_akhir < tgl_mulai:
            self.add_error("tgl_akhir_cuti", "Tanggal akhir tidak boleh lebih kecil dari tanggal mulai.")

        if tgl_mulai and lama:
            tanggal_akhir_hasil_hitung = tgl_mulai + timedelta(days=lama - 1)
            if jenis_cuti == CheckCuti.CUTI_TAHUNAN:
                target_pegawai = self.target_pegawai or self.request.user
                try:
                    pola_kerja = get_pola_kerja_aktif(target_pegawai, tgl_mulai)
                except PolaKerjaTidakDitemukan:
                    self.add_error(
                        'tgl_mulai_cuti',
                        'Pola kerja pegawai belum ditentukan pada tanggal mulai cuti. '
                        'Hubungi pengelola jadwal.',
                    )
                    pola_kerja = None
                if pola_kerja is not None:
                    tanggal_akhir_hasil_hitung = hitung_tanggal_akhir_cuti_tahunan(
                        tgl_mulai,
                        lama,
                        pola_kerja.pola_kerja,
                    )
            if tgl_akhir and tgl_akhir != tanggal_akhir_hasil_hitung:
                self.add_error(
                    "tgl_akhir_cuti",
                    "Tanggal akhir harus sesuai dengan tanggal mulai, jumlah hari cuti, "
                    "hari libur, dan pola kerja pegawai.",
                )
            elif not tgl_akhir:
                cleaned['tgl_akhir_cuti'] = tanggal_akhir_hasil_hitung
                self.instance.tgl_akhir_cuti = tanggal_akhir_hasil_hitung
                tgl_akhir = tanggal_akhir_hasil_hitung

        # Hanya cek untuk Cuti Tahunan (sesuai requirement)
        if jenis_cuti == CheckCuti.CUTI_TAHUNAN and tgl_mulai and tgl_akhir:
            checker = self.check_cuti or CheckCuti()
            target_pegawai = self.target_pegawai or self.request.user
            if checker.is_penerima_memiliki_pelimpahan_aktif(
                target_pegawai,
                tgl_mulai,
                tgl_akhir
            ):
                raise ValidationError(
                    "Anda tidak dapat mengajukan cuti karena sedang menerima pelimpahan tugas "
                    "pada rentang tanggal tersebut."
                )

        target_pegawai = self.target_pegawai or self.request.user
        if tgl_mulai and tgl_akhir and self.check_cuti:
            if self.check_cuti.is_memiliki_cuti_bentrok(
                target_pegawai,
                tgl_mulai,
                tgl_akhir,
            ):
                raise ValidationError(
                    "Pegawai sudah memiliki pengajuan atau pelaksanaan cuti lain "
                    "yang bertabrakan dengan rentang tanggal tersebut."
                )

        return cleaned

            

class RiwayatHukumanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatHukuman
        fields = ('pegawai', 'dokumen', 'jenis_hukuman', 'no_srt_kep', 'tgl_srt_kep', 'hukuman_ke', 'ket', 'file')
    
    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatHukumanForm, self).__init__(*args, **kwargs)
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
        self.fields['tgl_srt_kep'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class UrutkanRiwayatHukumanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatHukuman
        fields = ('no_urut_dokumen', 'jenis_hukuman', 'tgl_srt_kep')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatHukumanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['jenis_hukuman'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_srt_kep'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_hukuman = inlineformset_factory(DokumenSDM, RiwayatHukuman, UrutkanRiwayatHukumanForm, extra=0, can_delete=False)


class RiwayatPenghargaanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPenghargaan
        fields = ('pegawai', 'dokumen', 'jenis_penghargaan', 'tahun_perolehan', 'no_srt_kep', 'tgl_srt_kep', 'file')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(RiwayatPenghargaanForm, self).__init__(*args, **kwargs)
        if self.request and not is_document_scope_manager(self.request.user):
            self.fields['pegawai'].widget=forms.HiddenInput()
            self.fields['dokumen'].widget=forms.HiddenInput()
            self.fields['pegawai'].label = ''
            self.fields['dokumen'].label = ''
        self.fields['tgl_srt_kep'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class UrutkanRiwayatPenghargaanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPenghargaan
        fields = ('no_urut_dokumen', 'jenis_penghargaan', 'tgl_srt_kep')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatPenghargaanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['jenis_penghargaan'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tgl_srt_kep'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_penghargaan = inlineformset_factory(DokumenSDM, RiwayatPenghargaan, UrutkanRiwayatPenghargaanForm, extra=0, can_delete=False)


class RiwayatKeluargaForm(SecureEmployeeModelForm):
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


class UrutkanRiwayatKeluargaForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatKeluarga
        fields = ('no_urut_dokumen', 'pegawai', 'no_kk')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatKeluargaForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['pegawai'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['no_kk'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_keluarga = inlineformset_factory(DokumenSDM, RiwayatKeluarga, UrutkanRiwayatKeluargaForm, extra=0, can_delete=False)


class RiwayatKeluargaOrangTuaForm(SecureEmployeeModelForm):
    class Meta:
        model = OrangTua
        fields = ('keluarga', 'nama', 'status_hidup', 'pekerjaan', 'jk', 'nik', 'agama', 'tlp', 'alamat')
        
    def __init__(self, *args, **kwargs):
        super(RiwayatKeluargaOrangTuaForm, self).__init__(*args, **kwargs)
        self.fields['keluarga'].required = False
        self.fields['keluarga'].widget = forms.HiddenInput()
            

class RiwayatKeluargaPasanganForm(SecureEmployeeModelForm):
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


class RiwayatKeluargaAnakForm(SecureEmployeeModelForm):
    class Meta:
        model = Anak
        fields = ('keluarga', 'nama', 'status_hidup', 'tempat_lahir', 'tgl_lahir', 'akte_meninggal', 'tgl_meninggal', 'pekerjaan', 'jk', 'nik', 'agama', 'tlp', 'alamat', 'masuk_daftar_gaji')
        
    def __init__(self, *args, **kwargs):
        super(RiwayatKeluargaAnakForm, self).__init__(*args, **kwargs)
        self.fields['keluarga'].widget = forms.HiddenInput()
        self.fields['tgl_lahir'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        self.fields['tgl_meninggal'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})
        

class RiwayatInovasiFullForm(SecureEmployeeModelForm):
    can_select_other_employees = True
    class Meta:
        model = RiwayatInovasi
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatInovasiFullForm, self).__init__(*args, **kwargs)
        if self.request:
            self.fields['pegawai'].queryset = filter_users_for_inovasi_role(
                Users.objects.filter(is_active=True), self.request.user
            )
        if self.request and not (
            is_inovasi_admin(self.request.user)
            or is_inovasi_structural_officer(self.request.user)
        ):
            self.fields['dokumen'].widget = forms.HiddenInput()
            self.fields['pegawai'].widget = forms.HiddenInput()


class RiwayatInovasiForm(SecureEmployeeModelForm):
    can_select_other_employees = True
    class Meta:
        model = RiwayatInovasi
        fields = ('pegawai', 'dokumen', 'bidang', 'judul', 'desk', 'makalah',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RiwayatInovasiForm, self).__init__(*args, **kwargs)
        if self.request:
            self.fields['pegawai'].queryset = filter_users_for_inovasi_role(
                Users.objects.filter(is_active=True), self.request.user
            )
        if self.request and not (
            is_inovasi_admin(self.request.user)
            or is_inovasi_structural_officer(self.request.user)
        ):
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['dokumen'].widget = forms.HiddenInput()


class RiwayatInovasiTLForm(SecureEmployeeModelForm):
    can_select_other_employees = True
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


class RiwayatInovasiSKForm(SecureEmployeeModelForm):
    can_select_other_employees = True
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
        if self.request and not self.request.user.is_dokumen_admin:
            self.fields['pegawai'].widget = forms.HiddenInput()


class UrutkanRiwayatInovasiForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatInovasi
        fields = ('no_urut_dokumen', 'judul', 'no_sk')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatInovasiForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['judul'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['no_sk'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_inovasi = inlineformset_factory(DokumenSDM, RiwayatInovasi, UrutkanRiwayatInovasiForm, extra=0, can_delete=False)


class RiwayatPenugasanForm(SecureEmployeeModelForm):
    class Meta:
        model=RiwayatPenugasan
        fields = ('pegawai', 'dokumen', 'jabatan', 'panggol', 'nama_keg', 'tempat_keg', 'peran', 'lama_keg', 'tgl_mulai', 'tgl_selesai', 'anggaran', 'sumber_angg', 'file_spt')

    def __init__(self, *args, **kwargs):
        user=kwargs.pop("user", None)
        self.document_user = user
        initial_values = kwargs.pop('initial_values', {})
        super(RiwayatPenugasanForm, self).__init__(*args, **kwargs)
        for field, value in initial_values.items():
            self.fields[field].initial = value
        if user and not is_document_scope_manager(user):
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

    
class UrutkanRiwayatPenugasanForm(SecureEmployeeModelForm):
    class Meta:
        model = RiwayatPenugasan
        fields = ('no_urut_dokumen', 'nama_keg', 'tempat_keg')

    def __init__(self, *args, **kwargs):
        super(UrutkanRiwayatPenugasanForm, self).__init__(*args, **kwargs)
        self.fields['no_urut_dokumen'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['nama_keg'].widget.attrs['class'] = 'form-control col-md-6'
        self.fields['tempat_keg'].widget.attrs['class'] = bootstrap_col

urutkan_dokumen_penugasan = inlineformset_factory(DokumenSDM, RiwayatPenugasan, UrutkanRiwayatPenugasanForm, extra=0, can_delete=False)
