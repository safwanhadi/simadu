from django import forms
from django.utils.translation import gettext_lazy as _
from .models import LayananCuti, VerifikasiCuti
from .services import CheckCuti
from myaccount.models import Users
from datetime import date

class LayananCutiForm(forms.ModelForm):
    class Meta:
        model = LayananCuti
        fields = [
            'pegawai', 'layanan', 'jenis_jabatan', 'status', 'tahun'
        ]
        widgets = {
            'pegawai': forms.Select(attrs={'class': 'form-control'}),
            'layanan': forms.Select(attrs={'class': 'form-control'}),
            'jenis_jabatan': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'tahun': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_tgl_mulai(self):
        tgl_mulai = self.cleaned_data.get('tgl_mulai')
        if tgl_mulai:
            check_cuti = CheckCuti()
            if not check_cuti.cek_waktu_pengajuan_cuti(tgl_mulai):
                raise forms.ValidationError(
                    _('Pengajuan cuti harus dilakukan minimal 7 hari sebelum tanggal mulai cuti')
                )
        return tgl_mulai

    def clean(self):
        cleaned_data = super().clean()
        tgl_mulai = cleaned_data.get('tgl_mulai')
        tgl_akhir = cleaned_data.get('tgl_akhir')
        jenis_cuti = cleaned_data.get('jenis_cuti')

        if tgl_mulai and tgl_akhir:
            if tgl_mulai > tgl_akhir:
                raise forms.ValidationError(_('Tanggal mulai tidak boleh lebih besar dari tanggal akhir'))

            # Check sisa cuti untuk cuti tahunan
            if jenis_cuti == 'Cuti Tahunan' and self.user:
                check_cuti = CheckCuti()
                sisa_cuti = check_cuti.cek_sisa_cuti(self.user)
                lama_cuti = (tgl_akhir - tgl_mulai).days + 1
                
                if lama_cuti > sisa_cuti:
                    raise forms.ValidationError(
                        _(f'Sisa cuti Anda tidak mencukupi. Sisa cuti: {sisa_cuti} hari, '
                          f'yang diajukan: {lama_cuti} hari')
                    )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.user:
            instance.pegawai = self.user
        
        # Calculate lama_cuti and tahun_cuti
        if instance.tgl_mulai and instance.tgl_akhir:
            instance.lama_cuti = (instance.tgl_akhir - instance.tgl_mulai).days + 1
            instance.tahun_cuti = instance.tgl_mulai.year
        
        if commit:
            instance.save()
        return instance


class VerifikasiCutiForm(forms.ModelForm):
    """Form untuk verifikasi/persetujuan cuti menggunakan model VerifikasiCuti yang lebih efisien"""
    class Meta:
        model = VerifikasiCuti
        fields = []  # Will be set dynamically based on level
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.layanan_cuti = kwargs.pop('layanan_cuti', None)
        self.level = kwargs.pop('level', None)  # 1, 2, or 3
        super().__init__(*args, **kwargs)
        
        if self.level and self.layanan_cuti:
            self._setup_fields_for_level()
    
    def _setup_fields_for_level(self):
        """Setup form fields based on approval level"""
        # Get existing verification or create new one
        if self.layanan_cuti.verifikasi.exists():
            verifikasi = self.layanan_cuti.verifikasi.first()
        else:
            verifikasi = VerifikasiCuti(layanan_cuti=self.layanan_cuti)
        
        # Determine which fields to show based on current level
        if self.level == 1:
            self.fields['persetujuan1'] = forms.BooleanField(
                label=f'Setujui Level 1 (SubBidang)',
                required=False,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )
            self.fields['catatan1'] = forms.CharField(
                label='Catatan Verifikasi Level 1',
                required=False,
                widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Masukkan catatan jika perlu'})
            )
            
            # Set initial values if they exist
            self.initial['persetujuan1'] = verifikasi.persetujuan1
            self.initial['catatan1'] = verifikasi.catatan1
            
        elif self.level == 2:
            self.fields['persetujuan2'] = forms.BooleanField(
                label=f'Setujui Level 2 (Bidang)',
                required=False,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )
            self.fields['catatan2'] = forms.CharField(
                label='Catatan Verifikasi Level 2',
                required=False,
                widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Masukkan catatan jika perlu'})
            )
            
            # Set initial values if they exist
            self.initial['persetujuan2'] = verifikasi.persetujuan2
            self.initial['catatan2'] = verifikasi.catatan2
            
        elif self.level == 3:
            self.fields['persetujuan3'] = forms.BooleanField(
                label=f'Setujui Level 3 (Unor)',
                required=False,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )
            self.fields['catatan3'] = forms.CharField(
                label='Catatan Verifikasi Level 3',
                required=False,
                widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Masukkan catatan jika perlu'})
            )
            
            # Set initial values if they exist
            self.initial['persetujuan3'] = verifikasi.persetujuan3
            self.initial['catatan3'] = verifikasi.catatan3

    def clean(self):
        cleaned_data = super().clean()
        
        # Validation logic based on level
        if self.level == 1:
            persetujuan = cleaned_data.get('persetujuan1', False)
            catatan = cleaned_data.get('catatan1', '')
            
            # If rejecting, catatan is required
            if not persetujuan and not catatan.strip():
                raise forms.ValidationError({
                    'catatan1': 'Catatan harus diisi jika menolak pengajuan cuti'
                })
                
        elif self.level == 2:
            persetujuan = cleaned_data.get('persetujuan2', False)
            catatan = cleaned_data.get('catatan2', '')
            
            if not persetujuan and not catatan.strip():
                raise forms.ValidationError({
                    'catatan2': 'Catatan harus diisi jika menolak pengajuan cuti'
                })
                
        elif self.level == 3:
            persetujuan = cleaned_data.get('persetujuan3', False)
            catatan = cleaned_data.get('catatan3', '')
            
            if not persetujuan and not catatan.strip():
                raise forms.ValidationError({
                    'catatan3': 'Catatan harus diisi jika menolak pengajuan cuti'
                })
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Get or create verification record
        if not self.layanan_cuti.verifikasi.exists():
            instance.layanan_cuti = self.layanan_cuti
        
        # Set approval for current level
        if self.level == 1:
            instance.verifikator1 = self.user
            instance.persetujuan1 = self.cleaned_data.get('persetujuan1', False)
            instance.catatan1 = self.cleaned_data.get('catatan1', '')
        elif self.level == 2:
            instance.verifikator2 = self.user
            instance.persetujuan2 = self.cleaned_data.get('persetujuan2', False)
            instance.catatan2 = self.cleaned_data.get('catatan2', '')
        elif self.level == 3:
            instance.verifikator3 = self.user
            instance.persetujuan3 = self.cleaned_data.get('persetujuan3', False)
            instance.catatan3 = self.cleaned_data.get('catatan3', '')
        
        if commit:
            instance.save()
        return instance


# class PersetujuanCutiForm(forms.ModelForm):
#     """Form untuk persetujuan cuti (legacy, menggunakan PersetujuanCuti)"""
#     class Meta:
#         model = PersetujuanCuti
#         fields = ['status', 'catatan']
#         widgets = {
#             'status': forms.Select(attrs={'class': 'form-control'}),
#             'catatan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#         }

#     def __init__(self, *args, **kwargs):
#         self.user = kwargs.pop('user', None)
#         self.layanan_cuti = kwargs.pop('layanan_cuti', None)
#         super().__init__(*args, **kwargs)
        
#         # Add custom choices for status
#         self.fields['status'].choices = [
#             ('', '-- Pilih Status --'),
#             ('Approved', 'Setujui'),
#             ('Rejected', 'Tolak')
#         ]
#         self.fields['status'].required = True

#     def clean(self):
#         cleaned_data = super().clean()
#         status = cleaned_data.get('status')
#         catatan = cleaned_data.get('catatan')

#         if status == 'Rejected' and not catatan:
#             raise forms.ValidationError(_('Catatan harus diisi jika menolak pengajuan cuti'))

#         return cleaned_data


class CutiFilterForm(forms.Form):
    """Form untuk filter daftar cuti"""
    STATUS_CHOICES = [('', '-- Semua Status --')] + LayananCuti.STATUS_CHOICES
    JENIS_CHOICES = [('', '-- Semua Jenis --')] + LayananCuti.JENIS_CHOICES
    
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    jenis_cuti = forms.ChoiceField(choices=JENIS_CHOICES, required=False)
    tanggal_mulai = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    tanggal_akhir = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    pegawai = forms.ModelChoiceField(
        queryset=Users.objects.all(), 
        required=False,
        empty_label="-- Semua Pegawai --"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class CutiTundaForm(forms.ModelForm):
    """Form khusus untuk pengajuan cuti tertunda"""
    class Meta:
        model = LayananCuti
        fields = ['alasan_cuti', 'tgl_mulai', 'tgl_akhir', 'alamat_cuti', 'no_telp']
        widgets = {
            'alasan_cuti': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'tgl_mulai': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tgl_akhir': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'alamat_cuti': forms.TextInput(attrs={'class': 'form-control'}),
            'no_telp': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['alasan_cuti'].label = 'Alasan Cuti Tertunda'

    def clean(self):
        cleaned_data = super().clean()
        tgl_mulai = cleaned_data.get('tgl_mulai')
        tgl_akhir = cleaned_data.get('tgl_akhir')

        if tgl_mulai and tgl_akhir:
            if tgl_mulai > tgl_akhir:
                raise forms.ValidationError(_('Tanggal mulai tidak boleh lebih besar dari tanggal akhir'))

            # Check if this is a valid tunda cuti request
            check_cuti = CheckCuti()
            if not check_cuti.cek_waktu_pengajuan_cuti_tunda(tgl_mulai.year):
                raise forms.ValidationError(
                    _('Pengajuan cuti tertunda hanya dapat dilakukan untuk tahun berjalan')
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.user:
            instance.pegawai = self.user
            instance.jenis_cuti = 'Cuti Tertunda'
        
        # Calculate lama_cuti and tahun_cuti
        if instance.tgl_mulai and instance.tgl_akhir:
            instance.lama_cuti = (instance.tgl_akhir - instance.tgl_mulai).days + 1
            instance.tahun_cuti = instance.tgl_mulai.year
        
        if commit:
            instance.save()
        return instance