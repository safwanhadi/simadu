from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UsernameField
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.forms import UserCreationForm
from django.forms import inlineformset_factory
from django.db import transaction
from .models import AccountRegistration, Users, ProfilSDM
from .roles import ADMIN_GROUPS
from strukturorg.models import (
    Bidang, InstansiDaerah, PejabatStruktur, SatuanKerjaInduk, SubBidang,
    UnitInstalasi, UnitOrganisasi,
)


class UpdateUser(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = Users
        fields = ['email', 'first_name', 'last_name']


class AdminResetPasswordForm(SetPasswordForm):
    """Form reset kata sandi oleh Admin Akun dengan validator Django."""

    new_password1 = forms.CharField(
        label='Kata sandi baru',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
    )
    new_password2 = forms.CharField(
        label='Konfirmasi kata sandi baru',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
    )


class AccountAdminRolesForm(forms.Form):
    """Daftar peran yang secara eksplisit boleh dikelola Admin Akun."""

    roles = forms.MultipleChoiceField(
        choices=tuple((role, role) for role in ADMIN_GROUPS),
        required=False,
    )


class StructuralOfficerUserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        nip = getattr(getattr(obj, 'profil_user', None), 'nip', None)
        identity = obj.full_name_2 or obj.email
        return f'{identity} — {nip}' if nip else f'{identity} — {obj.email}'


class StructuralOfficerForm(forms.Form):
    """Aktifkan pejabat pada satu simpul struktur tanpa membuka Django Admin."""

    STRUCTURE_MODELS = (
        ('instansi_daerah', 'Instansi Daerah', InstansiDaerah, 'instansi'),
        ('satuan_kerja_induk', 'Satuan Kerja Induk', SatuanKerjaInduk, 'satuan_kerja'),
        ('unit_organisasi', 'Unit Organisasi', UnitOrganisasi, 'unor'),
        ('bidang', 'Bidang', Bidang, 'bidang'),
        ('sub_bidang', 'Sub Bidang/Seksi', SubBidang, 'sub_bidang'),
        ('unit_instalasi', 'Unit Instalasi', UnitInstalasi, 'instalasi'),
    )
    MODEL_BY_FIELD = {
        field_name: model
        for field_name, _group, model, _label_field in STRUCTURE_MODELS
    }

    pejabat = StructuralOfficerUserChoiceField(
        label='Nama pejabat',
        queryset=Users.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    struktur = forms.ChoiceField(
        label='Lokasi struktur',
        choices=(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Pilih satu unit tempat pegawai tersebut menjabat.',
    )
    jenis_penugasan = forms.ChoiceField(
        label='Jenis penugasan',
        choices=PejabatStruktur.JENIS_PENUGASAN,
        initial=PejabatStruktur.DEFINITIF,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    nama_jabatan = forms.CharField(
        label='Nama jabatan',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contoh: Direktur atau Kepala Bidang Pelayanan',
        }),
        help_text='Boleh dikosongkan untuk menggunakan nama jabatan pada struktur.',
    )
    tanggal_mulai = forms.DateField(
        label='Terhitung mulai tanggal (TMT)',
        initial=date.today,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pejabat'].queryset = (
            Users.objects.filter(is_active=True, is_superuser=False)
            .select_related('profil_user')
            .order_by('first_name', 'last_name', 'email')
        )
        grouped_choices = [('', 'Pilih lokasi struktur')]
        for field_name, group_label, model, label_field in self.STRUCTURE_MODELS:
            options = [
                (f'{field_name}:{obj.pk}', getattr(obj, label_field))
                for obj in model.objects.all().order_by(label_field)
            ]
            if options:
                grouped_choices.append((group_label, options))
        self.fields['struktur'].choices = grouped_choices

    def clean_tanggal_mulai(self):
        value = self.cleaned_data['tanggal_mulai']
        if value > date.today():
            raise forms.ValidationError(
                'TMT pejabat yang langsung diaktifkan tidak boleh di masa depan.'
            )
        return value

    def clean(self):
        cleaned_data = super().clean()
        raw_structure = cleaned_data.get('struktur')
        if not raw_structure:
            return cleaned_data
        try:
            field_name, object_id = raw_structure.split(':', 1)
            model = self.MODEL_BY_FIELD[field_name]
        except (ValueError, KeyError):
            self.add_error('struktur', 'Lokasi struktur tidak valid.')
            return cleaned_data
        try:
            structure = model.objects.get(pk=object_id)
        except model.DoesNotExist:
            self.add_error('struktur', 'Lokasi struktur tidak ditemukan.')
            return cleaned_data

        tanggal_mulai = cleaned_data.get('tanggal_mulai')
        current = structure.riwayat_pejabat.filter(is_active=True).first()
        if current and tanggal_mulai and tanggal_mulai < current.tanggal_mulai:
            self.add_error(
                'tanggal_mulai',
                f'TMT tidak boleh sebelum masa jabatan aktif saat ini ({current.tanggal_mulai:%d-%m-%Y}).',
            )

        cleaned_data['structure_field'] = field_name
        cleaned_data['structure_object'] = structure
        return cleaned_data

    @transaction.atomic
    def save(self):
        structure = self.cleaned_data['structure_object']
        field_name = self.cleaned_data['structure_field']
        jenis = self.cleaned_data['jenis_penugasan']
        nama_jabatan = self.cleaned_data.get('nama_jabatan', '').strip()
        if not nama_jabatan:
            nama_jabatan = structure.pimpinan or 'Pimpinan'
        prefix_by_type = {
            PejabatStruktur.PLT: 'Plt.',
            PejabatStruktur.PLH: 'Plh.',
        }
        prefix = prefix_by_type.get(jenis)
        if prefix and not nama_jabatan.lower().startswith(prefix.lower()):
            nama_jabatan = f'{prefix} {nama_jabatan}'

        return PejabatStruktur.objects.create(
            pejabat=self.cleaned_data['pejabat'],
            jenis_penugasan=jenis,
            nama_jabatan=nama_jabatan,
            tanggal_mulai=self.cleaned_data['tanggal_mulai'],
            is_active=True,
            **{field_name: structure},
        )


class EmployeeRegistrationForm(UserCreationForm):
    """Registrasi mandiri pegawai; akun selalu dibuat dalam keadaan nonaktif."""

    first_name = forms.CharField(label='Nama depan', max_length=30)
    last_name = forms.CharField(label='Nama belakang', max_length=150, required=False)
    email = forms.EmailField(label='Email')
    nip = forms.CharField(label='NIP/NIK pegawai', max_length=18)
    no_hp = forms.CharField(
        label='Nomor HP',
        max_length=20,
        help_text='Gunakan nomor aktif yang juga digunakan pada Telegram.',
    )
    agree_privacy = forms.BooleanField(
        label='Saya menyetujui Kebijakan Privasi SIMADU.',
    )

    class Meta(UserCreationForm.Meta):
        model = Users
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = Users.objects.normalize_email(self.cleaned_data['email']).lower()
        if Users.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email sudah digunakan oleh akun lain.')
        return email

    def clean_nip(self):
        nip = ''.join(char for char in self.cleaned_data['nip'] if char.isdigit())
        if not nip:
            raise forms.ValidationError('NIP/NIK pegawai wajib diisi dengan angka.')
        if len(nip) > 18:
            raise forms.ValidationError('NIP/NIK pegawai maksimal 18 angka.')
        if ProfilSDM.objects.filter(nip=nip).exists():
            raise forms.ValidationError('NIP/NIK pegawai sudah terdaftar.')
        return nip

    def clean_no_hp(self):
        value = self.cleaned_data['no_hp'].strip()
        digits = ''.join(char for char in value if char.isdigit())
        if digits.startswith('62'):
            digits = f'0{digits[2:]}'
        elif digits.startswith('8'):
            digits = f'0{digits}'
        if len(digits) < 10 or len(digits) > 15 or not digits.startswith('0'):
            raise forms.ValidationError('Masukkan nomor HP Indonesia yang valid.')
        return digits

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            ProfilSDM.objects.create(
                user=user,
                nip=self.cleaned_data['nip'],
                no_hp=self.cleaned_data['no_hp'],
                email_pribadi=user.email,
            )
            AccountRegistration.objects.create(user=user)
        return user


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Confirm password', widget=forms.PasswordInput)

    class Meta:
        model = Users
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = Users.objects.filter(email=email)
        if qs.exists():
            raise forms.ValidationError('email has taken')
        return email

    def clean_password2(self):
        # check taht the two password entries match
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Password don't match")
        return password2


class UserAdminCreationForm(forms.ModelForm):
    """
    A form for creating new users. include all the required
    fields, plus a repeated password
    """
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Password Confirm', widget=forms.PasswordInput)

    class Meta:
        model = Users
        fields = ('email',)

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password2 and password2 and password1 != password2:
            raise forms.ValidationError("Password don't match")
        return password2

    def save(self, commit=True):
        # save the provided password in hashed format
        users = super(UserAdminCreationForm, self).save(commit=False)
        users.set_password(self.cleaned_data["password1"])
        if commit:
            users.save()
        return users


class UserAdminChangeForm(forms.ModelForm):
    """
    A Form for updating users. Include all the fields on the user,
    but replaces the password field with admin's password hash display
    field
    """
    password = ReadOnlyPasswordHashField(label=("Password"),
                                         help_text=("Raw passwords are not stored, so there is no way to see "
                                                    "this user's password, but you can change the password "
                                                    "using <a href=\"../password/\">this form</a>."))

    class Meta:
        model = Users
        fields = ('email', 'password', 'is_active')

    def clean_password(self):

        # Regardless of what the user provides, return the initial value
        # This is done here, rather than on the field, because the
        # field does not have acces to the initial value
        return self.initial['password']


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)

    email = UsernameField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': ''}))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={
            'class': 'form-control',
            'placeholder': '',
        }
))


