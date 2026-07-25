from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView, TemplateView, UpdateView, DetailView, CreateView
from django.contrib.auth import logout
from django.contrib.auth.models import Group
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView
from django.contrib.messages.views import SuccessMessageMixin
import os
from django.http import JsonResponse
from django.db.models import Q
from django.db import transaction
from django.utils import timezone

from urllib.parse import urlencode
from django.conf import settings
from django.http import Http404
from django.core.paginator import Paginator


from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models.functions import ExtractMonth, ExtractDay

# SIMADU views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ProfilSDM

from .models import AccountRegistration, ProfilSDM, Users
from .forms import (
    AccountAdminRolesForm,
    AdminResetPasswordForm,
    EmployeeRegistrationForm,
    ProfilForm,
    StructuralOfficerForm,
    UserAdminChangeForm,
)
import logging
from .roles import ADMIN_DOKUMEN, ADMIN_GROUPS
from strukturorg.models import PejabatStruktur


class AccountAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Batasi pengelolaan akun untuk superuser atau anggota grup Admin Akun."""

    def test_func(self):
        return self.request.user.is_akun_admin


class AccountManagementListView(AccountAdminRequiredMixin, ListView):
    model = Users
    template_name = 'account_management/list.html'
    context_object_name = 'account_list'
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            Users.objects
            .select_related('profil_user')
            .prefetch_related('groups')
            .exclude(is_superuser=True)
            .exclude(registration_request__status__in=(
                AccountRegistration.PENDING,
                AccountRegistration.REJECTED,
            ))
            .order_by('is_active', 'first_name', 'last_name', 'email')
        )
        status = self.request.GET.get('status', '').strip()
        if status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status == 'active':
            queryset = queryset.filter(is_active=True)
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(profil_user__nip__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for account in context['account_list']:
            account.admin_role_names = {
                group.name
                for group in account.groups.all()
                if group.name in ADMIN_GROUPS
            }
        context.update({
            'q': self.request.GET.get('q', '').strip(),
            'status': self.request.GET.get('status', '').strip(),
            'inactive_count': Users.objects.filter(
                is_active=False,
                is_superuser=False,
            ).exclude(registration_request__status__in=(
                AccountRegistration.PENDING,
                AccountRegistration.REJECTED,
            )).count(),
            'pending_registration_count': AccountRegistration.objects.filter(
                status=AccountRegistration.PENDING,
            ).count(),
            'admin_roles': ADMIN_GROUPS,
            'account_management': 'active',
            'card_title': 'Pengelolaan Akun',
            'title_page': 'Pengelolaan Akun',
        })
        return context


class StructuralOfficerManagementView(AccountAdminRequiredMixin, FormView):
    form_class = StructuralOfficerForm
    template_name = 'account_management/structural_officers.html'
    success_url = reverse_lazy('myaccount_urls:structural_officer_management')

    def get_queryset(self):
        queryset = PejabatStruktur.objects.select_related(
            'pejabat',
            'pejabat__profil_user',
            'instansi_daerah',
            'satuan_kerja_induk',
            'unit_organisasi',
            'bidang',
            'sub_bidang',
            'unit_instalasi',
        )
        status = self.request.GET.get('status', 'active').strip()
        if status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status != 'all':
            status = 'active'
            queryset = queryset.filter(is_active=True)

        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(pejabat__email__icontains=query)
                | Q(pejabat__first_name__icontains=query)
                | Q(pejabat__last_name__icontains=query)
                | Q(pejabat__profil_user__nip__icontains=query)
                | Q(nama_jabatan__icontains=query)
                | Q(instansi_daerah__instansi__icontains=query)
                | Q(satuan_kerja_induk__satuan_kerja__icontains=query)
                | Q(unit_organisasi__unor__icontains=query)
                | Q(bidang__bidang__icontains=query)
                | Q(sub_bidang__sub_bidang__icontains=query)
                | Q(unit_instalasi__instalasi__icontains=query)
            )
        return queryset, status, query

    def form_valid(self, form):
        appointment = form.save()
        messages.success(
            self.request,
            f'{appointment.get_jenis_penugasan_display()} {appointment.pejabat.full_name_2} '
            f'berhasil diaktifkan sebagai {appointment.nama_jabatan} pada '
            f'{appointment.struktur_object}.',
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset, status, query = self.get_queryset()
        paginator = Paginator(queryset, 25)
        page_obj = paginator.get_page(self.request.GET.get('page'))
        context.update({
            'appointment_list': page_obj.object_list,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'q': query,
            'status': status,
            'today': date.today(),
            'active_count': PejabatStruktur.objects.filter(is_active=True).count(),
            'temporary_count': PejabatStruktur.objects.filter(
                is_active=True,
                jenis_penugasan__in=(PejabatStruktur.PLT, PejabatStruktur.PLH),
            ).count(),
            'account_management': 'active',
            'card_title': 'Pejabat Struktural',
            'title_page': 'Pengelolaan Pejabat Struktural',
        })
        return context


class StructuralOfficerDeactivateView(AccountAdminRequiredMixin, View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        appointment = get_object_or_404(
            PejabatStruktur.objects.select_for_update().select_related('pejabat'),
            pk=kwargs['pk'],
            is_active=True,
        )
        raw_date = request.POST.get('tanggal_selesai', '').strip()
        try:
            end_date = date.fromisoformat(raw_date) if raw_date else date.today()
        except ValueError:
            messages.error(request, 'Tanggal selesai tidak valid.')
            return redirect('myaccount_urls:structural_officer_management')
        if end_date < appointment.tanggal_mulai or end_date > date.today():
            messages.error(
                request,
                'Tanggal selesai harus berada di antara TMT dan tanggal hari ini.',
            )
            return redirect('myaccount_urls:structural_officer_management')

        appointment.is_active = False
        appointment.tanggal_selesai = end_date
        appointment.save()
        messages.success(
            request,
            f'Masa jabatan {appointment.pejabat.full_name_2} pada '
            f'{appointment.struktur_object} berhasil ditutup.',
        )
        return redirect('myaccount_urls:structural_officer_management')


class EmployeeRegistrationView(FormView):
    form_class = EmployeeRegistrationForm
    template_name = 'registration/account_register.html'
    success_url = reverse_lazy('myaccount_urls:account_registration_success')

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class EmployeeRegistrationSuccessView(TemplateView):
    template_name = 'registration/account_register_success.html'


class AccountRegistrationReviewListView(AccountAdminRequiredMixin, ListView):
    model = AccountRegistration
    template_name = 'account_management/registration_list.html'
    context_object_name = 'registration_list'
    paginate_by = 25

    def get_queryset(self):
        queryset = AccountRegistration.objects.select_related(
            'user',
            'user__profil_user',
            'reviewed_by',
        )
        status = self.request.GET.get('status', AccountRegistration.PENDING)
        valid_statuses = {
            AccountRegistration.PENDING,
            AccountRegistration.APPROVED,
            AccountRegistration.REJECTED,
        }
        if status in valid_statuses:
            queryset = queryset.filter(status=status)
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(user__email__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__profil_user__nip__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'q': self.request.GET.get('q', '').strip(),
            'status': self.request.GET.get('status', AccountRegistration.PENDING),
            'pending_count': AccountRegistration.objects.filter(
                status=AccountRegistration.PENDING,
            ).count(),
            'account_registration_review': 'active',
            'card_title': 'Verifikasi Registrasi Akun',
            'title_page': 'Verifikasi Registrasi Akun',
        })
        return context


class AccountRegistrationActionMixin(AccountAdminRequiredMixin):
    def get_registration(self, statuses):
        return get_object_or_404(
            AccountRegistration.objects.select_related('user'),
            pk=self.kwargs['pk'],
            status__in=statuses,
            user__is_superuser=False,
        )


class AccountRegistrationApproveView(AccountRegistrationActionMixin, View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        registration = self.get_registration((
            AccountRegistration.PENDING,
            AccountRegistration.REJECTED,
        ))
        registration.user.is_active = True
        registration.user.save(update_fields=['is_active'])
        registration.status = AccountRegistration.APPROVED
        registration.reviewed_at = timezone.now()
        registration.reviewed_by = request.user
        registration.save(update_fields=['status', 'reviewed_at', 'reviewed_by'])
        messages.success(
            request,
            f'Registrasi {registration.user.email} disetujui dan akun telah aktif.',
        )
        return redirect('myaccount_urls:account_registration_review_list')


class AccountRegistrationRejectView(AccountRegistrationActionMixin, View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        registration = self.get_registration((AccountRegistration.PENDING,))
        registration.user.is_active = False
        registration.user.save(update_fields=['is_active'])
        registration.status = AccountRegistration.REJECTED
        registration.reviewed_at = timezone.now()
        registration.reviewed_by = request.user
        registration.save(update_fields=['status', 'reviewed_at', 'reviewed_by'])
        messages.success(request, f'Registrasi {registration.user.email} ditolak.')
        return redirect('myaccount_urls:account_registration_review_list')


class AccountActionMixin(AccountAdminRequiredMixin):
    def get_target(self):
        # Akun superuser tidak boleh dimutasi dari menu operasional ini.
        return get_object_or_404(
            Users.objects.exclude(is_superuser=True).exclude(
                registration_request__status__in=(
                    AccountRegistration.PENDING,
                    AccountRegistration.REJECTED,
                ),
            ),
            pk=self.kwargs['pk'],
        )


class AccountToggleActiveView(AccountActionMixin, View):
    def post(self, request, *args, **kwargs):
        target = self.get_target()
        if target.pk == request.user.pk:
            messages.error(request, 'Anda tidak dapat menonaktifkan akun sendiri.')
        else:
            target.is_active = not target.is_active
            target.save(update_fields=['is_active'])
            status = 'diaktifkan' if target.is_active else 'dinonaktifkan'
            messages.success(request, f'Akun {target.email} berhasil {status}.')
        return redirect('myaccount_urls:account_management_list')


class AccountToggleStaffView(AccountActionMixin, View):
    def post(self, request, *args, **kwargs):
        target = self.get_target()
        if target.pk == request.user.pk:
            messages.error(request, 'Anda tidak dapat mengubah status staff akun sendiri.')
        else:
            target.is_staff = not target.is_staff
            target.save(update_fields=['is_staff'])
            status = 'dijadikan staff' if target.is_staff else 'dihapus dari staff'
            messages.success(request, f'Akun {target.email} berhasil {status}.')
        return redirect('myaccount_urls:account_management_list')


class AccountToggleDocumentAdminView(AccountActionMixin, View):
    def post(self, request, *args, **kwargs):
        target = self.get_target()
        if target.pk == request.user.pk:
            messages.error(
                request,
                'Anda tidak dapat mengubah peran Admin Dokumen akun sendiri.',
            )
        else:
            group, _ = Group.objects.get_or_create(name=ADMIN_DOKUMEN)
            if target.groups.filter(pk=group.pk).exists():
                target.groups.remove(group)
                status = 'dicabut'
            else:
                target.groups.add(group)
                status = 'diberikan'
            messages.success(
                request,
                f'Peran Admin Dokumen untuk {target.email} berhasil {status}.',
            )
        return redirect('myaccount_urls:account_management_list')


class AccountUpdateAdminRolesView(AccountActionMixin, View):
    """Ganti seluruh peran admin SIMADU tanpa mengubah grup non-admin."""

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        target = self.get_target()
        if target.pk == request.user.pk:
            messages.error(
                request,
                'Anda tidak dapat mengubah hak akses admin akun sendiri.',
            )
            return redirect('myaccount_urls:account_management_list')

        form = AccountAdminRolesForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Pilihan hak akses admin tidak valid.')
            return redirect('myaccount_urls:account_management_list')

        selected_names = set(form.cleaned_data['roles'])
        current_admin_groups = list(
            target.groups.filter(name__in=ADMIN_GROUPS)
        )
        selected_groups = []
        for role_name in ADMIN_GROUPS:
            if role_name in selected_names:
                group, _created = Group.objects.get_or_create(name=role_name)
                selected_groups.append(group)

        if current_admin_groups:
            target.groups.remove(*current_admin_groups)
        if selected_groups:
            target.groups.add(*selected_groups)

        if selected_names:
            role_summary = ', '.join(
                role for role in ADMIN_GROUPS if role in selected_names
            )
            messages.success(
                request,
                f'Hak akses admin {target.email} diperbarui: {role_summary}.',
            )
        else:
            messages.success(
                request,
                f'Seluruh hak akses admin {target.email} berhasil dicabut.',
            )
        return redirect('myaccount_urls:account_management_list')


class AccountResetPasswordView(AccountActionMixin, FormView):
    form_class = AdminResetPasswordForm
    template_name = 'account_management/reset_password.html'

    def dispatch(self, request, *args, **kwargs):
        self.target = self.get_target()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.target
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            f'Kata sandi akun {self.target.email} berhasil direset.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('myaccount_urls:account_management_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'target': self.target,
            'account_management': 'active',
            'card_title': 'Reset Kata Sandi',
            'title_page': 'Reset Kata Sandi Akun',
        })
        return context

logger = logging.getLogger(__name__)


class PrivacyPolicyView(TemplateView):
    template_name = 'privacy_policy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['privacy_contact_email'] = settings.PRIVACY_CONTACT_EMAIL
        return context


class AboutSimaduView(TemplateView):
    template_name = 'about_simadu.html'


class SimaduLoginView(LoginView):
    template_name = 'sso/login.html'

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name)
        sso_url = reverse('myaccount_urls:sso_portal')
        # dashboard_url = reverse('dashboard_urls:dashboard_view')
        # dashboard_absensi_url = reverse('dashboard_urls:dashboard_absensi_view')
        # riwayat_url = reverse('riwayat_urls:riwayat_view')
        # if self.request.user.is_superuser:
        #     return redirect_to if redirect_to else dashboard_url
        # else:
        #     return redirect_to if redirect_to else dashboard_absensi_url
        return redirect_to if redirect_to else sso_url
    

def logout_view(request):
    logout(request)
    return redirect(reverse('myaccount_urls:login_view'))


def back_view(request):
    return redirect(reverse('myaccount_urls:sso_portal'))


class ChangePassword(PasswordChangeView):
    template_name = 'change_password.html'       
    
    def get_success_url(self) -> str:
        return reverse('myaccount_urls:ganti_password_done_view')

class ChangePasswordDone(PasswordChangeDoneView):
    template_name = 'change_password_done.html'
    title = "Password berhasil diganti!"


class ProfilView(LoginRequiredMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def get_object(self):
        user = self.request.user
        try:
            data = ProfilSDM.objects.get(user=user)
            return data
        except Exception:
            return None
        
    def get(self, request):
        data = self.get_object()
        initial = {'user': request.user}
        form = ProfilForm(instance=data, initial=initial)
        context={
            'data':data,
            'form':form,
            'profil':'active',
        }
        return render(request, 'profil.html', context)
    
    def post(self, request):
        data_detail = self.get_object()
        instance = self.get_object()
        form = ProfilForm(data=request.POST, files=request.FILES, instance=instance)
        if form.is_valid():
            riwayat_profil = form.save(commit=False)
            nip = form.cleaned_data.get('nip')
            riwayat_profil.nip = nip.replace('.', '').replace(' ', '')
            if data_detail is not None:
                if data_detail.file_ktp and riwayat_profil.file_ktp and data_detail.file_ktp != riwayat_profil.file_ktp and os.path.exists(data_detail.file_ktp.path):
                    os.remove(data_detail.file_ktp.path)
                if data_detail.file_jkn and riwayat_profil.file_jkn and data_detail.file_jkn != riwayat_profil.file_jkn and os.path.exists(data_detail.file_jkn.path):
                    os.remove(data_detail.file_jkn.path)
                if data_detail.file_npwp and riwayat_profil.file_npwp and data_detail.file_npwp != riwayat_profil.file_npwp and os.path.exists(data_detail.file_npwp.path):
                    os.remove(data_detail.file_npwp.path)
                if data_detail.file_taspen and riwayat_profil.file_taspen and data_detail.file_taspen != riwayat_profil.file_taspen and os.path.exists(data_detail.file_taspen.path):
                    os.remove(data_detail.file_taspen.path)
                if data_detail.file_rek and riwayat_profil.file_rek and data_detail.file_rek != riwayat_profil.file_rek and os.path.exists(data_detail.file_rek.path):
                    os.remove(data_detail.file_rek.path)
                if data_detail.foto and riwayat_profil.foto and data_detail.foto != riwayat_profil.foto and os.path.exists(data_detail.foto.path):
                    os.remove(data_detail.foto.path)
            
            riwayat_profil.save()
            messages.success(request, 'Data berhasi disimpan!')
            return redirect(reverse('myaccount_urls:profil_view'))
        for field, errors in form.errors.items():
            for error in errors:
                if error:
                    messages.error(request, error)
                else:
                    messages.error(request, 'Maaf data gagal ditambahkan!')
        return redirect(reverse('myaccount_urls:profil_view'))
    

class ProfilCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = ProfilSDM
    template_name = 'profil_form.html'
    success_message = 'Profil berhasil disimpan!'
    form_class = ProfilForm
    
    def get_success_url(self) -> str:
        if self.request.user.is_superuser:
            url = reverse_lazy('myaccount_urls:profil_view')
        else:
            url = reverse_lazy('myaccount_urls:profil_detail_view', kwargs={'pk':self.request.user.pk})
        return url
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    

class ProfilDetailView(SuccessMessageMixin, LoginRequiredMixin, DetailView):
    model = ProfilSDM
    template_name = 'profil_detail.html'

    
class ProfilListView(SuccessMessageMixin, LoginRequiredMixin, ListView):
    model = Users
    template_name = 'profil.html'

    def get_queryset(self):
        if self.request.user.is_superuser:
            queryset = Users.objects.all()
        else:
            queryset = Users.objects.filter(id=self.request.user.id) 
        return queryset
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'profil'
        return ctx
    

class ProfilUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = ProfilSDM
    form_class = ProfilForm
    template_name = 'profil_form.html'
    success_message = 'Data berhasil diupdate'

    def get_success_url(self) -> str:
        if self.request.user.is_superuser:
            url = reverse_lazy('myaccount_urls:profil_view')
        else:
            url = reverse_lazy('myaccount_urls:profil_detail_view', kwargs={'pk':self.request.user.pk})
        return url

    def form_valid(self, form):
        # Get the old file
        old_file_ktp = self.get_object().file_ktp
        old_file_jkn = self.get_object().file_jkn
        old_file_npwp = self.get_object().file_npwp
        old_file_taspen = self.get_object().file_taspen
        old_file_rek = self.get_object().file_rek
        response = super().form_valid(form)

        # Check if a new file is being uploaded
        new_file_ktp = form.cleaned_data.get('your_file')
        if new_file_ktp and old_file_ktp and old_file_ktp != new_file_ktp:
            if os.path.isfile(old_file_ktp.path):
                os.remove(old_file_ktp.path)
        new_file_jkn = form.cleaned_data.get('your_file')
        if new_file_jkn and old_file_jkn and old_file_jkn != new_file_jkn:
            if os.path.isfile(old_file_jkn.path):
                os.remove(old_file_jkn.path)
        new_file_npwp = form.cleaned_data.get('your_file')
        if new_file_npwp and old_file_npwp and old_file_npwp != new_file_npwp:
            if os.path.isfile(old_file_npwp.path):
                os.remove(old_file_npwp.path)
        new_file_taspen = form.cleaned_data.get('your_file')
        if new_file_taspen and old_file_taspen and old_file_taspen != new_file_taspen:
            if os.path.isfile(old_file_taspen.path):
                os.remove(old_file_taspen.path)
        new_file_rek = form.cleaned_data.get('your_file')
        if new_file_rek and old_file_rek and old_file_rek != new_file_rek:
            if os.path.isfile(old_file_rek.path):
                os.remove(old_file_rek.path)
                
        return response
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method == 'POST':
            kwargs['files'] = self.request.FILES
        return kwargs
    

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    return Response({
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "id": u.pk,
    })

def sso_portal(request):
    # opsional: kalau ingin portal bisa diakses tanpa login, biarkan saja.
    # kalau ingin wajib login SIMADU dulu, tinggal cek request.user.is_authenticated.
    if request.user.is_authenticated:
        clients = settings.SSO_CLIENTS
        Visuals = settings.APP_VISUAL
        # identifikasi IP user untuk development: kalau IP localhost sembunyikan icon aplikasi kecuali untuk Tim IT
        # atau ambil di setting client SSO yang sudah ditentukan
        user_ip = get_client_ip(request)
        # Ganti dengan IP Publik/Lokal resmi Rumah Sakit Anda
        RS_IP_RANGE = "192.168."  # Contoh jika server mendeteksi IP lokal langsung
        # Atau IP publik statis RS: "112.x.x.x"
        # is_dev_ip = user_ip.startswith(RS_IP_RANGE) or user_ip == "127.0.0.1"
        is_dev_ip = user_ip == "127.0.0.1"
        
        
        # Ambil satu data riwayat terakhir berdasarkan tanggal SK terbaru
        riwayat_terakhir = request.user.riwayatjabatan_set.order_by('-tmt_jabatan').first()

        if riwayat_terakhir:
            user_jabatan = getattr(riwayat_terakhir, 'nama_jabatan', '')
            user_jabatan = user_jabatan.slug if user_jabatan else ''
        else:
            user_jabatan = ''
        
        apps = []
        for key, client in clients.items():
            visual = Visuals.get(key, {})
            # untuk filter url apakah local url atau tidak
            actual_url = client.get("redirect_uri", "")
            is_dev = True if (actual_url.startswith("http://localhost") or actual_url.startswith("http://127.0.0.1")) and user_jabatan == "it" else False
            app_data = {
                "id": client.get("client_id", ""),
                "key": key,
                "name": client.get("label", key),
                "url": actual_url,
                "login_url": client.get("login_url"),
                "type": client.get("type"),
                "icon": visual.get("icon", "fas fa-th-large"),
                "bg_class": visual.get("bg_class", "bg-gradient-to-br from-blue-500 to-blue-600"),
                "category": visual.get("category", "Umum"),
                "is_dev": is_dev,
            }
            apps.append(app_data)

        return render(request, "sso/portal.html", {"apps": apps})
    else:
        return redirect(reverse('myaccount_urls:login_view') + f"?{urlencode({'next': reverse('myaccount_urls:sso_portal')})}")
    

def sso_go(request, client_key):
    clients = settings.SSO_CLIENTS
    if client_key not in clients:
        raise Http404("Client tidak ditemukan")

    c = clients[client_key]

    # Kalau SIMADU sendiri: pakai login internal Django (LoginView)
    if c["type"] == "local":
        # next_url = request.GET.get("next") or "/"
        if request.user.is_superuser:
            return redirect(f'{c["dashboard"]}')
        else:
            return redirect(f'{c["dashboard_absensi"]}')
        # redirect_to = request.GET.get('next') or "/"
        # dashboard_url = redirect(reverse('dashboard_urls:dashboard_view'))
        # dashboard_absensi_url = redirect(reverse('dashboard_urls:dashboard_absensi_view'))
        # riwayat_url = redirect(reverse('riwayat_urls:riwayat_view'))
        # if request.user.is_superuser:
        #     return redirect_to if redirect_to else dashboard_url
        # else:
        #     return redirect_to if redirect_to else dashboard_absensi_url
        

    # OAuth client: arahkan ke /o/authorize/ milik DOT (SIMADU)
    authorize_url = f"{settings.SSO_AUTH_BASE}/o/authorize/"
    state = request.GET.get("state") or ""  # boleh dipakai untuk CSRF/tujuan
    next_url = request.GET.get("next") or ""  # boleh Anda simpan dalam state juga

    params = {
        "response_type": "code",
        "client_id": c["client_id"],
        "redirect_uri": c["redirect_uri"],
        "scope": c.get("scopes", "read"),
    }

    # kalau mau bawa "next" tujuan akhir di REMUN, taruh di state:
    # misalnya state="next=/dashboard"
    if next_url:
        params["state"] = f"next={next_url}"
    elif state:
        params["state"] = state

    return redirect(f"{authorize_url}?{urlencode(params)}")


# CEK APAKAH JARINGAN LOCAL ATAU TIDAK
from urllib.parse import urlparse
import requests

def cek_jaringan_lokal(request):
    target_url = request.GET.get('target', '').strip()
    
    # 1. Validasi kecocokan target (tetap menggunakan url asli)
    allowed_identifiers = ["172.16.16.", "12.12.12.", "192.168.3.", "dash.rsmandalika.com", "simrs.rsmandalika.com"]
    if not any(id in target_url for id in allowed_identifiers):
        return JsonResponse({'terhubung': False, 'error': 'Target tidak diizinkan'})
    
    # 2. Bersihkan URL untuk pengecekan jaringan
    if not target_url.startswith(('http://', 'https://')):
        target_url = f"https://{target_url}"
        
    try:
        # Ekstrak hanya protokol + domain (misal: https://dash.rsmandalika.com)
        # Ini menghindari error 401/403/404 dari halaman /callback/
        parsed_url = urlparse(target_url)
        base_check_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        
        # print('Melakukan HEAD request ke base domain:', base_check_url)
        
        # Lakukan HEAD request ke base domain
        response = requests.head(
            base_check_url,
            timeout=2,
            allow_redirects=False,
            verify=False,
        )
        
        # Jika server merespon (apapun statusnya, bahkan 404/403 pada base domain, asalkan servernya hidup/merespon)
        # Berarti server tersebut berada di jaringan yang sama/bisa diakses
        if response.status_code:
            return JsonResponse({'terhubung': True})
            
    except requests.RequestException as e:
        print(f"Gagal menjangkau server target karena kendala jaringan: {e}")
        # Jangan hanya pass, pastikan return eksplisit jika terjadi timeout/gagal koneksi
        return JsonResponse({'terhubung': False, 'reason': 'network_unreachable'})

    return JsonResponse({'terhubung': False})


from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Nonaktifkan warning log SSL insecure karena kita menggunakan verify=False di jaringan internal
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def app_gateway(request):
    """
    Gateway Backend untuk memeriksa jaringan lokal sebelum mengalihkan user ke aplikasi private.
    Menerima parameter 'sso' (URL tujuan login) dan 'target' (URL endpoint aplikasi untuk cek ping).
    """
    logger.error('tahap 0')
    sso_url = request.GET.get('sso', '').strip()
    target_url = request.GET.get('target', '').strip()
    
    # JALUR APLIKASI PUBLIC
    # Jika aplikasi tidak memiliki target endpoint khusus, langsung loloskan ke SSO
    if not target_url:
        logger.error('tahap 1')
        return redirect(sso_url)
    
    # 1. Validasi kecocokan target untuk mencegah SSRF
    allowed_identifiers = ["172.16.16.", "12.12.12.", "192.168.3.", "dash.rsmandalika.com", "simrs.rsmandalika.com"]
    is_private_app = any(id in target_url for id in allowed_identifiers)
    
    if is_private_app:
        logger.error('tahap 2')
        # 2. Standarkan skema URL ke HTTPS demi kecepatan (menghindari redirect HTTP -> HTTPS internal)
        if not target_url.startswith(('http://', 'https://')):
            target_url = f"https://{target_url}"
            
        try:
            logger.error('tahap 3')
            # Ekstrak hanya protokol + domain (misal: https://dash.rsmandalika.com)
            parsed_url = urlparse(target_url)
            base_check_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            
            # Lakukan HEAD request ke base domain dengan timeout ketat
            response = requests.head(
                base_check_url,
                timeout=1.5,       # Batas waktu tunggu server merespon
                allow_redirects=False,
                verify=False,      # Abaikan verifikasi SSL self-signed lokal
            )
            
            # Jika server merespon dengan status code apa saja (artinya server hidup & berada di LAN)
            if response.status_code:
                logger.error('tahap 4')
                return redirect(sso_url)
                
        except requests.RequestException as e:
            logger.error('tahap 5')
            print(f"Gateway gagal menjangkau server target lokal: {e}")
            # Jika timeout atau error jaringan, biarkan eksekusi lolos ke halaman blokir di bawah
            pass
            
        # JALUR EKSTERNAL (BLOKIR)
        # Jika blok 'try' gagal atau tidak terhubung, alihkan langsung ke halaman blokir lokal Anda
        return redirect(reverse('myaccount_urls:local_only_blocked'))

    # Fallback default jika tidak lolos validasi privat, alihkan langsung ke SSO aman
    return redirect(sso_url)


def access_denied_view(request):
    # Halaman statis jika diakses dari luar RS tanpa VPN
    return render(request, 'sso/access_denied.html')

# Saya akan membuat fungsi untuk mengidentifikasi IP dev sehingga proses development
# icon aplikasi bisa disembunyikan dari user.
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class PegawaiAutocompleteView(View):
    def get(self, request):
        term = request.GET.get('term', '')
        queryset = Users.objects.filter(Q(first_name__icontains=term)|Q(last_name__icontains=term))[:25]
        results = [
            {
                "id": obj.pk,
                "text": f"{obj.first_name} - {obj.last_name}",
            }
            for obj in queryset
        ]
        return JsonResponse({'results': results})


class UlangTahunSebulanTerakhirListView(LoginRequiredMixin, ListView):
    model = ProfilSDM
    template_name = "pegawai_ultah_sebulan.html"  # template lama bisa dipakai
    context_object_name = "items"
    paginate_by = 25

    def _birthday_window_q(self, start: date, end: date):
        """
        Filter Q untuk ulang tahun antara start..end (±14 hari),
        berdasarkan bulan & hari, aman lintas tahun.
        """

        # Kasus 1: masih di bulan yang sama
        if start.month == end.month:
            return Q(
                birth_month=start.month,
                birth_day__gte=start.day,
                birth_day__lte=end.day,
            )

        # Kasus 2: lintas bulan / lintas tahun
        q = Q()

        # bagian awal
        q |= Q(birth_month=start.month, birth_day__gte=start.day)

        # bulan di tengah
        def months_between(m1, m2):
            months = []
            cur = (m1 % 12) + 1
            while cur != m2:
                months.append(cur)
                cur = (cur % 12) + 1
            return months

        middle_months = months_between(start.month, end.month)
        if middle_months:
            q |= Q(birth_month__in=middle_months)

        # bagian akhir
        q |= Q(birth_month=end.month, birth_day__lte=end.day)

        return q

    def get_queryset(self):
        today = date.today()
        start = today - timedelta(days=14)
        end = today + timedelta(days=14)

        qs = (
            ProfilSDM.objects
            .select_related("user")
            .filter(tgl_lahir__isnull=False)
            .annotate(
                birth_month=ExtractMonth("tgl_lahir"),
                birth_day=ExtractDay("tgl_lahir"),
            )
        )

        qs = qs.filter(self._birthday_window_q(start, end))

        # search (opsional)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q)
                | Q(nip__icontains=q)
                | Q(no_hp__icontains=q)
            )

        return qs.order_by("birth_month", "birth_day", "user__first_name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["today"] = date.today()
        ctx["start_date"] = ctx["today"] - timedelta(days=14)
        ctx["end_date"] = ctx["today"] + timedelta(days=14)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx['active_tab'] = 'ultah'
        return ctx
