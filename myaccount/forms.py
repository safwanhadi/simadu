from datetime import date

from django import forms
from django.contrib.auth.models import Group
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UsernameField
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.forms import UserCreationForm
from django.forms import inlineformset_factory
from django.db import transaction
from .models import (
    AccountRegistration, AdminScopeAssignment, CoordinationAssignment,
    ProfilSDM, Users,
)
from .roles import ADMIN_GROUPS
from strukturorg.models import (
    Bidang, InstansiDaerah, PejabatStruktur, SatuanKerjaInduk, SubBidang,
    UnitInstalasi, UnitOrganisasi,
)
from oauth2_provider.models import Application

bootstrap_col = 'form-control col-md-12'
select2_col = f'{bootstrap_col} select2'

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


class SSOApplicationForm(forms.ModelForm):
    """Form aman untuk aplikasi OAuth; secret dikelola melalui aksi rotasi."""

    class Meta:
        model = Application
        fields = (
            'name', 'client_type', 'authorization_grant_type',
            'redirect_uris', 'post_logout_redirect_uris', 'allowed_origins',
            'skip_authorization',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'client_type': forms.Select(attrs={'class': 'form-control'}),
            'authorization_grant_type': forms.Select(attrs={'class': 'form-control'}),
            'redirect_uris': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'post_logout_redirect_uris': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'allowed_origins': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'skip_authorization': forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
        }
        labels = {
            'name': 'Nama aplikasi',
            'client_type': 'Tipe client',
            'authorization_grant_type': 'Jenis grant',
            'redirect_uris': 'Redirect URI',
            'post_logout_redirect_uris': 'Post logout redirect URI',
            'allowed_origins': 'Origin yang diizinkan (CORS)',
            'skip_authorization': 'Lewati halaman persetujuan pengguna',
        }
        help_texts = {
            'redirect_uris': 'Pisahkan beberapa URI dengan spasi.',
            'post_logout_redirect_uris': 'Opsional; pisahkan beberapa URI dengan spasi.',
            'allowed_origins': 'Opsional; contoh: https://aplikasi.example.id',
        }

    def clean(self):
        cleaned = super().clean()
        grant = cleaned.get('authorization_grant_type')
        if (
            grant in (
                Application.GRANT_AUTHORIZATION_CODE,
                Application.GRANT_IMPLICIT,
                Application.GRANT_OPENID_HYBRID,
            )
            and not cleaned.get('redirect_uris', '').strip()
        ):
            self.add_error('redirect_uris', 'Redirect URI wajib untuk jenis grant ini.')
        return cleaned


class AdminScopeAssignmentForm(forms.ModelForm):
    """Kelola satu cakupan struktur untuk satu peran admin."""

    class Meta:
        model = AdminScopeAssignment
        fields = (
            'user',
            'group',
            'scope_type',
            'instansi_daerah',
            'satuan_kerja_induk',
            'unit_organisasi',
            'bidang',
            'sub_bidang',
            'unit_instalasi',
            'valid_from',
            'valid_until',
            'is_active',
        )
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-control admin-scope-select2',
                'data-placeholder': 'Cari nama, email, atau NIP',
            }),
            'group': forms.Select(attrs={
                'class': 'form-control admin-scope-select2',
                'data-placeholder': 'Pilih peran admin',
            }),
            'scope_type': forms.Select(attrs={'class': 'form-control'}),
            'instansi_daerah': forms.Select(attrs={
                'class': 'form-control admin-scope-select2',
                'data-placeholder': 'Cari instansi daerah',
            }),
            'satuan_kerja_induk': forms.Select(attrs={
                'class': 'form-control admin-scope-select2',
                'data-placeholder': 'Cari satuan kerja induk',
            }),
            'unit_organisasi': forms.Select(attrs={
                'class': 'form-control admin-scope-select2',
                'data-placeholder': 'Cari unit organisasi',
            }),
            'bidang': forms.Select(attrs={
                'class': 'form-control admin-scope-select2',
                'data-placeholder': 'Cari bidang',
            }),
            'sub_bidang': forms.Select(attrs={
                'class': 'form-control admin-scope-select2',
                'data-placeholder': 'Cari sub bidang',
            }),
            'unit_instalasi': forms.Select(attrs={
                'class': 'form-control admin-scope-select2',
                'data-placeholder': 'Cari unit instalasi',
            }),
            'valid_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'valid_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'custom-control-input',
            }),
        }
        labels = {
            'user': 'Pengguna',
            'group': 'Peran admin',
            'scope_type': 'Jenis cakupan',
            'valid_from': 'Berlaku mulai',
            'valid_until': 'Berlaku sampai',
            'is_active': 'Assignment aktif',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = (
            Users.objects.filter(is_active=True, is_superuser=False)
            .select_related('profil_user')
            .order_by('first_name', 'last_name', 'email')
        )
        self.fields['group'].queryset = Group.objects.filter(
            name__in=ADMIN_GROUPS
        ).order_by('name')
        self.fields['user'].label_from_instance = self._user_label
        for field_name in AdminScopeAssignment.TARGET_FIELDS:
            self.fields[field_name].required = False
            self.fields[field_name].empty_label = 'Pilih target struktur'

    @staticmethod
    def _user_label(user):
        nip = getattr(getattr(user, 'profil_user', None), 'nip', '')
        identity = user.full_name or user.email
        return f'{identity} - {nip}' if nip else f'{identity} - {user.email}'

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        group = cleaned_data.get('group')
        scope_type = cleaned_data.get('scope_type')

        if user and group and not user.groups.filter(pk=group.pk).exists():
            self.add_error(
                'group',
                'Pengguna belum memiliki peran admin ini. Berikan role terlebih dahulu.',
            )

        selected = [
            field_name for field_name in AdminScopeAssignment.TARGET_FIELDS
            if cleaned_data.get(field_name) is not None
        ]
        if scope_type == AdminScopeAssignment.GLOBAL:
            if selected:
                self.add_error(
                    'scope_type',
                    'Cakupan global tidak memerlukan target struktur.',
                )
        elif scope_type:
            if selected != [scope_type]:
                self.add_error(
                    scope_type,
                    'Pilih tepat satu target yang sesuai dengan jenis cakupan.',
                )
        return cleaned_data


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
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': 'Pilih nama pejabat',
        }),
    )
    struktur = forms.ChoiceField(
        label='Lokasi struktur',
        choices=(),
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': 'Pilih lokasi struktur',
        }),
        help_text='Pilih satu unit tempat pegawai tersebut menjabat.',
    )
    jenis_penugasan = forms.ChoiceField(
        label='Jenis penugasan',
        choices=PejabatStruktur.JENIS_PENUGASAN,
        initial=PejabatStruktur.DEFINITIF,
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': 'Pilih jenis penugasan',
        }),
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