AGAMA = (
    ('Islam', 'Islam'),
    ('Kristen Prtestan', 'Kristen Prtestan'),
    ('Katolik', 'Katolik'),
    ('Budha', 'Budha'),
    ('Hindu', 'Hindu'),
    ('Khonghucu', 'Khonghucu')
)

class ProfilForm(forms.ModelForm):
    agama = forms.ChoiceField(choices=AGAMA, required=False)
    class Meta:
        model = ProfilSDM
        fields = ('user', 'no_hp', 'gender', 'tmp_lahir', 'tgl_lahir', 'nm_ibu', 'alamat', 'gol_darah', 'email_pribadi', 'pendidikan', 'gelar_depan', 'gelar_belakang',
                  'agama', 'stts_nikah', 'nip', 'no_ktp', 'no_npwp', 'no_jkn', 'no_jkk_taspen', 'no_rek_gaji', 'file_ktp', 'file_npwp', 'file_jkn', 'file_taspen', 'file_rek', 'foto')

    def __init__(self, *args, **kwargs):
        bootstrap_col = 'form-control col-12'
        user = kwargs.pop('user', None)
        super(ProfilForm, self).__init__(*args, **kwargs)
        field = self.fields['user']
        if user is not None and not user.is_superuser:
            field.initial = user
            field.widget = field.hidden_widget()
        self.fields['tgl_lahir'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})


class UsersForm(forms.ModelForm):
    class Meta:
        models = Users
        fields = '__all__'
