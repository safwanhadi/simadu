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
    PerubahanJadwalCuti,
    LayananSIP,
    LayananNaikPangkat,
    LayananNaikJabatan,
    validate_file_size,
    )

from dokumen.forms import (
    RiwayatDiklatForm, 
    FormRiwayatDiklatLaporan, 
    FormRiwayatDiklatProses,
    FormRiwayatDiklatSPT,
    FormAlihanRiwayatDiklat,
    FormPenugasanDiklat,
    FormUsulanRiwayatDiklat,
    RiwayatPengajuanCutiForm,
)
from myaccount.models import Users
from dokumen.models import (
    RiwayatCuti, 
    RiwayatGajiBerkala, 
    RiwayatDiklat, 
    RiwayatInovasi,
    KlaimCutiTunda,
    RiwayatKinerja,
    RiwayatJabatan,
    RiwayatPAK,
    RiwayatPendidikan,
    RiwayatPengangkatan,
    RiwayatBekerja,
    UjiKompetensi,
    RiwayatProfesi,
)
from django.forms import inlineformset_factory, BaseInlineFormSet

class TinyMCEWidget(TinyMCE): 
	def use_required_attribute(self, *args): 
		return False

bootstrap_col = 'form-control col-md-12'
select2_col = f'{bootstrap_col} select2'