class CoordinationAssignmentForm(forms.ModelForm):
    class Meta:
        model = CoordinationAssignment
        fields = (
            'coordinator', 'employee', 'relation_type', 'valid_from', 'notes',
        )
        widgets = {
            'coordinator': forms.Select(attrs={'class': 'form-control select2'}),
            'employee': forms.Select(attrs={'class': 'form-control select2'}),
            'relation_type': forms.Select(attrs={'class': 'form-control'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        users = Users.objects.filter(
            is_active=True, is_superuser=False
        ).select_related('profil_user').order_by('first_name', 'last_name', 'email')
        self.fields['coordinator'].queryset = users
        self.fields['employee'].queryset = users

    def clean_valid_from(self):
        value = self.cleaned_data['valid_from']
        if value > date.today():
            raise forms.ValidationError('TMT penugasan aktif tidak boleh di masa depan.')
        return value


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
    first_name = forms.CharField(
        label='Nama depan',
        max_length=30,
        required=True,
    )
    last_name = forms.CharField(
        label='Nama belakang',
        max_length=150,
        required=False,
        help_text='Boleh dikosongkan jika nama pegawai hanya terdiri dari satu kata.',
    )
    agama = forms.ChoiceField(choices=AGAMA, required=False)
    class Meta:
        model = ProfilSDM
        fields = ('user', 'no_hp', 'gender', 'tmp_lahir', 'tgl_lahir', 'nm_ibu', 'alamat', 'gol_darah', 'email_pribadi', 'pendidikan', 'gelar_depan', 'gelar_belakang',
                  'agama', 'stts_nikah', 'nip', 'no_ktp', 'no_npwp', 'no_jkn', 'no_jkk_taspen', 'no_rek_gaji', 'file_ktp', 'file_npwp', 'file_jkn', 'file_taspen', 'file_rek', 'foto')

    def __init__(self, *args, **kwargs):
        bootstrap_col = 'form-control col-12'
        user = kwargs.pop('user', None)
        super(ProfilForm, self).__init__(*args, **kwargs)
        self.account = user or getattr(self.instance, 'user', None)
        if self.account is not None:
            self.fields['first_name'].initial = self.account.first_name
            self.fields['last_name'].initial = self.account.last_name
        self.fields.pop('user', None)
        self.order_fields([
            'first_name',
            'last_name',
            *(
                field_name for field_name in self.fields
                if field_name not in {'first_name', 'last_name'}
            ),
        ])
        self.fields['tgl_lahir'].widget = forms.TextInput(attrs={'type':'date', 'class':bootstrap_col})

    def clean_first_name(self):
        return self.cleaned_data['first_name'].strip()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].strip()

    def save(self, commit=True):
        if not self.instance.user_id and self.account is not None:
            self.instance.user = self.account
        profil = super().save(commit=commit)
        account = profil.user
        account.first_name = self.cleaned_data['first_name']
        account.last_name = self.cleaned_data['last_name']
        if commit:
            account.save(update_fields=['first_name', 'last_name'])
        return profil


class UsersForm(forms.ModelForm):
    class Meta:
        models = Users
        fields = '__all__'