class LayananNaikPangkatForm(forms.ModelForm):
    class Meta:
        model = LayananNaikPangkat
        fields = (
            'pegawai', 'sk_kp_terakhir', 'kinerja_dua_thn', 'sk_jabfung', 'pak',
            'pendidikan', 'pengangkatan', 'mutasi',
        )
        widgets = {
            'pegawai': forms.Select(attrs={'class':select2_col}),
            'sk_kp_terakhir': forms.Select(attrs={'class': select2_col}),
            'kinerja_dua_thn': forms.SelectMultiple(attrs={'class': select2_col}),
            'sk_jabfung': forms.Select(attrs={'class': select2_col}),
            'pak': forms.SelectMultiple(attrs={'class': select2_col}),
            'pendidikan': forms.Select(attrs={'class': select2_col}),
            'pengangkatan': forms.Select(attrs={'class': select2_col}),
            'mutasi': forms.Select(attrs={'class': select2_col}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_pangkat_admin:
            queryset = Users.objects.filter(pk=user.pk)
            self.fields['pegawai'].queryset = queryset
            self.fields['pegawai'].initial = queryset.first()
            self.fields['pegawai'].widget = forms.HiddenInput()

        self.fields['sk_kp_terakhir'].label = 'SK Kenaikan Pangkat Terakhir'
        self.fields['kinerja_dua_thn'].label = 'SKP/Kinerja Dua Tahun Terakhir'
        self.fields['kinerja_dua_thn'].required = True
        self.fields['sk_jabfung'].label = 'SK Jabatan Fungsional'
        self.fields['pak'].label = 'Penetapan Angka Kredit (PAK)'
        self.fields['pendidikan'].label = 'Ijazah Pendidikan'
        self.fields['pengangkatan'].label = 'SK Pengangkatan CPNS/PNS/PPPK'
        self.fields['mutasi'].label = 'Riwayat Mutasi (jika ada)'

        if not user:
            for field_name in self.fields:
                self.fields[field_name].queryset = self.fields[field_name].queryset.none()
            return

        self.fields['sk_kp_terakhir'].queryset = RiwayatPanggol.objects.filter(
            pegawai=user
        ).order_by('-tmt_gol', '-id')
        self.fields['kinerja_dua_thn'].queryset = RiwayatKinerja.objects.filter(
            pegawai=user
        ).order_by('-periode_kinerja_akhir', '-id')
        self.fields['sk_jabfung'].queryset = RiwayatJabatan.objects.filter(
            pegawai=user
        ).order_by('-tmt_jabatan', '-id')
        self.fields['pak'].queryset = RiwayatPAK.objects.filter(
            pegawai=user
        ).order_by('-tgl_srt', '-id')
        self.fields['pendidikan'].queryset = RiwayatPendidikan.objects.filter(
            pegawai=user
        ).order_by('-tgl_lulus', '-id')
        self.fields['pengangkatan'].queryset = RiwayatPengangkatan.objects.filter(
            pegawai=user
        ).order_by('-tgl_srt_putusan', '-id')
        self.fields['mutasi'].queryset = RiwayatBekerja.objects.filter(
            pegawai=user
        ).order_by('-tgl_mulai', '-id')

    def clean_kinerja_dua_thn(self):
        values = self.cleaned_data['kinerja_dua_thn']
        if values.count() != 2:
            raise forms.ValidationError('Pilih tepat dua dokumen kinerja tahunan terakhir.')
        return values


class RiwayatPanggolHasilLayananForm(forms.ModelForm):
    class Meta:
        model = RiwayatPanggol
        fields = (
            'panggol', 'masa_kerja_tahun', 'masa_kerja_bulan', 'tmt_gol',
            'no_sk', 'tgl_sk', 'no_pertek_bkn', 'tgl_pertek_bkn', 'file',
        )
        widgets = {
            'panggol': forms.Select(attrs={'class': select2_col}),
            'masa_kerja_tahun': forms.NumberInput(attrs={'class': bootstrap_col, 'min': 0}),
            'masa_kerja_bulan': forms.NumberInput(attrs={'class': bootstrap_col, 'min': 0, 'max': 11}),
            'tmt_gol': forms.DateInput(attrs={'class': bootstrap_col, 'type': 'date'}),
            'no_sk': forms.TextInput(attrs={'class': bootstrap_col}),
            'tgl_sk': forms.DateInput(attrs={'class': bootstrap_col, 'type': 'date'}),
            'no_pertek_bkn': forms.TextInput(attrs={'class': bootstrap_col}),
            'tgl_pertek_bkn': forms.DateInput(attrs={'class': bootstrap_col, 'type': 'date'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].required = not bool(self.instance and self.instance.pk and self.instance.file)

    def clean_masa_kerja_bulan(self):
        value = self.cleaned_data['masa_kerja_bulan']
        if value < 0 or value > 11:
            raise forms.ValidationError('Masa kerja bulan harus antara 0 sampai 11.')
        return value


class LayananNaikJabatanForm(forms.ModelForm):
    class Meta:
        model = LayananNaikJabatan
        fields = (
           'pegawai', 'kinerja_dua_thn', 'kompetensi', 'pendidikan',
            'str_profesi', 'pak',
        )
        widgets = {
            'pegawai': forms.Select(attrs={'class': select2_col}),
            'kinerja_dua_thn': forms.SelectMultiple(attrs={'class': select2_col}),
            'kompetensi': forms.Select(attrs={'class': select2_col}),
            'pendidikan': forms.Select(attrs={'class': select2_col}),
            'str_profesi': forms.Select(attrs={'class': select2_col}),
            'pak': forms.Select(attrs={'class': select2_col}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_jabatan_admin:
            queryset = Users.objects.filter(pk=user.pk)
            self.fields['pegawai'].queryset = queryset
            self.fields['pegawai'].initial = queryset.first()
            self.fields['pegawai'].widget=forms.HiddenInput()

        self.fields['kinerja_dua_thn'].label = 'SKP/Kinerja Dua Tahun Terakhir'
        self.fields['kinerja_dua_thn'].required = True
        self.fields['kompetensi'].label = 'Sertifikat Uji Kompetensi'
        self.fields['pendidikan'].label = 'Ijazah Pendidikan (jika diperlukan)'
        self.fields['str_profesi'].label = 'STR Profesi (jika diperlukan)'
        self.fields['pak'].label = 'Penetapan Angka Kredit (PAK) Terakhir'

        if not user:
            for field_name in self.fields:
                self.fields[field_name].queryset = self.fields[field_name].queryset.none()
            return

        self.fields['kinerja_dua_thn'].queryset = RiwayatKinerja.objects.filter(
            pegawai=user
        ).order_by('-periode_kinerja_akhir', '-id')
        self.fields['kompetensi'].queryset = UjiKompetensi.objects.filter(
            pegawai=user
        ).order_by('-tgl_sert_ujikomp', '-id')
        self.fields['pendidikan'].queryset = RiwayatPendidikan.objects.filter(
            pegawai=user
        ).order_by('-tgl_lulus', '-id')
        self.fields['str_profesi'].queryset = RiwayatProfesi.objects.filter(
            pegawai=user
        ).order_by('-tgl_str', '-id')
        self.fields['pak'].queryset = RiwayatPAK.objects.filter(
            pegawai=user
        ).order_by('-tgl_srt', '-id')

    def clean_kinerja_dua_thn(self):
        values = self.cleaned_data['kinerja_dua_thn']
        if values.count() != 2:
            raise forms.ValidationError('Pilih tepat dua dokumen kinerja tahunan terakhir.')
        return values


class RiwayatJabatanHasilLayananForm(forms.ModelForm):
    class Meta:
        model = RiwayatJabatan
        fields = (
            'unor', 'bidang', 'sub_bidang', 'instalasi', 'jns_jabatan',
            'jenjang_jabatan', 'nama_jabatan', 'detail_nama_jabatan',
            'tmt_jabatan', 'tmt_pelantikan', 'no_sk', 'tgl_sk', 'file',
        )
        widgets = {
            'unor': forms.Select(attrs={'class': select2_col}),
            'bidang': forms.Select(attrs={'class': select2_col}),
            'sub_bidang': forms.Select(attrs={'class': select2_col}),
            'instalasi': forms.Select(attrs={'class': select2_col}),
            'jns_jabatan': forms.Select(attrs={'class': select2_col}),
            'jenjang_jabatan': forms.Select(attrs={'class': select2_col}),
            'nama_jabatan': forms.Select(attrs={'class': select2_col}),
            'detail_nama_jabatan': forms.TextInput(attrs={'class': bootstrap_col}),
            'tmt_jabatan': forms.DateInput(attrs={'class': bootstrap_col, 'type': 'date'}),
            'tmt_pelantikan': forms.DateInput(attrs={'class': bootstrap_col, 'type': 'date'}),
            'no_sk': forms.TextInput(attrs={'class': bootstrap_col}),
            'tgl_sk': forms.DateInput(attrs={'class': bootstrap_col, 'type': 'date'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].required = not bool(
            self.instance and self.instance.pk and self.instance.file
        )


# FORM LAYANAN BERKALA
class FormLayananBerkala(forms.ModelForm):
    class Meta:
        model = LayananGajiBerkala
        fields = ('pegawai', 'layanan', 'riwayat', 'status')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(FormLayananBerkala, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_berkala_admin:
            queryset = Users.objects.filter(pk=self.request.user.pk)
            self.fields['pegawai'].queryset = queryset
            self.fields['pegawai'].initial = queryset.first()
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
            
            
class LayananCutiForm(forms.ModelForm):
    pegawai = forms.ModelChoiceField(
        queryset=Users.objects.filter(is_active=True).exclude(is_superuser=True),
        label='Pegawai',
    )
    class Meta:
        model = LayananCuti
        fields = ('pegawai', 'layanan', 'status', 'tahun')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(LayananCutiForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-control')
        self.fields['status'].widget = forms.HiddenInput()
        self.fields["tahun"].disabled = True
        self.fields['layanan'].widget = forms.HiddenInput()
        if self.request and self.request.user.is_cuti_admin:
            self.fields['pegawai'].queryset = (
                Users.objects.filter(is_active=True)
                .exclude(is_superuser=True)
                .order_by('first_name', 'last_name', 'email')
            )
        elif self.request and self.request.user.is_authenticated:
            self.fields['pegawai'].queryset = Users.objects.filter(
                pk=self.request.user.pk,
            )
            self.fields['pegawai'].initial = self.request.user
            self.fields['pegawai'].widget = forms.HiddenInput()


class UploadFileCutiForm(forms.ModelForm):
    class Meta:
        model = RiwayatCuti
        fields = ('file',)
        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'application/pdf,.pdf',
            }),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        if not uploaded_file:
            raise forms.ValidationError('Pilih file surat cuti yang akan diunggah.')
        if not uploaded_file.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Surat cuti final harus berupa file PDF.')

        position = uploaded_file.tell()
        signature = uploaded_file.read(5)
        uploaded_file.seek(position)
        if signature != b'%PDF-':
            raise forms.ValidationError('Isi file tidak dikenali sebagai dokumen PDF yang valid.')
        return uploaded_file

pengajuan_cuti_formset = inlineformset_factory(
    LayananCuti,
    RiwayatCuti,
    form=RiwayatPengajuanCutiForm,
    extra=1,
    min_num=1,
    max_num=1,
    validate_min=True,
    validate_max=True,
    can_delete=False,
)
class PelimpahanTugasCreateForm(forms.ModelForm):
    class Meta:
        model = PelimpahanTugas
        fields = ['penerima_tugas', 'deskripsi_tugas', 'tgl_mulai', 'tgl_selesai']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.riwayat_cuti = kwargs.pop('riwayat_cuti', None)
        super().__init__(*args, **kwargs)

        queryset = Users.objects.filter(is_active=True).exclude(is_superuser=True)
        if self.riwayat_cuti:
            queryset = queryset.exclude(pk=self.riwayat_cuti.pegawai_id)
        self.fields['penerima_tugas'].queryset = queryset.order_by('first_name', 'last_name')

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
        penerima = cleaned.get("penerima_tugas")
        if a and b and a > b:
            raise forms.ValidationError("Tanggal mulai tidak boleh melebihi tanggal selesai.")
        if self.riwayat_cuti:
            if penerima and penerima.pk == self.riwayat_cuti.pegawai_id:
                self.add_error('penerima_tugas', "Penerima tugas tidak boleh pegawai yang mengajukan cuti.")
            if a != self.riwayat_cuti.tgl_mulai_cuti or b != self.riwayat_cuti.tgl_akhir_cuti:
                raise forms.ValidationError(
                    "Periode pelimpahan tugas harus sama dengan periode cuti."
                )
        if penerima and a and b:
            bentrok_cuti = RiwayatCuti.objects.filter(
                pegawai=penerima,
                tgl_mulai_cuti__lte=b,
                tgl_akhir_cuti__gte=a,
            ).exclude(
                usulan__status__in=('ditolak', 'dibatalkan')
            ).exists()
            bentrok_pelimpahan = PelimpahanTugas.objects.filter(
                penerima_tugas=penerima,
                tgl_mulai__lte=b,
                tgl_selesai__gte=a,
                status__in=('menunggu_penerima', 'menunggu_atasan', 'disetujui'),
            ).exclude(pk=self.instance.pk).exists()
            if bentrok_cuti or bentrok_pelimpahan:
                self.add_error(
                    'penerima_tugas',
                    'Pegawai ini sedang cuti atau menerima pelimpahan lain pada periode tersebut.',
                )
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


class PerubahanJadwalCutiForm(forms.ModelForm):
    class Meta:
        model = PerubahanJadwalCuti
        fields = ('tanggal_mulai_baru', 'tanggal_akhir_baru', 'alasan')
        widgets = {
            'tanggal_mulai_baru': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tanggal_akhir_baru': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'alasan': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.riwayat_cuti = kwargs.pop('riwayat_cuti')
        self.check_cuti = kwargs.pop('check_cuti')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        mulai = cleaned.get('tanggal_mulai_baru')
        akhir = cleaned.get('tanggal_akhir_baru')
        if not mulai or not akhir:
            return cleaned
        if mulai < date.today():
            self.add_error('tanggal_mulai_baru', 'Tanggal mulai baru tidak boleh sudah lewat.')
            return cleaned
        if akhir < mulai:
            self.add_error('tanggal_akhir_baru', 'Tanggal akhir tidak boleh sebelum tanggal mulai.')
            return cleaned

        lama_baru = (akhir - mulai).days + 1
        self.instance.lama_cuti_baru = lama_baru
        if (
            mulai == self.riwayat_cuti.tgl_mulai_cuti
            and akhir == self.riwayat_cuti.tgl_akhir_cuti
        ):
            raise forms.ValidationError('Jadwal baru sama dengan jadwal cuti saat ini.')

        bentrok = RiwayatCuti.objects.filter(
            pegawai=self.riwayat_cuti.pegawai,
            tgl_mulai_cuti__lte=akhir,
            tgl_akhir_cuti__gte=mulai,
        ).exclude(pk=self.riwayat_cuti.pk).exclude(
            usulan__status__in=('ditolak', 'dibatalkan')
        )
        if bentrok.exists():
            raise forms.ValidationError('Jadwal baru bertabrakan dengan pengajuan cuti lain.')

        if self.riwayat_cuti.jenis_cuti == 'Cuti Tahunan':
            total_klaim = self.riwayat_cuti.klaim_masuk.aggregate(
                total=Coalesce(Sum('jumlah_hari_diklaim'), 0)
            )['total'] or 0
            if lama_baru < total_klaim:
                raise forms.ValidationError(
                    f'Durasi baru tidak boleh kurang dari {total_klaim} hari yang sudah memakai cuti tunda.'
                )
            saldo_tersedia = self.check_cuti.cek_sisa_cuti(self.riwayat_cuti.pegawai)
            hak_lama_dilepas = self.riwayat_cuti.lama_cuti or 0
            if lama_baru > saldo_tersedia + hak_lama_dilepas:
                raise forms.ValidationError('Saldo cuti tidak mencukupi untuk jadwal baru.')

            pelimpahan = getattr(self.riwayat_cuti, 'pelimpahan_tugas', None)
            if self.riwayat_cuti.usulan.status in ('disetujui', 'selesai') and pelimpahan is None:
                raise forms.ValidationError(
                    'Pelimpahan tugas lama tidak ditemukan. Hubungi admin cuti sebelum mengubah jadwal.'
                )
            if pelimpahan:
                penerima = pelimpahan.penerima_tugas
                penerima_cuti = RiwayatCuti.objects.filter(
                    pegawai=penerima,
                    tgl_mulai_cuti__lte=akhir,
                    tgl_akhir_cuti__gte=mulai,
                ).exclude(
                    usulan__status__in=('ditolak', 'dibatalkan')
                ).exists()
                penerima_sibuk = PelimpahanTugas.objects.filter(
                    penerima_tugas=penerima,
                    tgl_mulai__lte=akhir,
                    tgl_selesai__gte=mulai,
                    status__in=('menunggu_penerima', 'menunggu_atasan', 'disetujui'),
                ).exclude(pk=pelimpahan.pk).exists()
                if penerima_cuti or penerima_sibuk:
                    raise forms.ValidationError(
                        'Penerima pelimpahan tidak tersedia pada jadwal baru. Revisi penerima tugas terlebih dahulu.'
                    )

        return cleaned


class PerubahanJadwalDecisionForm(forms.Form):
    keputusan = forms.ChoiceField(
        choices=(('setuju', 'Setujui perubahan'), ('tolak', 'Tolak perubahan')),
        widget=forms.RadioSelect,
    )
    catatan = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('keputusan') == 'tolak' and not (cleaned.get('catatan') or '').strip():
            self.add_error('catatan', 'Catatan wajib diisi jika perubahan ditolak.')
        return cleaned


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
            )
            .filter(Q(usulan__status__in=('disetujui', 'selesai')) | Q(usulan__isnull=True))
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
        fields = ('keputusan2', 'catatan2')

    def __init__(self, *args, **kwargs):
        super(Verifikator2CutiForm, self).__init__(*args, **kwargs)
        self.fields['keputusan2'].label = 'Apakah anda menyetujui pengajuan cuti pegawai ini?'
        self.fields['catatan2'].label = 'Catatan persetujuan cuti'


class Verifikator3CutiForm(forms.ModelForm):
    keputusan3 = forms.ChoiceField(choices=KEPUTUSAN_INPUT, widget=forms.RadioSelect, required=True, label="Keputusan")
    catatan3 = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Catatan")
    
    class Meta:
        model = VerifikasiCuti
        fields = ('keputusan3', 'catatan3')
    
    def __init__(self, *args, **kwargs):
        super(Verifikator3CutiForm, self).__init__(*args, **kwargs)
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
        if self.request and not self.request.user.is_diklat_admin:
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
        if self.request and self.request.user.is_diklat_admin:
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


class LayananSIPForm(forms.ModelForm):
    class Meta:
        model = LayananSIP
        fields = [
            "pegawai",
            "layanan",
            "ijazah",
            "str_profesi",
            "kecukupan_skp",
        ]

        widgets = {
            "layanan": forms.Select(attrs={"class": "form-control"}),
            "ijazah": forms.Select(attrs={"class": "form-control"}),
            "str_profesi": forms.Select(attrs={"class": "form-control"}),
            "kecukupan_skp": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(LayananSIPForm, self).__init__(*args, **kwargs)
        layanan_sip_qs = JenisLayanan.objects.filter(
            nama__icontains="SIP"
        )
        self.fields["layanan"].queryset = layanan_sip_qs
        if layanan_sip_qs.exists():
            self.fields["layanan"].initial = layanan_sip_qs.first()
            self.fields['layanan'].widget=forms.HiddenInput()

        # self.fields['layanan'].widget = forms.HiddenInput()
        if self.user and not self.user.is_sip_admin:
            self.fields["pegawai"].widget = forms.HiddenInput()
            self.fields["pegawai"].initial = self.user.pk

            self.fields["ijazah"].queryset = RiwayatPendidikan.objects.filter(
                pegawai=self.user
            )
            self.fields["ijazah"].help_text = "Pilih ijazah profesi yang sudah diunggah sebelumnya di Riwayat Pendidikan"

            self.fields["str_profesi"].queryset = RiwayatProfesi.objects.filter(
                pegawai=self.user
            )
            self.fields["str_profesi"].help_text = "Pilih STR profesi yang sudah diunggah sebelumnya di Riwayat Profesi"

        else:
            self.fields["ijazah"].queryset = RiwayatPendidikan.objects.all()
            self.fields["str_profesi"].queryset = RiwayatProfesi.objects.all()


class UploadPersyaratanSIPForm(forms.Form):
    file_ktp = forms.FileField(
        required=False,
        label="KTP",
        validators=[validate_file_size],
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}),
    )
    foto = forms.ImageField(
        required=False,
        label="Foto",
        validators=[validate_file_size],
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
    )
    file_ijazah = forms.FileField(
        required=False,
        label="Ijazah Profesi",
        validators=[validate_file_size],
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}),
    )

    def __init__(self, *args, **kwargs):
        self.layanan_sip = kwargs.pop("layanan_sip")
        super().__init__(*args, **kwargs)
        profil = getattr(self.layanan_sip.pegawai, "profil_user", None)

        if profil and profil.file_ktp:
            self.fields.pop("file_ktp")
        if profil and profil.foto:
            self.fields.pop("foto")
        if not self.layanan_sip.ijazah or self.layanan_sip.ijazah.file_ijazah:
            self.fields.pop("file_ijazah")

    def clean(self):
        cleaned_data = super().clean()
        if not getattr(self.layanan_sip.pegawai, "profil_user", None):
            raise forms.ValidationError("Profil pegawai belum tersedia.")
        if not any(cleaned_data.values()):
            raise forms.ValidationError("Pilih minimal satu dokumen untuk diunggah.")
        return cleaned_data

    def save(self):
        profil = self.layanan_sip.pegawai.profil_user
        profile_fields = []

        if self.cleaned_data.get("file_ktp"):
            profil.file_ktp = self.cleaned_data["file_ktp"]
            profile_fields.append("file_ktp")
        if self.cleaned_data.get("foto"):
            profil.foto = self.cleaned_data["foto"]
            profile_fields.append("foto")
        if profile_fields:
            profil.save(update_fields=profile_fields + ["updated_at"])

        if self.cleaned_data.get("file_ijazah"):
            ijazah = self.layanan_sip.ijazah
            ijazah.file_ijazah = self.cleaned_data["file_ijazah"]
            ijazah.save(update_fields=["file_ijazah", "updated_at"])

        self.layanan_sip.save(update_fields=["is_ktp", "is_foto", "updated_at"])


class UploadRekomendasiSIPForm(forms.ModelForm):
    class Meta:
        model = LayananSIP
        fields = ["kecukupan_skp", "surat_permohonan_rekomendasi", "surat_rekomendasi_sip"]
        widgets = {
            "kecukupan_skp": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
            "surat_permohonan_rekomendasi": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
            "surat_rekomendasi_sip": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Pegawai membuat surat kecukupan SKP. Surat rekomendasi final
        # hanya boleh diunggah oleh admin.
        if user and not user.is_sip_admin:
            self.fields.pop("surat_rekomendasi_sip")

        if user and user.is_sip_admin:
            self.fields.pop("kecukupan_skp")
            self.fields.pop("surat_permohonan_rekomendasi")

    def clean(self):
        cleaned_data = super().clean()
        if not any(field_name in self.files for field_name in self.fields):
            raise forms.ValidationError(
                "Pilih minimal satu file yang akan diunggah atau menggantikan file lama."
            )
        return cleaned_data
