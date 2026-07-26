from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, UpdateView, CreateView, DetailView, FormView, DeleteView
from django.db import transaction
# from django.views.generic import ListView, CreateView
from django.db.models import Sum, F, Q, Window, Prefetch
from django.db.models.functions import RowNumber
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from datetime import datetime, date, timedelta
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from typing import Optional
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
import os
import locale
import logging 
from .services import CheckCuti
from .utils import resolve_atasan_level3_for_level4
from .cuti_access import (
    build_approval_chain, can_supervise_employee, can_view_leave,
    ensure_diklat_verifier_snapshot, ensure_leave_verifier_snapshot,
)
from strukturorg.services import filter_structures_led_by, get_active_leader

# Konfigurasi logger (opsional, tapi direkomendasikan)
logger = logging.getLogger(__name__)


from .forms import OverrideKlaimTundaForCutiForm

from .models import (
    JenisLayanan, 
    LayananCuti, 
    VerifikasiCuti, 
    LayananGajiBerkala, 
    LayananUsulanDiklat, 
    VerifikasiDiklat, 
    LayananUsulanInovasi,
    PelimpahanTugas,
    PerubahanJadwalCuti,
    PemutihanCutiLog,
    STATUS_PENGAJUAN_CUTI,
    LayananNaikPangkat,
    LayananNaikJabatan,
)
from myaccount.models import Users
from dokumen.models import (
    DokumenSDM, 
    RiwayatCuti, 
    KlaimCutiTunda,
    RiwayatGajiBerkala, 
    RiwayatPenempatan, 
    RiwayatPanggol, 
    RiwayatDiklat, 
    RiwayatInovasi,
    RiwayatPengangkatan,
)
from .serializers import LayananGajiBerkalaSerializer
from dokumen.forms import (
    FormUsulanRiwayatDiklat,
    FormPenugasanDiklat,
    FormRiwayatDiklatSPT,
    FormRiwayatDiklatProses,
    FormRiwayatDiklatLaporan,
    RiwayatInovasiForm, 
    RiwayatInovasiTLForm, 
    RiwayatInovasiSKForm, 
    RiwayatInovasiFullForm
    )
from .forms import (
    RiwayatGajiBerkalaForm,
    LayananCutiForm,
    UploadFileCutiForm,
    Verifikator1CutiForm,
    Verifikator2CutiForm,
    Verifikator3CutiForm, 
    FormLayananBerkala, 
    pengajuan_cuti_formset,
    FormUsulanLayananDiklat,
    usulan_diklat_formset,
    update_diklat_formset,
    FormPenugasanUsulanDiklat,
    penugasan_inline_formset,
    FormPengalihanUsulanDiklat,
    pengalihan_diklat_formset,
    FormLayananDiklatLaporan,
    laporan_diklat_formset,
    FormLayananDiklatProses,
    proses_diklat_formset,
    FormLayananDiklatSPT,
    spt_diklat_formset,
    VerifikatorDiklatForm,
    Verifikator1DiklatForm,
    Verifikator2DiklatForm,
    Verifikator3DiklatForm,
    FormCatatanSDMUsulanLayananDiklat,
    inovasi_formset,
    update_inovasi_formset,
    full_update_inovasi_formset,
    proses_inovasi_formset,
    tindaklanjut_inovasi_formset,
    PelimpahanTugasCreateForm,
    PelimpahanTugasPenerimaForm,
    PelimpahanTugasAtasanForm,
    PerubahanJadwalCutiForm,
    PerubahanJadwalDecisionForm,
    LayananNaikPangkatForm,
    RiwayatPanggolHasilLayananForm,
    LayananNaikJabatanForm,
    RiwayatJabatanHasilLayananForm,
    SuratUsulanJabatanForm,
    )
from file_dokumen.services.jabatan_docx import generate_usulan_jabatan_docx
from dokumen.notifications import get_latest_str_records
from .cuti_schedule import (
    apply_nonfinal_change,
    approve_final_change,
    cancel_schedule_change,
    determine_change_type,
    finalize_pending_schedule_change,
    reject_pending_schedule_change,
    snapshot_verification,
)

# Create your views here.
locale.setlocale(locale.LC_ALL, '')

def get_nip(user):
    try:
        nip = user.profil_user.nip
        return nip
    except Exception:
        return None

def get_date_from_string(tanggal):
    tanggal_sekarang = date.today()
    try:
        get_tanggal = datetime.strptime(tanggal, "%Y-%m-%d").date()
        return get_tanggal
    except Exception:
        return tanggal_sekarang


class JenisLayananView(LoginRequiredMixin, View):
    def get(self, request):
        data:list = JenisLayanan.objects.all().order_by('id')
        context = {
            'data': data,
            'layanan':'active',
            'title_page':'Layanan SDM',
            'selected':'layanan'
        }
        return render(request, 'layanan_home.html', context)

def delete_existing_object(data_submitted, data, file):
    if data and file:
        # 2. Cek apakah ada file baru yang di-submit dari form
        #    `form.has_changed()` atau `form.cleaned_data` lebih aman
        #    Daripada membandingkan objek file langsung.
        if data_submitted.file: # Ini akan True jika file baru di-upload
            # 3. Cek apakah file fisik lama benar-benar ada di disk
            if os.path.exists(data.file.path):
                try:
                    # 4. Hapus file lama
                    os.remove(data.file.path)
                except OSError as e:
                    logger.error(f"Error deleting file: {e}")
            return None
        return None
    return None
        
class NotifikasiView(LoginRequiredMixin, View):
    def get_cuti_object(self, id):
        try:
            data = LayananCuti.objects.get(id=id)
            return data
        except LayananCuti.DoesNotExist:
            return None
        
    def get_berkala_object(self, id):
        try:
            data = LayananGajiBerkala.objects.get(id=id)
            return data
        except LayananGajiBerkala.DoesNotExist:
            return None
        
    def get_diklat_object(self, id):
        try:
            data = LayananUsulanDiklat.objects.get(id=id)
            return data
        except LayananUsulanDiklat.DoesNotExist:
            return None
        
    def get_inovasi_object(self, id):
        try:
            data = LayananUsulanInovasi.objects.get(id=id)
            return data
        except LayananUsulanInovasi.DoesNotExist:
            return None

    def get_sip_object(self, id):
        try:
            return LayananSIP.objects.get(id=id)
        except LayananSIP.DoesNotExist:
            return None

    def get_pangkat_object(self, id):
        try:
            return LayananNaikPangkat.objects.get(id=id)
        except LayananNaikPangkat.DoesNotExist:
            return None

    def get_jabatan_object(self, id):
        try:
            return LayananNaikJabatan.objects.get(id=id)
        except LayananNaikJabatan.DoesNotExist:
            return None
            
    def get(self, request, *args, **kwargs):
        get_layanan = request.GET.get('layanan')
        context={
            'data': get_layanan,
            'notification_menu': 'active',
        }
        if get_layanan == 'str-expiry':
            status_str = request.GET.get('status_str', 'semua')
            valid_statuses = {
                'semua', 'seumur_hidup',
                'berbatas_waktu', 'belum_teridentifikasi',
            }
            if status_str not in valid_statuses:
                status_str = 'semua'

            all_records = get_latest_str_records(request.user)
            context['str_summary'] = {
                status: sum(
                    item.validity_status == status
                    for item in all_records
                )
                for status in (
                    'seumur_hidup',
                    'berbatas_waktu',
                    'belum_teridentifikasi',
                )
            }
            context['all_str_lifetime'] = bool(all_records) and all(
                item.validity_status == 'seumur_hidup'
                for item in all_records
            )
            context['status_str'] = status_str
            context['str_monitoring_records'] = (
                all_records
                if status_str == 'semua'
                else [
                    item for item in all_records
                    if item.validity_status == status_str
                ]
            )
        return render(request, 'layanan_view_from_notif.html', context)
    
    def post(self, request, *args, **kwargs):
        id_layanan = kwargs.get('id')
        get_layanan = (request.GET.get('layanan') or '').strip()
        get_case = (request.GET.get('case') or 'detail').strip()
        if get_layanan == 'yancuti':
            data = self.get_cuti_object(id_layanan)
            can_open = data is not None and (
                request.user.is_cuti_admin or data.pegawai_id == request.user.pk
            )
            if can_open:
                data.is_read = True
                data.save(update_fields=['is_read', 'updated_at'])
                url = reverse(
                    'layanan_urls:layanan_cuti_update_view',
                    kwargs={'status': 'riwayat', 'id': id_layanan},
                )
                return redirect(f'{url}?case={get_case}')
            return redirect('layanan_urls:layanan_cuti_listview')
        elif get_layanan == 'yanberkala':
            data = self.get_berkala_object(id_layanan)
            can_open = data is not None and (
                request.user.is_berkala_admin or data.pegawai_id == request.user.pk
            )
            if can_open:
                data.is_read = True
                data.save(update_fields=['is_read', 'updated_at'])
                url = reverse(
                    'layanan_urls:layanan_berkala_update_view',
                    kwargs={'id': id_layanan},
                )
                return redirect(f'{url}?case={get_case}')
            return redirect('layanan_urls:layanan_berkala_view')
        if get_layanan == 'yandiklat':
            data = self.get_diklat_object(id_layanan)
            can_open = data is not None and (
                request.user.is_diklat_admin
                or data.riwayatdiklat_set.filter(pegawai=request.user).exists()
            )
            if can_open:
                data.is_read = True
                data.save(update_fields=['is_read', 'updated_at'])
                url = reverse(
                    'layanan_urls:layanan_diklat_update_view',
                    kwargs={'pk': id_layanan},
                )
                return redirect(f'{url}?case={get_case}')
            return redirect('layanan_urls:layanan_diklat_list_view')
        if get_layanan == 'yaninovasi':
            data = self.get_inovasi_object(id_layanan)
            can_open = data is not None and (
                request.user.is_inovasi_admin
                or data.pegawai_id == request.user.pk
            )
            if can_open:
                data.is_read = True
                data.save(update_fields=['is_read', 'updated_at'])
                url = reverse(
                    'layanan_urls:layanan_inovasi_update_view',
                    kwargs={'id': id_layanan},
                )
                return redirect(f'{url}?case={get_case}')
            return redirect('layanan_urls:layanan_inovasi_view')
        if get_layanan == 'yansip':
            data = self.get_sip_object(id_layanan)
            can_open = data is not None and (
                request.user.is_sip_admin or data.pegawai_id == request.user.pk
            )
            if can_open:
                data.is_read = True
                data.save(update_fields=['is_read', 'updated_at'])
                return redirect(
                    reverse('layanan_urls:layanan_sip_detail', kwargs={'pk': data.pk})
                )
            return redirect('layanan_urls:layanan_sip_list')
        if get_layanan == 'yanpangkat':
            data = self.get_pangkat_object(id_layanan)
            can_open = data is not None and (
                request.user.is_pangkat_admin or data.pegawai_id == request.user.pk
            )
            if can_open:
                if not request.user.is_pangkat_admin:
                    data.is_read = True
                    data.save(update_fields=['is_read', 'updated_at'])
                route_name = (
                    'layanan_urls:layanan_pangkat_process'
                    if request.user.is_pangkat_admin
                    else 'layanan_urls:layanan_pangkat_detail'
                )
                return redirect(reverse(route_name, kwargs={'pk': data.pk}))
            return redirect('layanan_urls:layanan_pangkat_list')
        if get_layanan == 'yanjabatan':
            data = self.get_jabatan_object(id_layanan)
            can_open = data is not None and (
                request.user.is_jabatan_admin or data.pegawai_id == request.user.pk
            )
            if can_open:
                if not request.user.is_jabatan_admin:
                    data.is_read = True
                    data.save(update_fields=['is_read', 'updated_at'])
                route_name = (
                    'layanan_urls:layanan_jabatan_process'
                    if request.user.is_jabatan_admin
                    else 'layanan_urls:layanan_jabatan_detail'
                )
                return redirect(reverse(route_name, kwargs={'pk': data.pk}))
            return redirect('layanan_urls:layanan_jabatan_list')

        messages.warning(
            request,
            'Jenis notifikasi tidak dikenali atau data notifikasi sudah tidak tersedia.',
        )
        return redirect('layanan_urls:notifikasi_view')


notfoundview = 'riwayat_urls:notfound_view'

class RiwayatLayananCutiView(LoginRequiredMixin, CheckCuti, ListView):
    model = RiwayatCuti
    template_name = '6_layanan_cuti/layanan_cuti_list.html'
    context_object_name = 'data'
    paginate_by = 25  # kalau mau paging
    
    def get_queryset(self):
        user = self.request.user
        nip = get_nip(user)
        data = RiwayatCuti.objects.all().order_by('-updated_at')
        if not self.request.user.is_cuti_admin:
            if nip:
                data = RiwayatCuti.objects.filter(pegawai__profil_user__nip=nip).order_by('-updated_at')
            else:
                return RiwayatCuti.objects.none()
        return data
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'cuti': 'active',
            'layanan': 'active',
            'selected': 'yancuti',
            'title_page': 'Riwayat Cuti Saya',
            'active_tab': 'saya',  # untuk nav/tab
        })
        return ctx


class RiwayatCutiBawahanView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = RiwayatCuti
    template_name = '6_layanan_cuti/layanan_cuti_list_bawahan.html'
    context_object_name = 'data'
    paginate_by = 25  # kalau mau paging
    
    def test_func(self):   
        # Akses halaman boleh untuk pengguna login; queryset di bawah tetap
        # membatasi data berdasarkan peran admin/lingkup struktur.
        return self.request.user.is_authenticated
    
    def handle_no_permission(self):
        messages.error(
            self.request,
            "Anda tidak memiliki akses ke halaman ini."
        )
        return redirect("layanan_urls:layanan_cuti_listview")

    def get_queryset(self):
        user = self.request.user

        # superuser bisa lihat semua
        base_qs = (
            RiwayatCuti.objects
            .select_related('pegawai', 'pegawai__profil_user', 'usulan')
            .prefetch_related(Prefetch(
                'perubahan_jadwal',
                queryset=PerubahanJadwalCuti.objects.filter(status='menunggu_verifikasi'),
                to_attr='perubahan_jadwal_menunggu',
            ))
            .order_by('-updated_at')
        )

        if user.is_cuti_admin:
            return base_qs

        snapshot_qs = base_qs.filter(
            Q(usulan__verifikasicuti__verifikator1=user)
            | Q(usulan__verifikasicuti__verifikator2=user)
            | Q(usulan__verifikasicuti__verifikator3=user)
        )

        profil_admin = getattr(user, 'profil_admin', None)
        if not profil_admin:
            return snapshot_qs.distinct()

        # hanya pegawai dengan penempatan aktif
        qs = base_qs.filter(
            pegawai__riwayat_penempatan__status=True
        ).exclude(pegawai=user)

        p = profil_admin

        instalasi_aktif = filter_structures_led_by(p.instalasi.all(), user)
        sub_bidang_aktif = filter_structures_led_by(p.sub_bidang.all(), user)
        bidang_aktif = filter_structures_led_by(p.bidang.all(), user)
        unor_aktif = filter_structures_led_by(p.unor.all(), user)

        if instalasi_aktif.exists():
            # atasan unit instalasi → bawahan: semua pegawai di instalasi tsb
            qs = qs.filter(
                pegawai__riwayat_penempatan__penempatan_level4__in=instalasi_aktif
            )

        elif sub_bidang_aktif.exists():
            # atasan sub_bidang → semua yg langsung di sub_bidang + instalasi di bawahnya
            qs = qs.filter(
                Q(pegawai__riwayat_penempatan__penempatan_level3__in=sub_bidang_aktif) |
                Q(pegawai__riwayat_penempatan__penempatan_level4__sub_bidang__in=sub_bidang_aktif)
            )

        elif bidang_aktif.exists():
            # atasan bidang → semua level di bawah bidang tsb
            qs = qs.filter(
                Q(pegawai__riwayat_penempatan__penempatan_level2__in=bidang_aktif) |
                Q(pegawai__riwayat_penempatan__penempatan_level3__bidang__in=bidang_aktif) |
                Q(pegawai__riwayat_penempatan__penempatan_level4__sub_bidang__bidang__in=bidang_aktif)
            )

        elif unor_aktif.exists():
            # atasan unor (level 1) → semua pegawai di unit tsb
            qs = qs.filter(
                Q(pegawai__riwayat_penempatan__penempatan_level1__in=unor_aktif) |
                Q(pegawai__riwayat_penempatan__penempatan_level2__unor__in=unor_aktif) |
                Q(pegawai__riwayat_penempatan__penempatan_level3__bidang__unor__in=unor_aktif) |
                Q(pegawai__riwayat_penempatan__penempatan_level4__sub_bidang__bidang__unor__in=unor_aktif)
            )
        else:
            return snapshot_qs.distinct()

        return (qs | snapshot_qs).distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'cuti': 'active',
            'layanan': 'active',
            'selected': 'yancuti',
            'title_page': 'Riwayat Pengajuan Cuti Bawahan',
            'active_tab': 'bawahan',  # untuk nav/tab
        })
        return ctx


class CutiSubmissionError(Exception):
    """Kesalahan bisnis yang harus membatalkan transaksi dan merender ulang form."""


class LayananCutiCreateView(LoginRequiredMixin, CheckCuti, CreateView):
    """
    Pengajuan Cuti TAHUNAN baru.
    - Model utama  : LayananCuti
    - Form utama   : LayananCutiForm
    - Formset      : RiwayatPengajuanCutiForm (RiwayatCuti)
    - Bisa klaim cuti TUNDA maksimal 2 tahun sebelumnya via KlaimCutiTunda.
    - >>> Integrasi dengan PelimpahanTugas:
        Setelah pengajuan Cuti Tahunan tersimpan, user diarahkan ke
        form pelimpahan tugas.
    """

    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    model = LayananCuti
    form_class = LayananCutiForm
    template_name = '6_layanan_cuti/layanan_cuti_create_form.html'
    success_url = reverse_lazy('layanan_urls:layanan_cuti_listview')

    # ---------- helpers ----------
    def get_layanan_default(self):
        return JenisLayanan.objects.filter(url='yancuti').first()

    def get_dokumen_default(self):
        return DokumenSDM.objects.filter(url='cuti').first()

    def get_nip_user(self):
        if self.request.user.is_cuti_admin:
            return None
        profil = getattr(self.request.user, 'profil_user', None)
        return getattr(profil, 'nip', None)

    def get_target_pegawai(self):
        """Pegawai pemohon; admin boleh memilih, pengguna biasa selalu dirinya."""
        user = self.request.user
        if not user.is_cuti_admin:
            return user

        raw_id = (
            self.request.POST.get('pegawai')
            if self.request.method == 'POST'
            else self.request.GET.get('pegawai')
        )
        if not raw_id:
            return None
        return (
            Users.objects.filter(pk=raw_id, is_active=True)
            .exclude(is_superuser=True)
            .first()
        )

    # ---------- form utama ----------
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        layanan_default = self.get_layanan_default()

        if not user.is_cuti_admin:
            initial['pegawai'] = user
        else:
            target_pegawai = self.get_target_pegawai()
            if target_pegawai:
                initial['pegawai'] = target_pegawai
        initial['layanan'] = layanan_default
        initial['status'] = 'pengajuan'
        initial['tahun'] = date.today().year
        return initial

    # ---------- formset ----------
    def get_formset(self, tahun_pengajuan=None, target_pegawai=None):
        if tahun_pengajuan is None:
            tahun_pengajuan = date.today().year
        if target_pegawai is None:
            target_pegawai = self.get_target_pegawai()

        if self.request.method == 'POST':
            formset = pengajuan_cuti_formset(
                data=self.request.POST,
                files=self.request.FILES,
                form_kwargs={
                    'request': self.request,
                    'tahun_pengajuan': tahun_pengajuan,
                    'check_cuti': self,
                    'target_pegawai': target_pegawai,
                },
            )
        else:
            formset = pengajuan_cuti_formset(
                form_kwargs={
                    'request': self.request,
                    'tahun_pengajuan': tahun_pengajuan,
                    'check_cuti': self,
                    'target_pegawai': target_pegawai,
                },
            )
        return formset

    # ---------- context ----------
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        self.set_allow_cuti_tunda()

        if 'formset' not in context:
            context['formset'] = self.get_formset()
        target_pegawai = self.get_target_pegawai()

        context.update({
            'nip': self.get_nip_user(),
            'cek_sisa_cuti': (
                self.cek_sisa_cuti(target_pegawai)
                if target_pegawai
                else 0
            ),
            'target_pegawai': target_pegawai,
            'title_page': 'Layanan Cuti',
            'card_title': 'Form Pengajuan Cuti',
            'cuti': 'active',
            'layanan': 'active',
            'selected': 'yancuti',
            'today': date.today(),
        })
        return context

    # ---------- POST: handle form + formset ----------
    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()

        tahun_pengajuan = date.today().year
        if form.is_valid():
            tahun_pengajuan = form.cleaned_data.get('tahun') or tahun_pengajuan
            target_pegawai = (
                form.cleaned_data.get('pegawai')
                if request.user.is_cuti_admin
                else request.user
            )
            formset = self.get_formset(
                tahun_pengajuan=tahun_pengajuan,
                target_pegawai=target_pegawai,
            )
            if formset.is_valid():
                try:
                    return self.forms_valid(form, formset, tahun_pengajuan)
                except CutiSubmissionError as exc:
                    messages.error(request, str(exc))
                    return self.forms_invalid(form, formset)
            else:
                return self.forms_invalid(form, formset)
        else:
            formset = self.get_formset(tahun_pengajuan=tahun_pengajuan)
            return self.forms_invalid(form, formset)

    def get_status_pegawai(self, pegawai):
        pengangkatan = RiwayatPengangkatan.objects.filter(
            pegawai=pegawai
        ).order_by('-id').first()
        return pengangkatan.status_pegawai if pengangkatan else None

    def simpan_snapshot_saldo_cuti(self, pegawai, tahun_pengajuan):
        self.object.snapshot_saldo_cuti = self.buat_snapshot_saldo_cuti(
            pegawai,
            tahun_pengajuan,
        )
        self.object.save(update_fields=('snapshot_saldo_cuti', 'updated_at'))
    
    def forms_valid(self, form, formset, tahun_pengajuan: int):
        request = self.request

        with transaction.atomic():
            # ============================================================
            # 1) Simpan LayananCuti
            # ============================================================
            self.object = form.save(commit=False)
            if not request.user.is_cuti_admin:
                self.object.pegawai = request.user
            # Field workflow tidak boleh dipercaya dari hidden input browser.
            layanan_default = self.get_layanan_default()
            dokumen_default = self.get_dokumen_default()
            if layanan_default is None or dokumen_default is None:
                raise CutiSubmissionError(
                    "Konfigurasi layanan/dokumen cuti belum lengkap."
                )
            self.object.layanan = layanan_default
            self.object.status = "pengajuan"
            self.object.tahun = tahun_pengajuan
            self.object.save()
            ensure_leave_verifier_snapshot(self.object)

            # ============================================================
            # 2) Proses formset (RiwayatCuti)
            # ============================================================
            data_form = formset.save(commit=False)
            if not data_form:
                raise CutiSubmissionError("Data detail cuti tidak boleh kosong.")

            cd0 = formset.cleaned_data[0]
            jenis_cuti = cd0.get("jenis_cuti")
            tgl_mulai_cuti = cd0.get("tgl_mulai_cuti")
            tgl_akhir_cuti = cd0.get("tgl_akhir_cuti")  # bisa None
            lama_cuti = cd0.get("lama_cuti") or 0

            # formset extra fields
            f0 = formset.forms[0].cleaned_data
            cuti_tunda_dipilih = f0.get("cuti_tunda_dipilih")   # QS sumber tunda yg dipilih
            pakai_tunda_saja = bool(f0.get("pakai_tunda_saja"))  # checkbox baru (default False)

            # hitung tgl_akhir jika belum diisi
            if tgl_mulai_cuti and not tgl_akhir_cuti and lama_cuti:
                tgl_akhir_cuti = tgl_mulai_cuti + timedelta(days=lama_cuti - 1)

            target_pegawai = self.object.pegawai
            # Serialisasi seluruh perubahan saldo per pegawai. Ini mencegah dua
            # request paralel menggunakan saldo tahunan/tunda yang sama.
            target_pegawai = Users.objects.select_for_update().get(pk=target_pegawai.pk)
            sisa_cuti = self.cek_sisa_cuti(target_pegawai)

            if (
                tgl_mulai_cuti
                and tgl_akhir_cuti
                and self.is_memiliki_cuti_bentrok(
                    target_pegawai,
                    tgl_mulai_cuti,
                    tgl_akhir_cuti,
                )
            ):
                raise CutiSubmissionError(
                    "Pegawai sudah memiliki pengajuan atau pelaksanaan cuti lain "
                    "yang bertabrakan dengan rentang tanggal tersebut."
                )

            # ============================================================
            # 3) Guard: penerima pelimpahan aktif tidak boleh ajukan cuti tahunan
            # ============================================================
            if jenis_cuti == "Cuti Tahunan" and tgl_mulai_cuti and tgl_akhir_cuti:
                if self.is_penerima_memiliki_pelimpahan_aktif(target_pegawai, tgl_mulai_cuti, tgl_akhir_cuti):
                    raise CutiSubmissionError(
                        "Anda tidak dapat mengajukan Cuti Tahunan karena sedang menerima "
                        "pelimpahan tugas pada rentang tanggal tersebut."
                    )

            # ============================================================
            # 4) Isi field umum tiap RiwayatCuti
            # ============================================================
            for item in data_form:
                item.pegawai = self.object.pegawai
                item.dokumen = dokumen_default
                item.status_cuti = 'Belum'
                if not item.tahun_cuti:
                    item.tahun_cuti = self.object.tahun or tahun_pengajuan
                item.usulan = self.object
                if not item.tgl_akhir_cuti and tgl_akhir_cuti:
                    item.tgl_akhir_cuti = tgl_akhir_cuti

            # ============================================================
            # 5) CABANG: CUTI TAHUNAN
            # ============================================================
            if jenis_cuti == "Cuti Tahunan":
                # waktu pengajuan tetap divalidasi utk cuti tahunan (mau tunda saja / normal)
                status_pegawai = self.get_status_pegawai(target_pegawai)
                if not status_pegawai:
                    raise CutiSubmissionError(
                        "Status kepegawaian belum tersedia. Hubungi pengelola data pegawai."
                    )
                if not self.cek_waktu_pengajuan_cuti(tgl_mulai_cuti, status_pegawai):
                    raise CutiSubmissionError(
                        "Mohon maaf waktu pengajuan cuti Anda terlalu mepet atau tidak sesuai."
                    )

                # if lama_cuti <= 0: user boleh buat cuti dengan lama cuti 0 nanti akan divalidasi di saat verifikasi pimpinan
                #     messages.error(request, "Lama cuti wajib diisi dan harus lebih dari 0.")
                #     return redirect(self.success_url)

                # ---- Mode A: pakai cuti tunda SAJA (tidak ganggu jatah tahun ini) ----
                if pakai_tunda_saja:
                    if not cuti_tunda_dipilih:
                        raise CutiSubmissionError(
                            "Anda memilih 'pakai cuti tunda saja' tetapi belum memilih "
                            "sumber cuti tunda."
                        )

                    eligible = self.get_cuti_tunda_eligible(target_pegawai, tahun_pengajuan)
                    valid_tunda = eligible.filter(
                        id__in=cuti_tunda_dipilih.values_list("id", flat=True)
                    )

                    # total sisa tunda yang tersedia dari pilihan user
                    total_sisa_valid = sum((s.sisa_hari_tunda or 0) for s in valid_tunda)
                    if total_sisa_valid < lama_cuti:
                        raise CutiSubmissionError(
                            f"Sisa cuti tunda yang dipilih tidak mencukupi. "
                            f"Total sisa tunda: {total_sisa_valid} hari, kebutuhan: {lama_cuti} hari."
                        )

                    # simpan riwayat cuti (main record)
                    cuti_baru_main = None
                    for idx, item in enumerate(data_form):
                        # tandai bahwa pengajuan ini "tunda saja"
                        setattr(item, "pakai_tunda_saja", True)
                        item.save()
                        if idx == 0:
                            cuti_baru_main = item

                    # klaim dari sumber tunda sampai kebutuhan terpenuhi
                    remaining = lama_cuti
                    for sumber in valid_tunda.order_by("tahun_cuti", "id"):
                        if remaining <= 0:
                            break
                        sisa = sumber.sisa_hari_tunda or 0
                        ambil = min(sisa, remaining)
                        if ambil > 0:
                            KlaimCutiTunda.objects.create(
                                sumber_tunda=sumber,
                                cuti_klaim=cuti_baru_main,
                                jumlah_hari_diklaim=ambil,
                            )
                            remaining -= ambil

                    # redirect ke pelimpahan tugas
                    if cuti_baru_main:
                        self.simpan_snapshot_saldo_cuti(
                            target_pegawai,
                            tahun_pengajuan,
                        )
                        messages.success(
                            request,
                            "Pengajuan Cuti Tunda berhasil disimpan (tanpa mengurangi jatah cuti tahun berjalan). "
                            "Silakan lengkapi dokumen pelimpahan tugas."
                        )
                        pelimpahan_url = reverse(
                            "layanan_urls:pelimpahan_create",
                            kwargs={"riwayat_pk": cuti_baru_main.pk}
                        )
                        return redirect(pelimpahan_url)

                    messages.success(request, "Pengajuan cuti berhasil disimpan.")
                    return redirect(self.success_url)

                # ---- Mode B: cuti normal (boleh + klaim tunda untuk membantu kuota) ----
                # Klaim tunda mengurangi bagian yang dibebankan pada hak tahun ini.
                total_tunda_terpilih = 0
                if cuti_tunda_dipilih:
                    eligible = self.get_cuti_tunda_eligible(target_pegawai, tahun_pengajuan)
                    valid_tunda = eligible.filter(
                        id__in=cuti_tunda_dipilih.values_list("id", flat=True)
                    )
                    total_tunda_terpilih = sum(s.sisa_hari_tunda for s in valid_tunda)
                kebutuhan_hak_tahun_ini = max(0, lama_cuti - total_tunda_terpilih)
                if sisa_cuti < kebutuhan_hak_tahun_ini:
                    raise CutiSubmissionError(
                        "Maaf jatah cuti tahunan Anda kurang atau habis."
                    )

                cuti_baru_main = None
                for idx, item in enumerate(data_form):
                    setattr(item, "pakai_tunda_saja", False)
                    item.save()
                    if idx == 0:
                        cuti_baru_main = item

                # Klaim tunda (opsional) untuk menutup sebagian dari lama_cuti
                if cuti_tunda_dipilih and cuti_baru_main:
                    remaining = lama_cuti
                    for sumber in valid_tunda.order_by("tahun_cuti", "id"):
                        if remaining <= 0:
                            break
                        sisa = sumber.sisa_hari_tunda or 0
                        ambil = min(sisa, remaining)
                        if ambil > 0:
                            KlaimCutiTunda.objects.create(
                                sumber_tunda=sumber,
                                cuti_klaim=cuti_baru_main,
                                jumlah_hari_diklaim=ambil,
                            )
                            remaining -= ambil

                # redirect ke pelimpahan tugas
                if cuti_baru_main:
                    self.simpan_snapshot_saldo_cuti(
                        target_pegawai,
                        tahun_pengajuan,
                    )
                    messages.success(
                        request,
                        "Pengajuan Cuti Tahunan berhasil disimpan. Silakan lengkapi dokumen pelimpahan tugas."
                    )
                    pelimpahan_url = reverse(
                        "layanan_urls:pelimpahan_create",
                        kwargs={"riwayat_pk": cuti_baru_main.pk}
                    )
                    return redirect(pelimpahan_url)

                messages.success(request, "Pengajuan cuti berhasil disimpan.")
                return redirect(self.success_url)

            # ============================================================
            # 6) CABANG: CUTI LAIN
            # ============================================================
            elif jenis_cuti in [
                "Cuti Alasan Penting",
                "Cuti melahirkan",
                "Cuti Sakit",
                "Cuti Besar",
                "Cuti Diluar Tanggungan Negara",
            ]:
                for item in data_form:
                    item.save()
                self.simpan_snapshot_saldo_cuti(
                    target_pegawai,
                    tahun_pengajuan,
                )
                messages.success(request, "Pengajuan cuti anda sukses, dan segera akan ditindaklanjuti oleh bagian SDM.")
                return redirect(self.success_url)

            # ============================================================
            # 7) DEFAULT
            # ============================================================
            raise CutiSubmissionError(
                "Jenis cuti yang dipilih belum didukung oleh alur digital ini."
            )

    def forms_invalid(self, form, formset):
        # 1) Error dari form utama
        # non-field errors
        for err in form.non_field_errors():
            messages.error(self.request, err)

        # field errors
        for field, errs in form.errors.items():
            if field == "__all__":
                continue
            for err in errs:
                messages.error(self.request, f"{field}: {err}")

        # 2) Error dari formset (bisa lebih dari 1 form)
        # non-form errors pada formset (kalau ada)
        if hasattr(formset, "non_form_errors"):
            for err in formset.non_form_errors():
                messages.error(self.request, err)

        # errors per form dalam formset
        for f in formset.forms:
            # non-field errors pada form di formset
            for err in f.non_field_errors():
                messages.error(self.request, err)

            # field errors pada form di formset
            for field, errs in f.errors.items():
                if field == "__all__":
                    continue
                for err in errs:
                    messages.error(self.request, f"{field}: {err}")

        return self.render_to_response(self.get_context_data(form=form, formset=formset))


class AdminOverrideKlaimTundaForCutiView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "6_layanan_cuti/admin_klaim_cuti_tunda.html"
    form_class = OverrideKlaimTundaForCutiForm

    def test_func(self):
        return self.request.user.is_cuti_admin

    def dispatch(self, request, *args, **kwargs):
        self.cuti_klaim = get_object_or_404(RiwayatCuti, pk=kwargs["riwayat_id"])

        # Guard: harus Cuti Tahunan tahun berjalan yang valid
        if self.cuti_klaim.jenis_cuti != "Cuti Tahunan":
            messages.error(request, "Override hanya untuk cuti tahunan.")
            return redirect(self.get_back_url())

        if self.cuti_klaim.status_cuti not in ["Belum", "Berlangsung", "Selesai"]:
            messages.error(request, "Override hanya bisa untuk cuti berstatus Proses/Selesai.")
            return redirect(self.get_back_url())

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["cuti_klaim"] = self.cuti_klaim
        kwargs["allow_same_year"] = True  # ini override tahun berjalan
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cuti_klaim"] = self.cuti_klaim

        # ringkasan klaim masuk (yang sudah ada)
        total_klaim_masuk = sum(x.jumlah_hari_diklaim for x in self.cuti_klaim.klaim_masuk.all())
        ctx["total_klaim_masuk"] = total_klaim_masuk
        ctx["sisa_kebutuhan"] = max(0, (self.cuti_klaim.lama_cuti or 0) - total_klaim_masuk)

        return ctx

    def form_valid(self, form):
        catatan = form.cleaned_data.get("catatan_admin") or ""

        with transaction.atomic():
            Users.objects.select_for_update().get(pk=self.cuti_klaim.pegawai_id)
            sumber = RiwayatCuti.objects.select_for_update().get(
                pk=form.cleaned_data['sumber_tunda'].pk
            )
            total_terklaim = sumber.klaim_keluar.aggregate(
                total=Sum('jumlah_hari_diklaim')
            )['total'] or 0
            sisa_aktual = max(0, (sumber.lama_cuti or 0) - total_terklaim)
            if form.cleaned_data['jumlah_hari_diklaim'] > sisa_aktual:
                form.add_error(
                    'jumlah_hari_diklaim',
                    f'Saldo cuti tunda berubah. Sisa saat ini {sisa_aktual} hari.',
                )
                return self.form_invalid(form)

            klaim = form.save(commit=False)
            klaim.sumber_tunda = sumber
            klaim.is_admin_override = True
            klaim.admin_override_by = self.request.user
            klaim.admin_override_at = timezone.now()
            klaim.catatan_admin = form.cleaned_data.get("catatan_admin", "")
            klaim.full_clean()
            klaim.save()
            
        if catatan:
            messages.info(self.request, f"Catatan admin: {catatan}")

        messages.success(
            self.request,
            f"Override berhasil: klaim {klaim.jumlah_hari_diklaim} hari dari tunda #{klaim.sumber_tunda_id} "
            f"ke cuti #{klaim.cuti_klaim_id}."
        )
        return redirect(self.get_back_url())

    def get_back_url(self):
        # arahkan kembali ke detail yang sudah Anda punya
        # SESUAIKAN nama url detail Anda:
        return reverse("layanan_urls:layanan_cuti_listview")


class PelimpahanTugasCreateView(LoginRequiredMixin, CreateView):
    model = PelimpahanTugas
    form_class = PelimpahanTugasCreateForm
    template_name = '6_layanan_cuti/pelimpahan/form_pelimpahan_tugas.html'

    def dispatch(self, request, *args, **kwargs):
        self.riwayat_cuti = get_object_or_404(RiwayatCuti, pk=kwargs['riwayat_pk'])
        self.pelimpahan_existing = getattr(self.riwayat_cuti, 'pelimpahan_tugas', None)

        # opsional: pastikan hanya pemilik cuti yang boleh buat pelimpahan
        if request.user.is_cuti_admin and self.pelimpahan_existing:
            return redirect('layanan_urls:pelimpahan_detail', pk=self.pelimpahan_existing.pk)
        if request.user.is_cuti_admin:
            messages.info(request, 'Pemohon belum membuat pelimpahan tugas.')
            return redirect('layanan_urls:layanan_cuti_listview')

        if self.riwayat_cuti.pegawai != request.user:
            messages.error(request, "Anda tidak berhak membuat pelimpahan untuk cuti ini.")
            return redirect('layanan_urls:layanan_cuti_listview')

        # jika sudah ada pelimpahan, redirect ke halaman detail
        if self.pelimpahan_existing and self.pelimpahan_existing.status not in (
            'ditolak_penerima', 'ditolak_atasan'
        ):
            return redirect('layanan_urls:pelimpahan_detail', pk=self.pelimpahan_existing.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['riwayat_cuti'] = self.riwayat_cuti
        if self.pelimpahan_existing:
            kwargs['instance'] = self.pelimpahan_existing
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.riwayat_cuti = self.riwayat_cuti
        obj.pemberi_tugas = self.request.user
        # Default status ketika selesai isi form: menunggu persetujuan penerima
        obj.status = 'menunggu_penerima'
        obj.persetujuan_penerima = "belum"
        obj.catatan_penerima = ""
        obj.persetujuan_atasan = "belum"
        obj.catatan_atasan = ""
        
        # aturan: jika pemberi level4 => set atasan (level3) sebagai penyetuju
        # jika pemberi level3+ => persetujuan atasan tidak diperlukan => auto "disetujui"
        if obj.requires_atasan_approval():
            obj.butuh_persetujuan_atasan = True
            obj.atasan_penyetuju = resolve_atasan_level3_for_level4(obj.pemberi_tugas)
            if obj.atasan_penyetuju is None:
                form.add_error(None, "Atasan penyetuju belum tersedia pada struktur organisasi.")
                return self.form_invalid(form)
            obj.persetujuan_atasan = "belum"
        else:
            obj.butuh_persetujuan_atasan = False
            obj.atasan_penyetuju = None
            obj.persetujuan_atasan = "disetujui"
            
        obj.save()
        messages.success(self.request, "Pelimpahan tugas berhasil dibuat. Menunggu persetujuan penerima")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('layanan_urls:pelimpahan_detail', kwargs={'pk': self.object.pk})


class PelimpahanTugasDetailView(LoginRequiredMixin, DetailView):
    model = PelimpahanTugas
    template_name = '6_layanan_cuti/pelimpahan/detail_pelimpahan_tugas.html'
    context_object_name = 'pelimpahan'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()

        # Opsional: cek hak akses
        u = request.user

        # hanya superuser, pemberi, penerima, atasan penyetuju yang boleh akses
        if u.is_cuti_admin or u in [obj.pemberi_tugas, obj.penerima_tugas, obj.atasan_penyetuju]:
            return super().dispatch(request, *args, **kwargs)
        
        # Jika bukan siapa-siapa → redirect
        messages.error(request, "Anda tidak berhak mengakses dokumen ini.")
        return redirect("layanan_urls:layanan_cuti_listview")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["needs_atasan"] = self.object.requires_atasan_approval()
        ctx["is_final"] = self.object.is_final_approved()
        return ctx


class PelimpahanTugasPenerimaListView(LoginRequiredMixin, ListView):
    model = PelimpahanTugas
    template_name = '6_layanan_cuti/pelimpahan/list_penerima.html'
    context_object_name = 'pelimpahan_list'

    def get_queryset(self):
        return PelimpahanTugas.objects.filter(
            penerima_tugas=self.request.user,
            status__in=['menunggu_penerima', 'menunggu_atasan', 'disetujui']
        ).select_related('riwayat_cuti', 'pemberi_tugas')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title_page'] = 'Daftar Pelimpahan Tugas Saya'
        context.update({
            'cuti': 'active',
            'layanan': 'active',
            'selected': 'yancuti',
            'active_tab': 'pelimpahan',  # untuk nav/tab
        })
        return context


class PelimpahanTugasPenerimaUpdateView(LoginRequiredMixin, UpdateView):
    model = PelimpahanTugas
    form_class = PelimpahanTugasPenerimaForm
    template_name = '6_layanan_cuti/pelimpahan/form_persetujuan_penerima.html'

    def get_queryset(self):
        # hanya boleh akses pelimpahan yang ditujukan ke dirinya
        return PelimpahanTugas.objects.filter(
            penerima_tugas=self.request.user,
            status='menunggu_penerima'
        )
    
    @transaction.atomic
    def form_valid(self, form):
        obj = PelimpahanTugas.objects.select_for_update().get(pk=form.instance.pk)

        aksi = form.cleaned_data["aksi"]
        obj.catatan_penerima = form.cleaned_data.get("catatan_penerima", "")

        if aksi == "tolak":
            obj.persetujuan_penerima = "ditolak"
            obj.status = "ditolak_penerima"
            obj.save(update_fields=["catatan_penerima", "persetujuan_penerima", "status"])
            perubahan_ditolak = reject_pending_schedule_change(obj.pk)
            if perubahan_ditolak:
                messages.info(
                    self.request,
                    "Pelimpahan jadwal baru ditolak. Jadwal dan pelimpahan lama tetap berlaku.",
                )
            else:
                messages.info(self.request, "Pelimpahan tugas ditolak.")
            return redirect("layanan_urls:pelimpahan_detail", pk=obj.pk)

        # aksi setuju
        obj.persetujuan_penerima = "disetujui"
        if obj.requires_atasan_approval():
            obj.status = "menunggu_atasan"
            obj.save(update_fields=["catatan_penerima", "persetujuan_penerima", "status"])
        else:
            obj.persetujuan_atasan = "disetujui"
            obj.status = "disetujui"
            obj.save(update_fields=["catatan_penerima", "persetujuan_penerima", "persetujuan_atasan", "status"])
            perubahan_diterapkan = finalize_pending_schedule_change(obj.pk)
            if perubahan_diterapkan:
                messages.success(self.request, "Jadwal cuti baru resmi diterapkan.")

        messages.success(self.request, "Persetujuan penerima tersimpan.")
        return redirect("layanan_urls:pelimpahan_detail", pk=obj.pk)

    
    def get_success_url(self):
        return reverse_lazy('layanan_urls:pelimpahan_penerima_list')


class PelimpahanKepalaListView(LoginRequiredMixin, ListView):
    """
    Daftar pelimpahan tugas yang MENUNGGU persetujuan kepala (kasi/subbidang).
    Hanya untuk kasus pemohon cuti level 4 (instalasi/unit).
    """
    template_name = "6_layanan_cuti/pelimpahan/list_kepala.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Ambil semua pelimpahan yang statusnya menunggu kepala
        # (sesuaikan value status Anda)
        qs = (
            PelimpahanTugas.objects
            .select_related(
                "riwayat_cuti",
                "riwayat_cuti__pegawai",
                "riwayat_cuti__pegawai__profil_user",
                "penerima_tugas",
                "penerima_tugas__profil_user",
            ).order_by('-created_at')
        )

        # Gunakan snapshot atasan saat pelimpahan diajukan. Mutasi pejabat tidak
        # boleh memindahkan pengajuan lama ke pejabat baru secara diam-diam.
        qs = qs.filter(
            status='menunggu_atasan',
            atasan_penyetuju=user,
        ).distinct()

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title_page": "Persetujuan Pelimpahan Tugas",
            "card_title": "Daftar Pelimpahan Menunggu Persetujuan Anda",
            "active_tab": "pelimpahan_kepala",
        })
        return ctx


class PelimpahanTugasAtasanUpdateView(LoginRequiredMixin, UpdateView):
    model = PelimpahanTugas
    form_class = PelimpahanTugasAtasanForm
    template_name = '6_layanan_cuti/pelimpahan/form_persetujuan_atasan.html'

    def get_queryset(self):
        return PelimpahanTugas.objects.filter(
            status='menunggu_atasan',
            atasan_penyetuju=self.request.user
        )

    @transaction.atomic
    def form_valid(self, form):
        aksi = form.cleaned_data["aksi"]

        locked_object = PelimpahanTugas.objects.select_for_update().get(pk=form.instance.pk)
        form.instance = locked_object
        self.object = form.save(commit=False)

        self.object.catatan_atasan = form.cleaned_data.get("catatan_atasan", "")

        if aksi == "setuju":
            self.object.persetujuan_atasan = "disetujui"
            self.object.status = "disetujui"
            messages.success(self.request, "Pelimpahan disetujui Kepala Instalasi/Unit.")
        else:
            self.object.persetujuan_atasan = "ditolak"
            self.object.status = "ditolak_atasan"
            messages.error(self.request, "Pelimpahan ditolak Kepala Instalasi/Unit.")

        self.object.save()
        if aksi == "setuju":
            perubahan_diterapkan = finalize_pending_schedule_change(self.object.pk)
            if perubahan_diterapkan:
                messages.success(self.request, "Jadwal cuti baru resmi diterapkan.")
        else:
            perubahan_ditolak = reject_pending_schedule_change(self.object.pk)
            if perubahan_ditolak:
                messages.info(
                    self.request,
                    "Pelimpahan jadwal baru ditolak. Jadwal dan pelimpahan lama tetap berlaku.",
                )
        return super().form_valid(form)  # aman karena instance sudah berisi nilai terbaru

    def get_success_url(self):
        return reverse_lazy('layanan_urls:pelimpahan_atasan_list')


class LayananCutiDetailView(LoginRequiredMixin, DetailView):
    """
    Halaman detail pengajuan cuti (header + detail RiwayatCuti).
    Tujuan: memudahkan penilaian status (proses, disetujui, ditolak, selesai),
    dan membaca ringkasan tanggal/lama/dokumen.
    """
    model = LayananCuti
    template_name = "6_layanan_cuti/layanan_cuti_detail.html"
    login_url = "/accounts/login/"

    def get_queryset(self):
        # agar tidak N+1
        return (
            super()
            .get_queryset()
            .select_related("pegawai", "layanan")
        )

    def _get_detail_qs(self, layanan: LayananCuti):
        # detail cuti (RiwayatCuti) untuk layanan ini
        return (
            RiwayatCuti.objects
            .filter(usulan=layanan)
            .select_related("pegawai", "pegawai__profil_user", "dokumen")
            .order_by("id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        layanan: LayananCuti = self.object

        details = self._get_detail_qs(layanan)

        # ringkasan (ambil baris utama = baris pertama)
        main = details.first()

        total_hari = details.aggregate(total=Sum("lama_cuti")).get("total") or 0

        # Dua status dengan tanggung jawab yang berbeda.
        status_ringkas = {
            "status_pengajuan": layanan.status,
            "status_pelaksanaan": getattr(main, "status_pelaksanaan_aktual", None),
        }

        # izin akses sederhana:
        # - pemohon boleh lihat detailnya sendiri
        # - superuser boleh lihat semua
        # - admin boleh (opsional) tambahkan rules profil_admin sesuai kebutuhan
        user = self.request.user
        can_view = can_view_leave(user, layanan)
        # jika Anda punya aturan admin, bisa diperluas di sini
        if not can_view:
            # biar aman, Anda bisa raise PermissionDenied
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Anda tidak berhak melihat detail pengajuan cuti ini.")

        perubahan_aktif = None
        riwayat_perubahan = PerubahanJadwalCuti.objects.none()
        can_verify_change = False
        if main:
            riwayat_perubahan = main.perubahan_jadwal.select_related('diajukan_oleh').all()
            perubahan_aktif = riwayat_perubahan.filter(
                status__in=('menunggu_verifikasi', 'menunggu_pelimpahan')
            ).first()
            if perubahan_aktif:
                can_verify_change = user.pk in {
                    perubahan_aktif.verifikator1_id,
                    perubahan_aktif.verifikator2_id,
                    perubahan_aktif.verifikator3_id,
                }

        context.update({
            "details": details,
            "main": main,
            "total_hari": total_hari,
            "status_ringkas": status_ringkas,
            "is_owner": layanan.pegawai_id == user.id,
            "can_upload_surat_cuti": bool(
                (user.is_superuser or user.is_cuti_admin)
                and main
                and layanan.status in ('disetujui', 'selesai')
            ),
            "perubahan_aktif": perubahan_aktif,
            "riwayat_perubahan": riwayat_perubahan,
            "can_verify_change": can_verify_change,
            "can_request_change": bool(
                main
                and layanan.pegawai_id == user.id
                and layanan.status != 'ditolak'
                and main.status_cuti not in ('Tunda', 'Batal')
                and main.tgl_mulai_cuti
                and main.tgl_akhir_cuti
                and (main.lama_cuti or 0) > 0
                and main.tgl_akhir_cuti >= date.today()
                and perubahan_aktif is None
            ),

            # tampilan
            "title_page": "Detail Pengajuan Cuti",
            "card_title": "Detail Cuti Pegawai",
            "cuti": "active",
            "layanan": "active",
            "selected": "yancuti",
        })
        return context


class UploadFileCutiView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    UpdateView,
):
    """Unggah surat cuti final dan selesaikan proses pengajuannya."""

    model = RiwayatCuti
    form_class = UploadFileCutiForm
    template_name = '6_layanan_cuti/upload_file_cuti.html'
    context_object_name = 'riwayat_cuti'
    login_url = reverse_lazy('myaccount_urls:login_view')
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.is_cuti_admin

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('usulan', 'pegawai')
            .filter(
                usulan__isnull=False,
                usulan__status__in=('disetujui', 'selesai'),
            )
        )

    @transaction.atomic
    def form_valid(self, form):
        old_file_name = self.object.file.name if self.object.file else ''
        storage = self.object.file.storage
        new_file_name = ''

        try:
            self.object = form.save()
            new_file_name = self.object.file.name

            layanan = LayananCuti.objects.select_for_update().get(
                pk=self.object.usulan_id,
            )
            layanan.status = 'selesai'
            layanan.save(update_fields=('status', 'updated_at'))
        except Exception:
            if new_file_name and new_file_name != old_file_name:
                storage.delete(new_file_name)
            raise

        if old_file_name and old_file_name != new_file_name:
            transaction.on_commit(lambda: storage.delete(old_file_name))

        messages.success(
            self.request,
            'Surat cuti berhasil diunggah dan status pengajuan menjadi selesai.',
        )
        return redirect(
            'layanan_urls:layanan_cuti_detail',
            pk=self.object.usulan_id,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title_page': 'Upload Surat Cuti Final',
            'cuti': 'active',
            'layanan': 'active',
            'selected': 'yancuti',
        })
        return context


#refactoring layanan cuti -- masih memikirkan logika cuti tahun sebelumnya jika tidak diajukan cuti tunda
class LayananCutiUpdateView(LoginRequiredMixin, View):
    """Adapter URL lama menuju alur detail/verifikasi cuti yang aktif."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        layanan = get_object_or_404(LayananCuti, pk=kwargs.get('id'))
        if not can_view_leave(request.user, layanan):
            raise PermissionDenied("Anda tidak berhak mengakses pengajuan cuti ini.")
        if request.method != 'GET':
            raise PermissionDenied("Alur cuti lama sudah dinonaktifkan.")

        if request.GET.get('case') == 'tindaklanjut' and (
            request.user.is_cuti_admin
            or any(
                item['user'] and item['user'].pk == request.user.pk
                for item in build_approval_chain(layanan.pegawai)
            )
        ):
            return redirect('layanan_urls:layanan_cuti_verifikasi', id=layanan.pk)
        return redirect('layanan_urls:layanan_cuti_detail', pk=layanan.pk)

class VerifikasiCutiAccessMixin(LoginRequiredMixin):
    """
    - Mengambil LayananCuti berdasarkan `id` di URL.
    - Mengambil/membuat VerifikasiCuti.
    - Menentukan rantai atasan (level 1-3) berdasarkan RiwayatPenempatan.
    - Menentukan level verifikasi user saat ini (current_level).
    """

    lookup_url_kwarg = "id"  # nama kwarg di URL: path(".../<int:id>/verifikasi/", ...)

    # --- Helper object ---

    def get_layanan_cuti(self) -> LayananCuti:
        if not hasattr(self, "_layanan_cuti"):
            pk = self.kwargs.get(self.lookup_url_kwarg)
            self._layanan_cuti = get_object_or_404(
                LayananCuti.objects.select_related("pegawai"),
                pk=pk,
            )
        return self._layanan_cuti

    def get_verifikasi_obj(self) -> VerifikasiCuti:
        if not hasattr(self, "_verifikasi_obj"):
            chain = build_approval_chain(self.get_layanan_cuti().pegawai)
            defaults = {
                f"verifikator{item['level']}": item['user']
                for item in chain
                if item['user'] is not None
            }
            self._verifikasi_obj, _ = VerifikasiCuti.objects.get_or_create(
                layanan_cuti=self.get_layanan_cuti(),
                defaults=defaults,
            )
            changed_fields = []
            for field_name, user in defaults.items():
                if getattr(self._verifikasi_obj, field_name) is None:
                    setattr(self._verifikasi_obj, field_name, user)
                    changed_fields.append(field_name)
            if changed_fields:
                self._verifikasi_obj.save(update_fields=changed_fields + ['updated_at'])
        return self._verifikasi_obj

    def get_riwayat_penempatan_aktif(self) -> Optional[RiwayatPenempatan]:
        if hasattr(self, "_riwayat_penempatan_aktif"):
            return self._riwayat_penempatan_aktif

        pegawai = self.get_layanan_cuti().pegawai
        self._riwayat_penempatan_aktif = (
            pegawai.riwayat_penempatan
            .filter(status=True)
            .select_related(
                "penempatan_level1__satker_induk__instansi_daerah",
                "penempatan_level2__unor__satker_induk__instansi_daerah",
                "penempatan_level3__bidang__unor__satker_induk__instansi_daerah",
                "penempatan_level4__sub_bidang__bidang__unor__satker_induk__instansi_daerah",
            )
            .order_by("-updated_at", "-id")
            .first()
        )
        return self._riwayat_penempatan_aktif

    # --- Chain verifikator: list[{level, user, label}] ---

    def build_verifikator_chain(self):
        """
        Kembalikan list of dict:
        [
          {"level": 1, "user": <User atau None>, "label": "Kasi/Subbag ..."},
          {"level": 2, "user": <User atau None>, "label": "Kabid ..."},
          {"level": 3, "user": <User atau None>, "label": "Direktur ..."},
        ]
        """
        return build_approval_chain(self.get_layanan_cuti().pegawai)

    @property
    def verifikator_chain(self):
        if not hasattr(self, "_verifikator_chain"):
            chain_aktif = {
                item['level']: item
                for item in self.build_verifikator_chain()
            }
            snapshot = self.get_verifikasi_obj()
            gabungan = []
            for level in (1, 2, 3):
                item = chain_aktif.get(level)
                saved_user = getattr(snapshot, f"verifikator{level}", None)
                if item is None and saved_user is None:
                    continue
                gabungan.append({
                    'level': level,
                    'user': saved_user or item['user'],
                    'label': (
                        item['label']
                        if item is not None
                        else f'Verifikator Level {level}'
                    ),
                })
            self._verifikator_chain = gabungan
        return self._verifikator_chain

    @property
    def user_level(self):
        """Level user dalam snapshot/rantai verifikator, termasuk riwayat lama."""
        if hasattr(self, '_user_level'):
            return self._user_level
        user = self.request.user
        self._user_level = None
        for item in self.verifikator_chain:
            atasan = item["user"]
            if atasan and atasan.pk == user.pk:
                self._user_level = item['level']
                break
        return self._user_level

    @property
    def current_level(self):
        """Level yang dapat diedit; None berarti halaman hasil/read-only."""
        if hasattr(self, '_current_level'):
            return self._current_level

        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied

        if self.is_monitor_user():
            self._current_level = None
            return None

        level = self.user_level
        if level is None:
            if self.can_monitor_as_supervisor():
                self._current_level = None
                return None
            raise PermissionDenied(
                "Anda tidak tercatat sebagai verifikator pengajuan cuti ini."
            )

        verifikasi = self.get_verifikasi_obj()
        keputusan = getattr(verifikasi, f"keputusan{level}", 'belum')
        status_final = self.get_layanan_cuti().status in (
            'disetujui',
            'selesai',
            'ditolak',
        )
        self._current_level = (
            level
            if keputusan == 'belum' and not status_final
            else None
        )
        return self._current_level

    def is_monitor_user(self) -> bool:
        u = self.request.user
        return u.is_authenticated and u.is_cuti_admin

    def can_monitor_as_supervisor(self) -> bool:
        if not hasattr(self, '_can_monitor_as_supervisor'):
            self._can_monitor_as_supervisor = can_supervise_employee(
                self.request.user,
                self.get_layanan_cuti().pegawai,
            )
        return self._can_monitor_as_supervisor

    def is_read_only_mode(self) -> bool:
        return self.is_monitor_user() or self.current_level is None

    def dispatch(self, request, *args, **kwargs):
        if self.is_monitor_user():
            return super().dispatch(request, *args, **kwargs)

        if self.user_level is None and not self.can_monitor_as_supervisor():
            raise PermissionDenied(
                "Anda tidak tercatat sebagai verifikator pengajuan cuti ini."
            )
        return super().dispatch(request, *args, **kwargs)


class LayananCutiVerifikasiView(VerifikasiCutiAccessMixin, CheckCuti, UpdateView):
    """
    View khusus untuk verifikasi berjenjang (kasi/kabid/unor/dst).
    - URL: /layanan/cuti/<id>/verifikasi/
    - Objek: VerifikasiCuti (OneToOne dengan LayananCuti)
    """

    model = VerifikasiCuti
    template_name = "6_layanan_cuti/layanan_cuti_verifikasi.html"
    context_object_name = "verifikasi"

    def get_object(self, queryset=None):
        return self.get_verifikasi_obj()

    def get_form_class(self):
        level = self.current_level or self.user_level or 3
        if level == 1:
            return Verifikator1CutiForm
        elif level == 2:
            return Verifikator2CutiForm
        return Verifikator3CutiForm

    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.is_read_only_mode():
            for f in form.fields.values():
                f.disabled = True
        return form

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     kwargs.setdefault("request", self.request)
    #     return kwargs
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if self.is_read_only_mode():
            messages.info(
                request,
                "Hasil verifikasi hanya dapat dilihat dan tidak dapat diubah kembali.",
            )
            return redirect(request.path)  # stay di halaman yang sama

        layanan = self.get_layanan_cuti()
        Users.objects.select_for_update().get(pk=layanan.pegawai_id)
        riwayat = RiwayatCuti.objects.select_for_update().filter(usulan=layanan).first()
        if not riwayat:
            messages.error(request, "Detail pengajuan cuti tidak ditemukan.")
            return redirect("layanan_urls:layanan_cuti_bawahan_listview")
        if layanan.status in (
            'disetujui', 'selesai', 'ditolak', 'dibatalkan',
        ):
            messages.error(request, "Pengajuan ini sudah memiliki keputusan final dan tidak dapat diubah.")
            return redirect(request.path)
        if any(item['user'] is None for item in self.verifikator_chain):
            messages.error(request, "Rantai verifikator belum lengkap. Hubungi admin struktur organisasi.")
            return redirect(request.path)

        level = self.current_level
        verifikasi = self.get_verifikasi_obj()
        level_sebelumnya = [
            item['level'] for item in self.verifikator_chain if item['level'] < level
        ]
        if any(getattr(verifikasi, f'keputusan{lvl}') != 'setuju' for lvl in level_sebelumnya):
            messages.error(request, "Verifikasi pada level sebelumnya belum disetujui.")
            return redirect(request.path)

        if riwayat.jenis_cuti == self.CUTI_TAHUNAN:
            pelimpahan = getattr(riwayat, 'pelimpahan_tugas', None)
            if pelimpahan is None or not pelimpahan.is_final_approved():
                messages.error(request, "Pelimpahan tugas harus disetujui sebelum cuti diverifikasi.")
                return redirect(request.path)
        return super().post(request, *args, **kwargs)

    def _update_verifikator_user(self, verifikasi: VerifikasiCuti):
        """Set field verifikator1/2/3 dengan user login pada level-nya."""
        user = self.request.user
        level = self.current_level

        if level == 1 and hasattr(verifikasi, "verifikator1"):
            verifikasi.verifikator1 = user
        elif level == 2 and hasattr(verifikasi, "verifikator2"):
            verifikasi.verifikator2 = user
        elif level == 3 and hasattr(verifikasi, "verifikator3"):
            verifikasi.verifikator3 = user

    def _update_status_after_verifikasi(self, verifikasi: VerifikasiCuti):
        layanan = verifikasi.layanan_cuti

        riwayat = (
            RiwayatCuti.objects
            .filter(usulan=layanan)
            .order_by("-updated_at", "-id")
            .first()
        )

        active_levels = [item["level"] for item in self.verifikator_chain]

        keputusan_values = []
        for lvl in active_levels:
            keputusan_values.append(getattr(verifikasi, f"keputusan{lvl}", "belum"))

        ada_keputusan = any(k != "belum" for k in keputusan_values)

        # minimal tindaklanjut kalau sudah ada keputusan
        if ada_keputusan and layanan.status == "pengajuan":
            layanan.status = "tindaklanjut"

        # 1) Jika ADA TOLAK -> final ditolak
        if any(k == "tolak" for k in keputusan_values):
            layanan.status = "ditolak"
            if riwayat:
                riwayat.status_cuti = "Batal"
            layanan.save()
            if riwayat:
                riwayat.save()
            return

        # 2) Jika ADA TUNDA -> final jadi saldo tunda
        if any(k == "tunda" for k in keputusan_values):
            layanan.status = "disetujui"
            if riwayat:
                riwayat.status_cuti = "Tunda"
                # pastikan tahun_cuti terisi untuk tracking saldo
                if not riwayat.tahun_cuti:
                    riwayat.tahun_cuti = layanan.tahun
            layanan.save()
            if riwayat:
                riwayat.save()
            return

        # 3) Jika semua setuju -> final disetujui
        if keputusan_values and all(k == "setuju" for k in keputusan_values):
            layanan.status = "disetujui"
            layanan.save()
            if riwayat:
                riwayat.status_cuti = riwayat.tentukan_status_pelaksanaan()
                riwayat.save()
            return

        # 4) selain itu -> masih proses
        layanan.status = layanan.status or "tindaklanjut"
        layanan.save()
        if riwayat:
            riwayat.save()

    @transaction.atomic
    def form_valid(self, form):
        if self.is_monitor_user():
            messages.info(self.request, "Mode monitoring: tidak ada perubahan yang disimpan.")
            return redirect(self.request.path)
        
        verifikasi: VerifikasiCuti = form.save(commit=False)

        level = self.current_level
        keputusan = form.cleaned_data.get(f'keputusan{level}')
        level_terakhir = max(item['level'] for item in self.verifikator_chain)
        if keputusan == 'tunda' and level != level_terakhir:
            form.add_error(None, "Keputusan menunda hanya dapat diberikan oleh verifikator terakhir.")
            return self.form_invalid(form)

        # set verifikatorX = user login
        self._update_verifikator_user(verifikasi)

        setattr(verifikasi, f'diputuskan_pada{level}', timezone.now())
        if level == level_terakhir:
            sekarang = timezone.now()
            verifikasi.tanggal = (
                timezone.localtime(sekarang).date()
                if timezone.is_aware(sekarang)
                else sekarang.date()
            )

        verifikasi.save()

        # update status layanan & riwayat
        self._update_status_after_verifikasi(verifikasi)

        messages.success(self.request, "Verifikasi cuti berhasil disimpan.")
        return super().form_valid(form)

    def get_success_url(self):
        # setelah verifikasi, balik ke riwayat cuti bawahan
        return reverse_lazy("layanan_urls:layanan_cuti_bawahan_listview")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        layanan = self.get_layanan_cuti()
        verifikasi = self.get_verifikasi_obj()
        
        current_level = self.current_level
        user_level = self.user_level

        # riwayat cuti terkait (untuk ringkasan)
        riwayat = (
            RiwayatCuti.objects
            .filter(usulan=layanan)
            .order_by("-updated_at", "-id")
            .first()
        )
        pengangkatan = RiwayatPengangkatan.objects.filter(pegawai=layanan.pegawai).order_by('-id').first()
        status_pegawai = pengangkatan.desk_status_pegawai if pengangkatan else None
        ctx["status_pegawai"] = status_pegawai
        ctx["layanan_disetujui"] = layanan.status in ("disetujui", "selesai")

        # Siapkan chain untuk ditampilkan di UI
        chain_display = []
        for item in self.verifikator_chain:
            lvl = item["level"]
            user = item["user"]
            label = item["label"]

            pers_attr = f"keputusan{lvl}"
            catatan_attr = f"catatan{lvl}"
            
            catatan_val = getattr(verifikasi, catatan_attr, "")  # bisa kosong                
            pers_val = getattr(verifikasi, pers_attr, "belum")

            if pers_val == "setuju":
                status = "approved"
            elif pers_val == "tolak":
                status = "rejected"
            elif pers_val == "tunda":
                status = "deferred"
            else:
                status = "pending"

            chain_display.append({
                "level": lvl,
                "label": label,
                "user": user,
                "status": status,
                "catatan": catatan_val,
                "is_current": (user_level == lvl),
            })

        ctx.update({
            "title_page": "Verifikasi Pengajuan Cuti",
            "layanan": layanan,
            "riwayat": riwayat,
            "chain_display": chain_display,
            "current_level": current_level,
            "user_level": user_level,
            "view_only": self.is_read_only_mode(),
            "can_submit_verification": not self.is_read_only_mode(),
            "active_tab": "bawahan",
            "cek_sisa_cuti_pegawai": self.cek_sisa_cuti(layanan.pegawai),
            "cek_sisa_tunda_cuti_pegawai": self.cek_sisa_tunda_cuti(layanan.pegawai),
        })
        return ctx


class LayananCutiDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatCuti
    template_name = 'delete.html'
    success_url = reverse_lazy('layanan_urls:layanan_cuti_listview')
    success_message = "Data berhasil dihapus!"


class CutiPemutihanAdminView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Koreksi massal status pengajuan cuti dengan jejak audit."""

    template_name = '6_layanan_cuti/cuti_pemutihan_admin.html'
    allowed_actions = {'disetujui', 'selesai', 'ditolak', 'dibatalkan'}

    def test_func(self):
        return self.request.user.is_cuti_admin

    def _parse_date(self, value, default):
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            return default

    def _filters(self):
        today = date.today()
        return {
            'tanggal_mulai': self._parse_date(
                self.request.GET.get('tanggal_mulai')
                or self.request.POST.get('tanggal_mulai'),
                date(today.year, 1, 1),
            ),
            'tanggal_akhir': self._parse_date(
                self.request.GET.get('tanggal_akhir')
                or self.request.POST.get('tanggal_akhir'),
                today,
            ),
            'status': (
                self.request.GET.get('status')
                or self.request.POST.get('status')
                or 'proses'
            ),
            'q': (
                self.request.GET.get('q')
                or self.request.POST.get('q')
                or ''
            ).strip(),
        }

    def _queryset(self, filters):
        queryset = (
            LayananCuti.objects
            .select_related('pegawai__profil_user', 'cuti_usulan')
            .filter(
                created_at__date__gte=filters['tanggal_mulai'],
                created_at__date__lte=filters['tanggal_akhir'],
            )
            .order_by('created_at', 'id')
        )
        status = filters['status']
        if status == 'proses':
            queryset = queryset.filter(status__in=('pengajuan', 'tindaklanjut'))
        elif status in dict(STATUS_PENGAJUAN_CUTI):
            queryset = queryset.filter(status=status)
        if filters['q']:
            queryset = queryset.filter(
                Q(pegawai__first_name__icontains=filters['q'])
                | Q(pegawai__last_name__icontains=filters['q'])
                | Q(pegawai__email__icontains=filters['q'])
                | Q(pegawai__profil_user__nip__icontains=filters['q'])
            )
        return queryset

    def get(self, request, *args, **kwargs):
        filters = self._filters()
        queryset = self._queryset(filters)
        context = {
            'data': queryset[:500],
            'total_data': queryset.count(),
            'filters': filters,
            'status_choices': STATUS_PENGAJUAN_CUTI,
            'action_choices': (
                ('disetujui', 'Disetujui'),
                ('selesai', 'Selesai'),
                ('ditolak', 'Ditolak'),
                ('dibatalkan', 'Dibatalkan'),
            ),
            'recent_logs': (
                PemutihanCutiLog.objects
                .select_related('layanan_cuti__pegawai', 'admin')
                .all()[:50]
            ),
            'title_page': 'Pemutihan Pengajuan Cuti',
            'cuti': 'active',
            'layanan': 'active',
        }
        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        filters = self._filters()
        action = request.POST.get('aksi')
        catatan = (request.POST.get('catatan') or '').strip()
        selected_ids = request.POST.getlist('pengajuan_ids')

        if action not in self.allowed_actions:
            messages.error(request, 'Pilih keputusan pemutihan yang valid.')
            return self.get(request, *args, **kwargs)
        if not catatan:
            messages.error(request, 'Catatan/alasan pemutihan wajib diisi.')
            return self.get(request, *args, **kwargs)
        if not selected_ids:
            messages.error(request, 'Pilih minimal satu pengajuan cuti.')
            return self.get(request, *args, **kwargs)

        visible_ids = self._queryset(filters).filter(
            pk__in=selected_ids,
        ).values_list('pk', flat=True)
        layanan_list = list(
            LayananCuti.objects
            .select_for_update()
            .select_related('cuti_usulan')
            .filter(pk__in=visible_ids)
            .order_by('id')
        )
        if not layanan_list:
            messages.error(
                request,
                'Pengajuan terpilih tidak ditemukan pada hasil filter.',
            )
            return self.get(request, *args, **kwargs)

        logs = []
        for layanan in layanan_list:
            riwayat = getattr(layanan, 'cuti_usulan', None)
            status_pengajuan_lama = layanan.status
            status_pelaksanaan_lama = (
                riwayat.status_cuti if riwayat else ''
            )

            layanan.status = action
            layanan.is_read = True
            layanan.save(update_fields=('status', 'is_read', 'updated_at'))

            if riwayat:
                if action in ('ditolak', 'dibatalkan'):
                    riwayat.status_cuti = 'Batal'
                elif riwayat.status_cuti != 'Tunda':
                    riwayat.status_cuti = 'Belum'
                    riwayat.status_cuti = (
                        riwayat.tentukan_status_pelaksanaan(pada=date.today())
                    )
                riwayat.save(update_fields=('status_cuti', 'updated_at'))

            logs.append(PemutihanCutiLog(
                layanan_cuti=layanan,
                riwayat_cuti=riwayat,
                admin=request.user,
                aksi=action,
                status_pengajuan_sebelum=status_pengajuan_lama,
                status_pengajuan_sesudah=layanan.status,
                status_pelaksanaan_sebelum=status_pelaksanaan_lama,
                status_pelaksanaan_sesudah=(
                    riwayat.status_cuti if riwayat else ''
                ),
                catatan=catatan,
            ))

        PemutihanCutiLog.objects.bulk_create(logs)
        messages.success(
            request,
            f'{len(logs)} pengajuan cuti berhasil diubah menjadi '
            f'{dict(STATUS_PENGAJUAN_CUTI)[action]}.',
        )
        query = (
            f'?tanggal_mulai={filters["tanggal_mulai"].isoformat()}'
            f'&tanggal_akhir={filters["tanggal_akhir"].isoformat()}'
            f'&status={filters["status"]}'
        )
        return redirect(
            reverse('layanan_urls:cuti_pemutihan_admin') + query
        )


class GajiBerkalaCheck:
    def get_two_year_before(self, start_year) -> dict:
        end_year = start_year - relativedelta(months=22)
        date_interval = relativedelta(end_year, start_year)
        return {
            'interval_tahun': date_interval.years,
            'interval_bulan': date_interval.months
            }
    def get_two_year_after(self, start_year):
        today = datetime.today()
        date_interval = relativedelta(today, start_year)
        return {
            'interval_tahun': date_interval.years,
            'interval_bulan': date_interval.months
            } 
    
    def check_status(self, nip) -> bool:
        data = RiwayatGajiBerkala.objects.filter(pegawai__profil_user__nip=nip).values('tmt_gaji').last()
        try:
            status = None
            if self.get_two_year_after(data.get('tmt_gaji')).get('interval_tahun') >= 2:
                status = True
            elif self.get_two_year_after(data.get('tmt_gaji')).get('interval_tahun') == 1 and self.get_two_year_after(data.get('tmt_gaji')).get('interval_bulan') >= 9:
                status = True
            else:
                status = False
            # if statement with one line = True if self.get_two_year_after(data.get('tgl_srt_gaji')).get('interval_tahun') >= 1 and self.get_two_year_after(data.get('tgl_srt_gaji')).get('interval_bulan') >= 9 else False
            return status
        except Exception:
            return True
    
    def next_berkala(self, nip) -> date:
        data = RiwayatGajiBerkala.objects.filter(pegawai__profil_user__nip=nip).values('tmt_gaji')
        second_last_date = data.order_by('-tmt_gaji')
        if nip and len(second_last_date) >= 2:
            #jika TMT data pertama kosong akan tereksekusi data sebelumnya
            if second_last_date[0].get('tmt_gaji') is not None:
                data1 = second_last_date[0].get('tmt_gaji')+relativedelta(months=24)
                return data1
            data2 = second_last_date[1].get('tmt_gaji')+relativedelta(months=24)
            return data2
        elif nip and len(second_last_date) == 1:
            if second_last_date[0].get('tmt_gaji') is None:
                return None
            data3 = second_last_date[0].get('tmt_gaji')+relativedelta(months=24)
            return data3
        return None
    

class BerkalaListView(LoginRequiredMixin, ListView):
    """
    Menampilkan daftar monitoring gaji berkala pegawai.
    Menghitung interval kenaikan gaji berkala berikutnya dan mengurutkannya
    berdasarkan urgensi (yang paling dekat jatuh tempo berada di paling atas).
    """
    model = RiwayatGajiBerkala
    template_name = '3_layanan_berkala/layanan_berkala_list.html'
    context_object_name = 'data_berkala'

    def get_queryset(self):
        """
        Menggunakan Window Function (ROW_NUMBER) untuk mendapatkan data gaji berkala
        terakhir untuk setiap pegawai secara efisien. Solusi ini kompatibel dengan
        MariaDB dan lebih performan daripada subquery dengan LIMIT.
        """
        today = date.today()

        # Anotasi setiap baris RiwayatGajiBerkala dengan nomor urut (row_number)
        # - `partition_by=[F('pegawai')]`: Mengelompokkan data per pegawai.
        # - `order_by=F('tmt_gaji').desc()`: Mengurutkan riwayat gaji dari yang terbaru.
        # - `RowNumber()`: Memberikan nomor urut 1, 2, 3, ... dalam setiap kelompok.
        latest_berkala_qs = RiwayatGajiBerkala.objects.annotate(
            row_number=Window(
                expression=RowNumber(),
                partition_by=[F('pegawai')],
                order_by=F('tmt_gaji').desc()
            )
        ).select_related('pegawai', 'pegawai__profil_user').filter(row_number=1)

        processed_data = []
        for berkala in latest_berkala_qs:
            tmt_gaji = berkala.tmt_gaji
            if not isinstance(tmt_gaji, date):
                # Log peringatan untuk data yang bermasalah agar bisa diperbaiki
                logger.warning(
                    f"Data gaji berkala dengan id {berkala.pk} untuk pegawai '{berkala.pegawai}' "
                    f"memiliki TMT Gaji yang tidak valid (tipe: {type(tmt_gaji)}, nilai: '{tmt_gaji}'). "
                    "Data ini dilewati."
                )
                continue  # Lewati record ini dan lanjut ke record
            # Hitung tanggal jatuh tempo kenaikan gaji berkala berikutnya (2 tahun dari TMT terakhir)
            next_due_date = berkala.tmt_gaji + relativedelta(years=2) if berkala.tmt_gaji is not None else 0
            
            # Hitung sisa hari hingga jatuh tempo
            days_until_due = (next_due_date - today).days
            
            # Kategorisasi interval dan tentukan kunci untuk pengurutan
            interval_category = ""
            interval_sort_key = 0  # 0 untuk paling mendesak, 2 untuk paling lama

            if days_until_due < 0:
                interval_category = "Terlewat"
                interval_sort_key = -1
            elif days_until_due < 90:  # < 3 bulan (diasumsikan 1 bulan = 30 hari)
                interval_category = "< 3 bulan"
                interval_sort_key = 0
            elif days_until_due < 180: # >= 3 bulan dan < 6 bulan
                interval_category = ">= 3 bulan"
                interval_sort_key = 1
            else: # >= 6 bulan
                interval_category = ">= 6 bulan"
                interval_sort_key = 2

            if berkala.is_final:
                berkala_status = 'final'
            elif berkala.has_layanan:
                berkala_status = 'proses'
            else:
                berkala_status = ''
                
            #dapatkan NIP untuk dikirim ke template
            nip = berkala.pegawai.profil_user.nip if berkala.pegawai is not None and hasattr(berkala.pegawai, 'profil_user') else None
            
            #dapatkan layanan_id untuk dikirim ke template
            berkala_saat_ini = berkala.berkala_saat_ini.first()
            layanan_id = berkala_saat_ini.pk if berkala_saat_ini is not None else None
             
            # Siapkan data untuk ditampilkan di template
            processed_data.append({
                'berkala_pk': berkala.pk,
                'layanan_id': layanan_id,
                'pegawai_pk': berkala.pegawai.pk,
                'pegawai_nip': nip,
                'nama_pegawai': berkala.pegawai.full_name_2,
                'berkala_terakhir': berkala.tmt_gaji,
                'next_due_date': next_due_date,
                'interval_category': interval_category,
                'interval_sort_key': interval_sort_key,
                'days_until_due': days_until_due,
                'berkala_status': berkala_status
            })

        # Urutkan data di Python berdasarkan kategori dan sisa hari
        sorted_data = sorted(processed_data, key=lambda x: (x['interval_sort_key'], x['days_until_due']))

        return sorted_data
    
    def get_context_data(self):
        context = super().get_context_data()
        context.update({
            'berkala':'active',
            'layanan':'active',
            'title_page':'Layanan Gaji Berkala',
            'selected':'yanberkala'
        })
        return context


def createlayananberkala(request, riwayat_id):
    if not request.user.is_authenticated or not request.user.is_berkala_admin:
        raise PermissionDenied
    try:
        riwayat_berkala = RiwayatGajiBerkala.objects.get(id=riwayat_id)
        jenis_layanan = JenisLayanan.objects.filter(url='yanberkala').first()
        nip = riwayat_berkala.pegawai.profil_user.nip if riwayat_berkala.pegawai and hasattr(riwayat_berkala.pegawai, 'profil_user') else None
        # if riwayat_berkala.has_layanan and not riwayat_berkala.is_final:
        #     messages.error(request, f'Gaji berkala sedang dalam proses silahkan akses di menu admin panel untuk melihat secara detail!')
        #     return redirect(reverse('layanan_urls:layanan_berkala_view'))
        # elif riwayat_berkala.is_final:
        #     messages.error(request, f'SK gaji berkala sudah dibuat!')
        #     return redirect(reverse('layanan_urls:layanan_berkala_view'))
        data, _ = LayananGajiBerkala.objects.get_or_create(
            pegawai=riwayat_berkala.pegawai,
            layanan=jenis_layanan,
            riwayat=riwayat_berkala,
            status='pengajuan'
        )
        
        messages.success(request, 'Layanan Gaji Berkala berhasil dibuat!')
        return redirect(reverse('layanan_urls:layanan_berkala_admin_view', kwargs={'layanan_id':data.pk, 'nip':nip}))
    except Exception as e:
        messages.error(request, f'Maaf layanan gaji berkala gagal dibuat! Error: {str(e)}')
        return redirect(reverse('layanan_urls:layanan_berkala_view'))
    
    

class LayananGajiBerkalaUpdateView(LoginRequiredMixin, GajiBerkalaCheck, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    redirect_display = 'layanan_urls:layanan_berkala_view'
    def detail_object(self, id):
        try:
            layanan = LayananGajiBerkala.objects.get(id=id)
            return layanan
        except Exception:
            return None
    
    def get(self, request, **kwargs):
        id_obj = kwargs.get('id')
        instance = self.detail_object(id_obj)
        form = FormLayananBerkala(instance=instance, request=request)
        context = {
            'update_form':True,
            'form':form,
            'form_view':'block',
            'data_view':'none',
            'berkala':'active',
            'layanan':'active',
            'title_page':'Layanan Gaji Berkala',
            'selected':'yanberkala'
        }
        return render(request, '3_layanan_berkala/layanan_berkala_master.html', context)
    
    def post(self, request, **kwargs):
        id_obj = kwargs.get('id')
        instance = self.detail_object(id_obj)
        form = FormLayananBerkala(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data berhasil diupdate!')
            return redirect(reverse(self.redirect_display))
        for field, errors in form.errors.items():
                for error in errors:
                    if error:
                        messages.error(request, error)
                    else:
                        messages.error(request, 'Maaf data gagal diupdate!')
        return redirect(reverse(self.redirect_display))
    

class LayananGajiBerkalaAdminView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def test_func(self):
        return self.request.user.is_berkala_admin

    def get_object(self, layanan_id):
        try:
            data = LayananGajiBerkala.objects.get(id=layanan_id)
            return data
        except Exception:
            return None
        
    def get_user(self, nip):
        try: 
            data = Users.objects.get(profil_user__nip=nip)
            return data
        except Exception:
            return None
    
    def get(self, request, **kwargs):
        layanan_id = kwargs.get('layanan_id')
        detail = self.get_object(layanan_id)
        selected_nip = kwargs.get('nip')
        nip = None
        if request.user.is_berkala_admin:
            nip = selected_nip
        else:
            nip = get_nip(request.user)

        pegawai = self.get_user(nip)
        data = LayananGajiBerkala.objects.filter(pegawai=pegawai)
        
        context={
            'layanan_id':layanan_id,
            'data':data,
            'detail': detail,
            'berkala':'active',
            'layanan':'active',
            'title_page':'Layanan Gaji Berkala',
            'selected':'yanberkala'
        }
        return render(request, '3_layanan_berkala/layanan_berkala_admin_view.html', context)


class LayananGajiBerkalaAdminAddView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def test_func(self):
        return self.request.user.is_berkala_admin
        
    def get_user(self, nip):
        try: 
            data = Users.objects.get(profil_user__nip=nip)
            return data
        except Exception:
            return None

    def get(self, request, **kwargs):
        selected_nip = kwargs.get('nip')
        dokumen = DokumenSDM.objects.filter(url='berkala')
        nip = None
        if request.user.is_berkala_admin:
            nip = selected_nip
        else:
            nip = get_nip(request.user)

        pegawai = self.get_user(nip)
        panggol = RiwayatPanggol.objects.filter(pegawai__profil_user__nip=nip)
        tempat_kerja = RiwayatPenempatan.objects.filter(pegawai__profil_user__nip=nip)
        initial = {
            'pegawai':pegawai,
            'dokumen':dokumen.first(),
            'pangkat':panggol.last(),
            'tempat_kerja':tempat_kerja.last()
        }
        form = RiwayatGajiBerkalaForm(initial=initial)
        context={
            'update_form':True,
            'pegawai':pegawai,
            'form':form,
            'form_view':'block',
            'data_view':'none',
            'berkala':'active',
            'layanan':'active',
            'title_page':'Layanan Gaji Berkala',
            'selected':'yanberkala'
        }
        return render(request, '3_layanan_berkala/layanan_berkala_master.html', context)
    
    def post(self, request, **kwargs):
        layanan_id = kwargs.get('layanan_id')
        nip = kwargs.get('nip')
        form = RiwayatGajiBerkalaForm(data=request.POST)
        if form.is_valid():
            with transaction.atomic():
                berkala = form.save(commit=False)
                berkala.has_layanan = True
                berkala.save()
                LayananGajiBerkala.objects.filter(id=layanan_id).update(berkala=berkala, status='proses')
                messages.success(request, 'Gaji berkala berhasil dibuat..')
                return redirect(reverse('layanan_urls:layanan_berkala_admin_view', kwargs={'layanan_id':layanan_id, 'nip':nip} ))
        else:
            messages.error(request, 'Maaf ada kesalahan pada pengisian form, silahkan pastikan kembali isian yang anda lakukan!!')
            return redirect(reverse('layanan_urls:layanan_berkala_admin_add_view', kwargs={'layanan_id':layanan_id, 'nip':nip} ))
        

class LayananGajiBerkalaUpload(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def test_func(self):
        return self.request.user.is_berkala_admin

    def get_object(self, id):
        try:
            data = RiwayatGajiBerkala.objects.get(id=id)
            return data
        except Exception:
            return None
        
    def get(self, request, **kwargs):
        berkala_id = kwargs.get('berkala_id')
        status_post = request.GET.get('action')
        instance = self.get_object(berkala_id)
        form = RiwayatGajiBerkalaForm(instance=instance, action=status_post)
        context={
            'update_form':True,
            'form':form,
            'form_view':'block',
            'data_view':'none',
            'berkala':'active',
            'layanan':'active',
            'title_page':'Layanan Gaji Berkala',
            'selected':'yanberkala'
        }
        return render(request, '3_layanan_berkala/layanan_berkala_master.html', context)
    
    def post(self, request, **kwargs):
        berkala_id = kwargs.get('berkala_id')
        layanan_id = kwargs.get('layanan_id')
        status_post = request.GET.get('action')
        nip = kwargs.get('nip')
        berkala_existing = self.get_object(id=berkala_id)
        instance = self.get_object(id=berkala_id)
        form = RiwayatGajiBerkalaForm(data=request.POST, files=request.FILES, action=status_post, instance=instance)
        layanan = LayananGajiBerkala.objects.filter(id=layanan_id)
        url_reverse = reverse('layanan_urls:layanan_berkala_admin_view', kwargs={"layanan_id":layanan_id, "nip":nip})
        if form.is_valid():
            with transaction.atomic():
                data_submitted = form.save(commit=False)
                file = berkala_existing.file if berkala_existing is not None and hasattr(berkala_existing, 'file') else None
                delete_existing_object(data_submitted, berkala_existing, file)
                data_submitted.is_final = True
                data_submitted.save()
                layanan.update(status='selesai')
                messages.success(request, 'Data berhasil diupload!')
                return redirect(f'{url_reverse}')
        for field, errors in form.errors.items():
                for error in errors:
                    if error:
                        messages.error(request, error)
                    else:
                        messages.error(request, 'Data gagal diupdate!')
        return redirect(f'{url_reverse}?action=upload')


class PengalihanDiklatCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = LayananUsulanDiklat
    form_class = FormPengalihanUsulanDiklat
    template_name = '7_layanan_diklat/layanan_diklat_pengalihan.html'
    success_url = reverse_lazy('layanan_urls:layanan_diklat_staf_view')

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_diklat_admin
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        data = self.get_object()
        kwargs['initial'] = {
            'layanan':data.layanan, 'tor':data.tor, 
            'brosur':data.brosur, 'pembiayaan':data.pembiayaan, 'biaya':data.biaya, 'status':data.status
        }
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data_usulan = self.get_object()
        data_riwayat = RiwayatDiklat.objects.filter(usulan=data_usulan).first()
        initial = None
        if data_riwayat:
            initial = [{
                'dokumen':data_riwayat.dokumen, 'jenis_diklat':data_riwayat.jenis_diklat, 'nama_diklat':data_riwayat.nama_diklat, 'penyelenggara':data_riwayat.penyelenggara, 'metode':data_riwayat.metode, 
                'skp':data_riwayat.skp, 'tgl_mulai':data_riwayat.tgl_mulai, 'tgl_selesai':data_riwayat.tgl_selesai, 'kategori_kompetensi':data_riwayat.kategori_kompetensi, 'kompetensi':data_riwayat.kompetensi,
            }]
        if self.request.POST:
            context['riwayat_form'] = pengalihan_diklat_formset(data=self.request.POST, form_kwargs={'request': self.request})
        else:
            context['riwayat_form']=pengalihan_diklat_formset(initial=initial, form_kwargs={'request': self.request})
        context['riwayat_object'] = data_riwayat
        context['diklat'] = 'active'
        context['layanan'] = 'active'
        context['card_title'] = 'Pengalihan Diklat'
        context['title_page'] = 'Layanan Diklat'
        context['selected'] = 'yandiklat'
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        usulan_pengusul = self.get_object()
        #form pengalihan
        riwayat_form = context['riwayat_form']
        if form.is_valid() and riwayat_form.is_valid():
            self.object = form.save()
            pegawai = riwayat_form.cleaned_data[0].get('pegawai')
            for riwayat in riwayat_form:
                data_riwayat = riwayat.save(commit=False)
                data_riwayat.usulan = self.object
                data_riwayat.is_usulan = True
                data_riwayat.save()
                data_riwayat.pegawai.set(pegawai)
            #Tolak pengusul awal
            usulan_pengusul.status = 'tidak ditindaklanjut'
            usulan_pengusul.save()
            messages.success(self.request, 'Data berhasil disimpan!')
            return super().form_valid(form)
        # messages.error(self.request, 'Maaf terdapat kesalahan atau kurang data dalam pengisian form')
        print('form: ', form.errors)
        print('layana_form: ', riwayat_form.errors)
        return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Data gagal disimpan!')
        return super().form_invalid(form)

        
class PenugasanDiklatCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = LayananUsulanDiklat
    form_class = FormPenugasanUsulanDiklat
    template_name = '7_layanan_diklat/layanan_diklat_form.html'
    success_url = reverse_lazy('layanan_urls:layanan_diklat_staf_view')

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_diklat_admin
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        layanan = JenisLayanan.objects.filter(url='yandiklat').first()
        kwargs['initial'] = {'layanan':layanan}
        kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dokumen = DokumenSDM.objects.filter(url='diklat').first()
        initial = {'dokumen':dokumen}
        context['riwayat_form']=penugasan_inline_formset(self.request.POST or None, initial=[initial], form_kwargs={'request':self.request})
        context['card_title'] = 'Buat Penugasan Diklat'
        context['diklat']='active'
        context['layanan']='active'
        context['title_page']='Layanan Diklat'
        context['selected']='yandiklat'
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        riwayat_form = context['riwayat_form']
        if riwayat_form.is_valid():
            self.object = form.save()
            pegawai = riwayat_form.cleaned_data[0].get('pegawai')
            for item in riwayat_form:
                data_riwayat = item.save(commit=False)
                data_riwayat.usulan = self.object
                data_riwayat.is_usulan = True
                data_riwayat.save()
                data_riwayat.pegawai.set(pegawai)
            messages.success(self.request, 'Data berhasil disimpan!')
            return super().form_valid(form)
        print('riwayatform: ', riwayat_form.errors)
        print('form: ', form.errors)
        return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Data gagal disimpan!')
        return super().form_invalid(form)

class LayananUsulanDiklatStaffView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    template_name = '7_layanan_diklat/layanan_diklat_list.html'
    model = LayananUsulanDiklat

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_diklat_admin
    
    def get_queryset(self):
        queryset = None
        if self.request.user.is_staff and not self.request.user.is_diklat_admin:
            penempatan_admin = self.request.user.riwayat_penempatan.filter(status=True).last()
            if penempatan_admin:
                queryset=self.model.objects.filter(
                        riwayatdiklat__pegawai__riwayat_penempatan__penempatan_level3__sub_bidang=penempatan_admin.penempatan, riwayatdiklat__pegawai__riwayat_penempatan__status=True
                    ).order_by('-id').exclude(riwayatdiklat__pegawai=self.request.user).distinct()|self.model.objects.filter(
                        riwayatdiklat__pegawai__riwayat_penempatan__penempatan_level2__bidang=penempatan_admin.penempatan, riwayatdiklat__pegawai__riwayat_penempatan__status=True
                    ).order_by('-id').exclude(riwayatdiklat__pegawai=self.request.user).distinct()|self.model.objects.filter(
                        riwayatdiklat__pegawai__riwayat_penempatan__penempatan_level1__unor=penempatan_admin.penempatan, riwayatdiklat__pegawai__riwayat_penempatan__status=True
                    ).order_by('-id').exclude(riwayatdiklat__pegawai=self.request.user).distinct()  
        elif self.request.user.is_diklat_admin:
            queryset = super().get_queryset()
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # for item in Kompetensi.objects.all():
        #     item.pegawai.add(item.pegawai_old)
        context['card_title'] = 'Daftar Usulan Diklat Staff'
        context['diklat'] = 'active'
        context['layanan'] = 'active'
        context['title_page'] = 'Layanan Diklat'
        context['selected'] = 'yandiklat'
        return context
    
    
class LayananUsulanDiklatListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    model = LayananUsulanDiklat
    
    def get_queryset(self):
        nip = get_nip(self.request.user)
        if not self.request.user.is_diklat_admin and nip:
            queryset = LayananUsulanDiklat.objects.filter(riwayatdiklat__pegawai__profil_user__nip=nip).order_by('-id')
        else:
            queryset = LayananUsulanDiklat.objects.all().order_by('-id')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nip = get_nip(self.request.user)
        context['card_title'] = 'Riwayat Usulan Diklat'
        if not self.request.user.is_diklat_admin and nip:
            context['card_title'] = 'Riwayat Diklat Saya'
        context['diklat']='active'
        context['layanan']='active'
        context['title_page']='Layanan Diklat'
        context['selected']='yandiklat'
        return context
    
    def get_template_names(self):
        if self.request.user.is_diklat_admin:
            return ['7_layanan_diklat/layanan_diklat_list.html']
        return ['7_layanan_diklat/layanan_diklat_perorang.html']
    
    
class LayananUsulanDiklatCreateView(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    model = LayananUsulanDiklat
    form_class = FormUsulanLayananDiklat
    template_name = '7_layanan_diklat/layanan_diklat_form.html'
    success_url = reverse_lazy('layanan_urls:layanan_diklat_list_view')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        layanan = JenisLayanan.objects.filter(url='yandiklat')
        kwargs['initial'] = {'layanan':layanan.first()}
        kwargs['request']=self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nip = get_nip(self.request.user)
        user = Users.objects.filter(profil_user__nip=nip)
        dokumen = DokumenSDM.objects.filter(url='diklat')
        initial = [{'dokumen':dokumen.first()}]
        if not self.request.user.is_diklat_admin:
            initial = [{
                'pegawai':user, 'dokumen':dokumen.first()
            }]
        context['riwayat_form']=usulan_diklat_formset(data=self.request.POST or None, initial=initial, form_kwargs={'request':self.request})
        context['card_title']='Usulan Diklat'
        context['diklat']='active'
        context['layanan']='active'
        context['title_page']='Layanan Diklat'
        context['selected']='yandiklat'
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        riwayat_form = context['riwayat_form']
        if form.is_valid() and riwayat_form.is_valid():
            self.object = form.save()
            for item in riwayat_form:
                data_riwayat = item.save(commit=False)
                data_riwayat.usulan = self.object
                data_riwayat.is_usulan = True
                data_riwayat.save()
                pegawai_diklat = riwayat_form.cleaned_data[0].get('pegawai')
                data_riwayat.pegawai.set(pegawai_diklat)
                pegawai_snapshot = pegawai_diklat.first()
                if pegawai_snapshot:
                    ensure_diklat_verifier_snapshot(self.object, pegawai_snapshot)
            messages.success(self.request, 'Data berhasil disimpan!')
            return super().form_valid(form)
        print('form: ', form.errors)
        print('riwayat_form: ', riwayat_form.errors)
        return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Data gagal disimpan!')
        return super().form_invalid(form)
    
    
# LayananUsulanDiklatView ini tidak digunakan, hanya mengetahui logic awal saja    
class LayananUsulanDiklatView(LoginRequiredMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def get_user(self, nip):
        try: 
            data = Users.objects.get(profil_user__nip=nip)
            return data
        except Exception:
            return None
        
    def get(self, request, *args, **kwargs):
        selected_nip = kwargs.get('nip')
        user = request.user
        dokumen = DokumenSDM.objects.filter(url='diklat')
        layanan = JenisLayanan.objects.filter(url='yandiklat')
        data = LayananUsulanDiklat.objects.all()
        initial_riwayat = {'dokumen':dokumen.first()}
        initial = {'layanan':layanan.first()}
        nip = None
        detail = None
        if not user.is_diklat_admin:
            nip = get_nip(user)
            initial_riwayat = {'pegawai':user, 'dokumen':dokumen.first()}
            initial = {'pegawai':user, 'layanan':layanan.first()}
            if nip:
                data = LayananUsulanDiklat.objects.filter(pegawai__profil_user__nip=nip)
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'layanan', 'selected':'yandiklat'}))
            
        riwayat_form = FormUsulanRiwayatDiklat(initial=initial_riwayat, request=request)
        form = usulan_diklat_formset(initial=[initial], form_kwargs={'request': request})
        context={
            'nip':nip,
            'data':data,
            'detail':detail,
            'riwayat_form':riwayat_form,
            'form':form,
            'form_view':'none',
            'data_view':'block',
            'diklat':'active',
            'layanan':'active',
            'title_page':'Layanan Diklat',
            'selected':'yandiklat'
        }
        return render(request, '7_layanan_diklat/layanan_diklat_master.html', context)
    
    def post(self, request, *args, **kwargs):
        riwayat_form = FormUsulanRiwayatDiklat(data=request.POST, files=request.FILES, request=request)
        form = usulan_diklat_formset(data=request.POST, files=request.FILES)
        if riwayat_form.is_valid() and form.is_valid():
            data_riwayat = riwayat_form.save()
            for item in form:
                if item.is_valid():
                    data_usulan = item.save(commit=False)
                    data_usulan.diklat = data_riwayat
                    data_usulan.save()
            messages.success(request, 'Data berhasil disimpan!')    
            return redirect(reverse('layanan_urls:layanan_diklat_view'))
        messages.error(request, 'Maaf data gagal disimpan!')
        return redirect(reverse('layanan_urls:layanan_diklat_view'))


context_tindaklanjut_diklat = {
    'diklat': 'active',
    'layanan': 'active',
    'title_page': 'Layanan Diklat',
    'selected': 'yandiklat'
    }

class LayananUsulanDiklatUpdateView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    model = LayananUsulanDiklat
    success_url = reverse_lazy('layanan_urls:layanan_diklat_list_view')

    def dispatch(self, request, *args, **kwargs):
        if request.GET.get('case') == 'spt' and not request.user.is_diklat_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.GET.get('case') == 'proses' and not request.user.is_diklat_admin:
            raise PermissionDenied
        return super().post(request, *args, **kwargs)
    
    def get_form_class(self):
        case_data = self.request.GET.get('case')
        if case_data == 'laporan':
            return FormLayananDiklatLaporan
        elif case_data == 'proses':
            return FormLayananDiklatProses
        elif case_data == 'spt':
            return FormLayananDiklatSPT
        return FormUsulanLayananDiklat
    
    def get_template_names(self):
        case_data = self.request.GET.get('case')
        if case_data == 'laporan':
            return ['7_layanan_diklat/layanan_diklat_form.html']
        elif case_data == 'proses':
            return ['7_layanan_diklat/layanan_diklat_proses.html']
        elif case_data == 'spt':
            return ['7_layanan_diklat/layanan_diklat_spt.html']
        elif case_data == 'detail':
            return ['7_layanan_diklat/layanan_diklat_detail.html']
        return ['7_layanan_diklat/layanan_diklat_form.html']
    
    def get_verification_object(self, diklat):
        layanan_diklat = self.get_object()
        if layanan_diklat:
            data, _ = VerifikasiDiklat.objects.get_or_create(layanan_diklat=layanan_diklat)
            return data
        return None
    
    def get_verifikator_form(self, get_case, get_level, verifikasi_diklat):
        if get_case == 'proses':
            if get_level == '1':
                return Verifikator1DiklatForm(self.request.POST or None, instance=verifikasi_diklat)
            elif get_level == '2':
                return Verifikator2DiklatForm(self.request.POST or None, instance=verifikasi_diklat)
            elif get_level == '3':
                return Verifikator3DiklatForm(self.request.POST or None, instance=verifikasi_diklat)
        return VerifikatorDiklatForm(self.request.POST or None, instance=verifikasi_diklat)
    
    def check_if_riwayatpenempatan(self, instance):
        data = RiwayatDiklat.objects.filter(usulan=instance).first()
        if data:
            penempatan = data.pegawai.first().riwayat_penempatan.filter(status=True).last() if data.pegawai.first() is not None else None 
            if penempatan is not None:
                return penempatan
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.get_object()
        level = self.request.GET.get('level')
        riwayat_object = RiwayatDiklat.objects.filter(usulan=instance).first()
        
        if self.request.GET.get('case') == 'laporan':
            context['riwayat_form']=laporan_diklat_formset(data=self.request.POST or None, files=self.request.FILES or None, instance=instance)
            context['card_title']='Laporan Diklat'
        elif self.request.GET.get('case') == 'proses':
            instalasi = self.check_if_riwayatpenempatan(instance)
            if not instalasi:
                context['error_penempatan'] = 0
                context['penempatan_notfound'] = 'Cek data penempatan pegawai'
                context['card_title'] = 'Error penempatan'
                return context
            nama_verifikator = instalasi.nama_atasan if instalasi else {}
            direktur = get_active_leader(instalasi.penempatan_level1)
            nama_verifikator.update({
                'direktur': getattr(direktur, 'full_name_2', None),
                'nip_direktur': getattr(getattr(direktur, 'profil_user', None), 'nip', None),
            })
            verifikator_object = self.get_verification_object(instance)
            context['nama_verifikator'] = nama_verifikator
            context['riwayat_form']=proses_diklat_formset(data=self.request.POST or None, files=self.request.FILES or None, instance=instance)
            context['card_title']='Proses Usulan Diklat'
            #proses submit untuk form verifikasi divalidasi di view yang berbeda yaitu pada view --> VerfiikasiDiklatView
            context['verifikator_form'] = self.get_verifikator_form(self.request.GET.get('case'), level, verifikator_object)
        elif self.request.GET.get('case') == 'spt':
            context['riwayat_form']=spt_diklat_formset(data=self.request.POST or None, files=self.request.FILES or None, instance=instance, form_kwargs={'request':self.request})
            context['card_title']='SPT Diklat'
        else:
            context['riwayat_form']=update_diklat_formset(data=self.request.POST or None, files=self.request.FILES or None, instance=instance, form_kwargs={'request':self.request})
            context['card_title']='Update Usulan Diklat'
        #object yanobj digunakan untuk memastikan apakah usulan telah diverifikasi atau belum
        context['riwayatobj'] = riwayat_object
        context['level'] = level
        context.update(context_tindaklanjut_diklat)
        return context
        
    def form_valid(self, form):
        context = self.get_context_data()
        instance = self.get_object()
        layanan_case = self.request.GET.get('case')
        riwayat_object = RiwayatDiklat.objects.filter(usulan=instance).first()
        riwayat_form = context['riwayat_form']
        if form.is_valid() and riwayat_form.is_valid():
            self.object = form.save(commit=False)
            # memproses status usulan
            data_status = ['tindaklanjut', 'selesai']
            if layanan_case == 'proses'  and not any(data == self.object.status for data in data_status):
                self.object.status = 'proses'
            elif layanan_case == 'spt' and self.object.status != 'selesai':
                self.object.status = 'tindaklanjut'
            elif layanan_case == 'laporan' and riwayat_form.cleaned_data[0].get('file_laporan'):
                self.object.status = 'selesai'
            #memproses file yang diupload (menghapus file lama jika ada)
            if self.object.brosur:
                if instance.brosur and self.object.brosur != instance.brosur and os.path.exists(instance.brosur.path.strip()):
                    os.remove(instance.brosur.path)
            if self.object.spt:
                if instance.spt and self.object.spt != instance.spt and os.path.exists(instance.spt.path.strip()):
                    os.remove(instance.spt.path)
            if self.object.bukti_lunas:
                if instance.bukti_lunas and self.object.bukti_lunas != instance.bukti_lunas and os.path.exists(instance.bukti_lunas.path.strip()):
                    os.remove(instance.bukti_lunas.path)
            self.object.save()
            for item in riwayat_form:
                data_riwayat = item.save(commit=False)
                data_riwayat.usulan = self.object
                if data_riwayat.file:
                    if riwayat_object.file and data_riwayat.file != riwayat_object.file and os.path.exists(riwayat_object.file.path):
                        os.remove(riwayat_object.file.path)
                if data_riwayat.file_laporan:
                    if riwayat_object.file_laporan and data_riwayat.file_laporan != riwayat_object.file_laporan and os.path.exists(riwayat_object.file_laporan.path):
                        os.remove(riwayat_object.file_laporan.path)
                data_riwayat.save()
            messages.success(self.request, 'Data berhasil disimpan!')
            return super().form_valid(form)
        print('riwayat_form: ', riwayat_form.errors)
        print('form: ', form.errors)
        return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Data gagal disimpan!')
        return super().form_invalid(form)
    

class VerifikasiDiklatView(LoginRequiredMixin, UpdateView):
    model = VerifikasiDiklat
    
    def get_form_class(self):
        level = self.request.GET.get('level')
        if level == '1':
            return Verifikator1DiklatForm
        elif level == '2':
            return Verifikator2DiklatForm
        elif level == '3':
            return Verifikator3DiklatForm
        return VerifikatorDiklatForm
    
    def get_success_url(self):
        url = reverse('layanan_urls:layanan_diklat_update_view', kwargs={'pk':self.get_object().layanan_diklat.id})
        return f'{url}?case=proses#close'
    
    def form_valid(self, form):
        if form.is_valid():
            form_submitted = form.save(commit=False)
            level = self.request.GET.get('level')
            if level == '1':
                form_submitted.verifikator1 = self.request.user
            elif level == '2':
                form_submitted.verifikator2 = self.request.user
            elif level == '3':
                form_submitted.verifikator3 = self.request.user
                form_submitted.tanggal = date.today()
            form_submitted.save()
        messages.success(self.request, 'Data berhasil disimpan!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Data gagal disimpan!')
        url = reverse('layanan_urls:layanan_diklat_update_view', kwargs={'pk':self.get_object().riwayatdiklat.id})
        return redirect(f'{url}?case=proses#openModal')


class CatatanSDMUsulanLayananDiklatUpdateView(
    LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    model = LayananUsulanDiklat
    form_class = FormCatatanSDMUsulanLayananDiklat
    template_name = '7_layanan_diklat/layanan_diklat_catatan_sdm.html'

    def test_func(self):
        return self.request.user.is_diklat_admin
    
    def get_success_url(self):
        url = reverse('layanan_urls:layanan_diklat_update_view', kwargs={'pk':self.get_object().id})
        return f'{url}?case=proses'
    
    def form_valid(self, form):
        if form.is_valid():
            form.save()
        messages.success(self.request, 'Data berhasil disimpan!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['card_title'] = 'Catatan SDM'
        return context
    
    def form_invalid(self, form):
        messages.error(self.request, 'Data gagal disimpan!')
        url = reverse('layanan_urls:layanan_diklat_update_view', kwargs={'pk':self.get_object().id})
        return redirect(f'{url}?case=proses')
    

class LayananUsulanInovasiView(LoginRequiredMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def get_user(self, nip):
        try: 
            data = Users.objects.get(profil_user__nip=nip)
            return data
        except Exception:
            return None
        
    def get(self, request, *args, **kwargs):
        user = request.user
        dokumen = DokumenSDM.objects.filter(url='inovasi')
        layanan = JenisLayanan.objects.filter(url='yaninovasi')
        data = LayananUsulanInovasi.objects.all()
        initial_riwayat = {'dokumen':dokumen.first()}
        initial = {'layanan':layanan.first(), 'status':'usulan'}
        nip = None
        card_title = 'Riwayat Usulan Inovasi'
        if not request.user.is_inovasi_admin:
            initial_riwayat = {'pegawai':user, 'dokumen':dokumen.first()}
            initial = {'pegawai':user, 'layanan':layanan.first(), 'status':'usulan'}
            nip = get_nip(user)
            if nip:
                data = LayananUsulanInovasi.objects.filter(pegawai__profil_user__nip=nip)
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'layanan', 'selected':'yaninovasi'}))
        
        riwayat_form = RiwayatInovasiForm(initial=initial_riwayat, request=request)
        form = inovasi_formset(initial=[initial], form_kwargs={'request': request})
        context={
            'nip':nip,
            'data':data,
            'riwayat_form':riwayat_form,
            'form':form,
            'card_title':card_title,
            'form_view':'none',
            'data_view':'block',
            'inovasi':'active',
            'layanan':'active',
            'title_page':'Layanan Inovasi',
            'selected':'yaninovasi'
        }
        return render(request, '8_layanan_inovasi/layanan_inovasi_master.html', context)
    
    def post(self, request, *args, **kwargs):
        riwayat_form = RiwayatInovasiForm(data=request.POST, files=request.POST, request=request)
        form = inovasi_formset(data=request.POST, files=request.FILES, form_kwargs={'request': request})
        if riwayat_form.is_valid() and form.is_valid():
            data_riwayat = riwayat_form.save()
            for item in form:
                if item.is_valid():
                    inovasi = item.save(commit=False)
                    inovasi.pegawai = data_riwayat.pegawai 
                    inovasi.inovasi = data_riwayat
                    inovasi.save()
            messages.success(request, 'Data berhasil disimpan!')    
            return redirect(reverse('layanan_urls:layanan_inovasi_view'))
        messages.error(request, 'Maaf data gagal disimpan!')
        return redirect(reverse('layanan_urls:layanan_inovasi_view'))


class LayananUsulanInovasiUpdateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def dispatch(self, request, *args, **kwargs):
        admin_cases = {'proses', 'sk', 'tl'}
        if request.GET.get('case') in admin_cases and not request.user.is_inovasi_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, id):
        try:
            queryset = LayananUsulanInovasi.objects.all()
            if not self.request.user.is_inovasi_admin:
                queryset = queryset.filter(pegawai=self.request.user)
            data = queryset.get(id=id)
            return data
        except LayananUsulanInovasi.DoesNotExist:
            return None
        
    def get_riwayat_object(self, id):
        try:
            data = RiwayatInovasi.objects.get(id=id)
            return data
        except RiwayatInovasi.DoesNotExist:
            return None
        
    def get(self, request, *args, **kwargs):
        get_case = request.GET.get('case')
        selected_nip = kwargs.get('nip')
        id = kwargs.get('id')
        nip = None
        id_riwayat = None
        card_title = 'Edit Usulan Inovasi'
        form_view = 'block'
        data_view = 'none'
        if request.user.is_inovasi_admin:
            nip = selected_nip
        else:
            nip = get_nip(request.user)  
        layanan_instance = self.get_object(id)
        if layanan_instance is not None:
            id_riwayat = layanan_instance.inovasi.id if hasattr(layanan_instance, 'inovasi') else None
        riwayat_instance = self.get_riwayat_object(id_riwayat)
        form = update_inovasi_formset(instance=riwayat_instance, form_kwargs={'request': request})
        riwayat_form = RiwayatInovasiForm(instance=riwayat_instance, request=request) 
        if get_case == 'sk':
            form = update_inovasi_formset(instance=riwayat_instance, form_kwargs={'request': request})
            riwayat_form = RiwayatInovasiSKForm(instance=riwayat_instance, request=request) 
            card_title = 'Tambah SK Inovasi'
            data_view = 'block'
            form_view = 'none'
        elif get_case == 'proses':
            form = proses_inovasi_formset(instance=riwayat_instance, form_kwargs={'request': request})
            riwayat_form = RiwayatInovasiTLForm(instance=riwayat_instance, request=request)
            card_title = 'Proses Verifikasi Usulan'
            data_view = 'block'
            form_view = 'none'
        elif get_case == 'tl':
            form = tindaklanjut_inovasi_formset(instance=riwayat_instance, form_kwargs={'request': request})
            riwayat_form = RiwayatInovasiTLForm(instance=riwayat_instance, request=request)
            card_title = 'Tindaklanjut Penilaian Usulan'
            data_view = 'block'
            form_view = 'none'
        elif get_case == 'detail':
            card_title = 'Detail Usulan Inovasi'
            data_view = 'block'
            form_view = 'none'
        elif request.user.is_inovasi_admin:
            form = full_update_inovasi_formset(instance=riwayat_instance)
            riwayat_form = RiwayatInovasiFullForm(instance=riwayat_instance, request=request)
        context={
            'update_form':True,
            'nip':nip,
            'riwayat_form': riwayat_form,
            'form':form,
            'data_detail':layanan_instance,
            'card_title':card_title,
            'form_view':form_view,
            'data_view':data_view,
            'case':get_case,
            'inovasi':'active',
            'layanan':'active',
            'title_page':'Layanan Inovasi',
            'selected':'yaninovasi'
        }
        return render(request, '8_layanan_inovasi/layanan_inovasi_master.html', context)
    
    def post(self, request, *args, **kwargs):
        get_case = request.GET.get('case')
        id = kwargs.get('id')
        riwayat_instance = None
        layanan_instance = self.get_object(id)
        id_riwayat = None
        if layanan_instance is not None:
            id_riwayat = layanan_instance.inovasi.id if hasattr(layanan_instance, 'inovasi') else None
        riwayat_existing = self.get_riwayat_object(id_riwayat)
        riwayat_instance = self.get_riwayat_object(id_riwayat)
        riwayat_form = RiwayatInovasiForm(data=request.POST, files=request.FILES, instance=riwayat_instance, request=request)
        form = update_inovasi_formset(data=request.POST, files=request.FILES, instance=riwayat_instance, form_kwargs={'request': request})
        if get_case == 'sk':
            riwayat_form = RiwayatInovasiSKForm(data=request.POST, files=request.FILES, instance=riwayat_instance, request=request) 
            form = update_inovasi_formset(data=request.POST, files=request.FILES, instance=riwayat_instance, form_kwargs={'request': request})
        elif get_case == 'proses':
            form = proses_inovasi_formset(data=request.POST, files=request.FILES, instance=riwayat_instance, form_kwargs={'request': request})
            riwayat_form = RiwayatInovasiTLForm(data=request.POST, files=request.FILES, instance=riwayat_instance, request=request)
        elif get_case == 'tl':
            form = tindaklanjut_inovasi_formset(data=request.POST, files=request.FILES, instance=riwayat_instance, form_kwargs={'request': request})
            riwayat_form = RiwayatInovasiTLForm(data=request.POST, files=request.FILES, instance=riwayat_instance, request=request)
        elif request.user.is_inovasi_admin:
            form = full_update_inovasi_formset(data=request.POST, files=request.FILES, instance=riwayat_instance)
            riwayat_form = RiwayatInovasiFullForm(data=request.POST, files=request.FILES, instance=riwayat_instance, request=request)
        if riwayat_form.is_valid() and form.is_valid():
            data_riwayat = riwayat_form.save(commit=False)
            if data_riwayat.makalah and riwayat_existing.makalah and riwayat_existing.makalah != data_riwayat.makalah and os.path.exists(riwayat_existing.makalah.path):
                os.remove(riwayat_existing.makalah.path)
            if data_riwayat.file_sk and riwayat_existing.file_sk and riwayat_existing.file_sk != data_riwayat.file_sk and os.path.exists(riwayat_existing.file_sk.path):
                os.remove(riwayat_existing.file_sk.path)
            data_riwayat.save()
            for item in form:
                if item.is_valid():
                    data_usulan = item.save(commit=False)
                    data_status = ['tindaklanjut', 'selesai']
                    if get_case == 'proses' and not any(data == layanan_instance.status for data in data_status):
                        data_usulan.status = form.cleaned_data[0].get('status')
                    elif get_case == 'tl' and layanan_instance.status != 'selesai':
                        data_usulan.status = 'tindaklanjut'
                    elif get_case == 'sk':
                        data_usulan.status = 'selesai'
                    data_usulan.inovasi = data_riwayat
                    data_usulan.save()
                messages.success(request, 'Data berhasil disimpan!') 
                return redirect(reverse('layanan_urls:layanan_inovasi_view'))
        messages.error(request, 'Maaf data gagal disimpan!')
        return redirect(reverse('layanan_urls:layanan_inovasi_view'))


from .models import LayananSIP
from .forms import LayananSIPForm, UploadRekomendasiSIPForm, UploadPersyaratanSIPForm


class LayananSIPListView(LoginRequiredMixin, ListView):
    model = LayananSIP
    template_name = "layanan_sip/list.html"
    context_object_name = "layanan_sip_list"
    paginate_by = 10

    def get_queryset(self):
        layanan_sip = LayananSIP.objects.filter(pegawai=self.request.user).select_related(
            "pegawai",
        ).order_by("-created_at")

        if self.request.user.is_sip_admin:
            layanan_sip = LayananSIP.objects.all().select_related(
                "pegawai",
            ).order_by("-created_at")

        return layanan_sip

    def get_context_data(self):
        context = super().get_context_data()
        context["card_title"] = "Data Permohonan SIP"
        context["title_page"] = "Layanan SIP"
        return context


class LayananSIPCreateView(LoginRequiredMixin, CreateView):
    model = LayananSIP
    form_class = LayananSIPForm
    template_name = "layanan_sip/form.html"
    success_url = reverse_lazy("layanan_urls:layanan_sip_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_sip_admin:
            form.instance.pegawai = self.request.user
        response = super().form_valid(form)

        messages.success(self.request, "Permohonan SIP berhasil diajukan.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["card_title"] = "Permohonan SIP"
        context["title_page"] = "Layanan SIP"
        return context


class LayananSIPDetailView(LoginRequiredMixin, DetailView):
    model = LayananSIP
    template_name = "layanan_sip/detail.html"
    context_object_name = "layanan_sip"

    def get_queryset(self):
        # 1. Ambil query dasar dengan select_related untuk menghemat query database (Bagus!)
        queryset = super().get_queryset().select_related(
            "pegawai",
            "layanan",
            "ijazah",
            "str_profesi",
        )

        # 2. Atur hak akses: Jika BUKAN superuser, kunci hanya untuk datanya sendiri
        if not self.request.user.is_sip_admin:
            queryset = queryset.filter(pegawai=self.request.user)

        # JIKA SUPERUSER, biarkan lolos tanpa filter agar bisa melihat detail SIP milik siapa saja
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["card_title"] = "Detail Permohonan SIP"
        context["title_page"] = "Layanan SIP"
        return context


class LayananSIPUpdateView(LoginRequiredMixin, UpdateView):
    model = LayananSIP
    form_class = LayananSIPForm
    template_name = "layanan_sip/form.html"
    success_url = reverse_lazy("layanan_urls:layanan_sip_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_queryset(self):
        qs = LayananSIP.objects.all()

        if self.request.user.is_sip_admin:
            return qs

        return qs.filter(pegawai=self.request.user)

    def form_valid(self, form):
        if not self.request.user.is_sip_admin:
            form.instance.pegawai = self.request.user

        return super().form_valid(form)


class LayananSIPUploadRekomendasiView(
    LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    model = LayananSIP
    form_class = UploadRekomendasiSIPForm
    template_name = "layanan_sip/upload_rekomendasi.html"

    def test_func(self):
        return (
            self.request.user.is_sip_admin
            or self.get_object().pegawai_id == self.request.user.pk
        )

    def handle_no_permission(self):
        messages.error(self.request, "Anda tidak memiliki akses untuk mengunggah dokumen SKP ini.")
        return redirect("layanan_urls:layanan_sip_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        replaced_files = []
        for field_name in form.fields:
            if field_name not in self.request.FILES:
                continue

            old_file = getattr(self.object, field_name, None)
            if old_file and old_file.name:
                replaced_files.append((field_name, old_file.storage, old_file.name))

        # Permohonan baru dinyatakan selesai setelah rekomendasi final tersedia.
        if (
            self.request.user.is_sip_admin
            and form.cleaned_data.get("surat_rekomendasi_sip")
        ):
            form.instance.status = "selesai"
            # Munculkan notifikasi baru kepada pegawai setelah rekomendasi selesai.
            form.instance.is_read = False

        with transaction.atomic():
            response = super().form_valid(form)

            # Hapus file lama hanya setelah data file baru berhasil disimpan ke DB.
            for field_name, storage, old_name in replaced_files:
                new_file = getattr(self.object, field_name)
                if old_name != new_file.name:
                    transaction.on_commit(
                        lambda storage=storage, name=old_name: storage.delete(name),
                        robust=True,
                    )

        if self.request.user.is_sip_admin and self.object.surat_rekomendasi_sip:
            message = "Dokumen berhasil diunggah dan status permohonan menjadi selesai."
        else:
            message = "Dokumen rekomendasi SIP berhasil diunggah."
        messages.success(self.request, message)
        return response

    def get_success_url(self):
        return reverse("layanan_urls:layanan_sip_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["card_title"] = "Upload/Ganti Dokumen Rekomendasi SIP"
        context["title_page"] = "Layanan SIP"
        context["is_admin_upload"] = self.request.user.is_sip_admin
        context["current_documents"] = [
            {
                "label": form_field.label,
                "file": getattr(self.object, field_name, None),
            }
            for field_name, form_field in context["form"].fields.items()
        ]
        return context


class PerubahanJadwalCutiCreateView(LoginRequiredMixin, CheckCuti, CreateView):
    model = PerubahanJadwalCuti
    form_class = PerubahanJadwalCutiForm
    template_name = '6_layanan_cuti/perubahan_jadwal_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        self.riwayat = get_object_or_404(
            RiwayatCuti.objects.select_related('pegawai', 'usulan'),
            pk=kwargs['riwayat_pk'],
        )
        if self.riwayat.pegawai_id != request.user.pk:
            raise PermissionDenied('Hanya pemohon yang dapat mengajukan perubahan jadwal.')
        if self.riwayat.usulan.status == 'ditolak':
            messages.error(request, 'Pengajuan yang ditolak harus dibuat sebagai pengajuan baru.')
            return redirect('layanan_urls:layanan_cuti_detail', pk=self.riwayat.usulan_id)
        if self.riwayat.status_cuti in ('Tunda', 'Batal'):
            messages.error(request, 'Jadwal cuti tunda atau cuti yang ditolak tidak dapat diubah.')
            return redirect('layanan_urls:layanan_cuti_detail', pk=self.riwayat.usulan_id)
        if not self.riwayat.tgl_mulai_cuti or not self.riwayat.tgl_akhir_cuti or not self.riwayat.lama_cuti:
            messages.error(request, 'Tanggal atau durasi cuti lama belum lengkap.')
            return redirect('layanan_urls:layanan_cuti_detail', pk=self.riwayat.usulan_id)
        if self.riwayat.perubahan_jadwal.filter(
            status__in=('menunggu_verifikasi', 'menunggu_pelimpahan')
        ).exists():
            messages.error(request, 'Masih ada perubahan jadwal yang sedang diproses.')
            return redirect('layanan_urls:layanan_cuti_detail', pk=self.riwayat.usulan_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['riwayat_cuti'] = self.riwayat
        kwargs['check_cuti'] = self
        return kwargs

    def get_initial(self):
        return {
            'tanggal_mulai_baru': self.riwayat.tgl_mulai_cuti,
            'tanggal_akhir_baru': self.riwayat.tgl_akhir_cuti,
        }

    @transaction.atomic
    def form_valid(self, form):
        Users.objects.select_for_update().get(pk=self.riwayat.pegawai_id)
        self.riwayat = RiwayatCuti.objects.select_for_update().select_related(
            'pegawai', 'usulan'
        ).get(pk=self.riwayat.pk)
        if self.riwayat.perubahan_jadwal.filter(
            status__in=('menunggu_verifikasi', 'menunggu_pelimpahan')
        ).exists():
            form.add_error(None, 'Perubahan jadwal lain sedang diproses.')
            return self.form_invalid(form)

        perubahan = form.save(commit=False)
        perubahan.riwayat_cuti = self.riwayat
        perubahan.diajukan_oleh = self.request.user
        perubahan.jenis_perubahan = determine_change_type(self.riwayat)
        perubahan.tanggal_mulai_lama = self.riwayat.tgl_mulai_cuti
        perubahan.tanggal_akhir_lama = self.riwayat.tgl_akhir_cuti
        perubahan.lama_cuti_lama = self.riwayat.lama_cuti
        perubahan.lama_cuti_baru = (
            perubahan.tanggal_akhir_baru - perubahan.tanggal_mulai_baru
        ).days + 1

        verifikasi = VerifikasiCuti.objects.filter(layanan_cuti=self.riwayat.usulan).first()
        perubahan.snapshot_verifikasi = snapshot_verification(verifikasi)

        if perubahan.jenis_perubahan == 'perubahan_final':
            chain = build_approval_chain(self.riwayat.pegawai)
            if not chain or any(item['user'] is None for item in chain):
                form.add_error(None, 'Rantai verifikator belum lengkap. Hubungi admin struktur organisasi.')
                return self.form_invalid(form)
            for item in chain:
                setattr(perubahan, f"verifikator{item['level']}", item['user'])
            perubahan.status = 'menunggu_verifikasi'
            perubahan.full_clean()
            perubahan.save()
            messages.success(
                self.request,
                'Permohonan perubahan jadwal dikirim. Jadwal lama tetap berlaku sampai perubahan disetujui.',
            )
        else:
            perubahan.status = 'diterapkan'
            perubahan.full_clean()
            perubahan.save()
            try:
                apply_nonfinal_change(perubahan.pk)
            except ValidationError as exc:
                perubahan.delete()
                form.add_error(None, exc)
                return self.form_invalid(form)
            if perubahan.jenis_perubahan == 'revisi_proses':
                message = 'Jadwal diperbarui dan verifikasi dimulai kembali dari level pertama.'
            else:
                message = 'Jadwal cuti berhasil diperbarui sebelum verifikasi.'
            messages.success(self.request, message)

        self.object = perubahan
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('layanan_urls:layanan_cuti_detail', kwargs={'pk': self.riwayat.usulan_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'riwayat': self.riwayat,
            'jenis_perubahan': determine_change_type(self.riwayat),
            'title_page': 'Perubahan Jadwal Cuti',
            'cuti': 'active',
            'layanan': 'active',
        })
        return context


class PerubahanJadwalCutiCancelView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        perubahan = get_object_or_404(
            PerubahanJadwalCuti.objects.select_related('riwayat_cuti__usulan'),
            pk=kwargs['pk'],
        )
        if perubahan.diajukan_oleh_id != request.user.pk:
            raise PermissionDenied('Hanya pemohon yang dapat membatalkan perubahan jadwal.')
        try:
            cancel_schedule_change(perubahan.pk)
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages))
        else:
            messages.success(request, 'Permohonan perubahan jadwal dibatalkan.')
        return redirect(
            'layanan_urls:layanan_cuti_detail',
            pk=perubahan.riwayat_cuti.usulan_id,
        )


class PerubahanJadwalCutiVerifikasiView(LoginRequiredMixin, FormView):
    form_class = PerubahanJadwalDecisionForm
    template_name = '6_layanan_cuti/perubahan_jadwal_verifikasi.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        self.perubahan = get_object_or_404(
            PerubahanJadwalCuti.objects.select_related(
                'riwayat_cuti__pegawai', 'riwayat_cuti__usulan',
                'verifikator1', 'verifikator2', 'verifikator3',
            ),
            pk=kwargs['pk'],
        )
        if self.perubahan.status != 'menunggu_verifikasi':
            messages.info(request, 'Permohonan perubahan jadwal ini sudah tidak menunggu verifikasi.')
            return redirect('layanan_urls:layanan_cuti_detail', pk=self.perubahan.riwayat_cuti.usulan_id)
        self.current_level = self._get_current_level(request.user)
        if request.user.is_cuti_admin:
            self.current_level = None
        elif self.current_level is None:
            raise PermissionDenied('Anda bukan verifikator perubahan jadwal ini.')
        return super().dispatch(request, *args, **kwargs)

    def _get_current_level(self, user):
        for level in (1, 2, 3):
            if (
                getattr(self.perubahan, f'verifikator{level}_id') == user.pk
                and getattr(self.perubahan, f'keputusan{level}') == 'belum'
            ):
                return level
        return None

    def post(self, request, *args, **kwargs):
        if request.user.is_cuti_admin:
            messages.info(request, 'Admin cuti berada dalam mode monitoring.')
            return redirect(request.path)
        previous = [
            level for level in (1, 2, 3)
            if getattr(self.perubahan, f'verifikator{level}_id') and level < self.current_level
        ]
        if any(getattr(self.perubahan, f'keputusan{level}') != 'setuju' for level in previous):
            messages.error(request, 'Verifikator sebelumnya belum menyetujui perubahan jadwal.')
            return redirect(request.path)
        return super().post(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        perubahan = PerubahanJadwalCuti.objects.select_for_update().get(pk=self.perubahan.pk)
        if perubahan.status != 'menunggu_verifikasi':
            messages.error(self.request, 'Status perubahan sudah berubah.')
            return redirect(self.request.path)

        level = self.current_level
        keputusan = form.cleaned_data['keputusan']
        setattr(perubahan, f'keputusan{level}', keputusan)
        setattr(perubahan, f'catatan{level}', form.cleaned_data.get('catatan', ''))
        setattr(perubahan, f'diputuskan_pada{level}', timezone.now())
        perubahan.save()

        if keputusan == 'tolak':
            perubahan.status = 'ditolak'
            perubahan.save(update_fields=('status', 'updated_at'))
            messages.error(self.request, 'Permohonan perubahan jadwal ditolak.')
        else:
            active_levels = [
                level for level in (1, 2, 3)
                if getattr(perubahan, f'verifikator{level}_id')
            ]
            if all(getattr(perubahan, f'keputusan{item}') == 'setuju' for item in active_levels):
                try:
                    approve_final_change(perubahan.pk)
                except ValidationError as exc:
                    form.add_error(None, exc)
                    transaction.set_rollback(True)
                    return self.form_invalid(form)
                messages.success(
                    self.request,
                    'Perubahan jadwal disetujui. Menunggu persetujuan ulang pelimpahan jika diperlukan.',
                )
            else:
                messages.success(self.request, 'Keputusan perubahan jadwal berhasil disimpan.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('layanan_urls:layanan_cuti_detail', kwargs={
            'pk': self.perubahan.riwayat_cuti.usulan_id,
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chain = []
        for level in (1, 2, 3):
            user = getattr(self.perubahan, f'verifikator{level}')
            if user:
                chain.append({
                    'level': level,
                    'user': user,
                    'keputusan': getattr(self.perubahan, f'keputusan{level}'),
                    'catatan': getattr(self.perubahan, f'catatan{level}'),
                })
        context.update({
            'perubahan': self.perubahan,
            'chain': chain,
            'current_level': self.current_level,
            'is_monitor': self.request.user.is_cuti_admin,
            'title_page': 'Verifikasi Perubahan Jadwal Cuti',
            'cuti': 'active',
            'layanan': 'active',
        })
        return context


class LayananSIPUploadPersyaratanView(LoginRequiredMixin, FormView):
    form_class = UploadPersyaratanSIPForm
    template_name = "layanan_sip/upload_persyaratan.html"

    def dispatch(self, request, *args, **kwargs):
        self.layanan_sip = get_object_or_404(
            LayananSIP.objects.select_related("pegawai", "ijazah"),
            pk=kwargs["pk"],
            pegawai=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["layanan_sip"] = self.layanan_sip
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            form.save()
        messages.success(self.request, "Dokumen persyaratan SIP berhasil diunggah.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "layanan_urls:layanan_sip_detail",
            kwargs={"pk": self.layanan_sip.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["layanan_sip"] = self.layanan_sip
        context["card_title"] = "Upload Persyaratan SIP"
        context["title_page"] = "Layanan SIP"
        return context


class LayananNaikPangkatListView(LoginRequiredMixin, ListView):
    model = LayananNaikPangkat
    template_name = 'layanan_pangkat/list.html'
    context_object_name = 'usulan_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            LayananNaikPangkat.objects
            .select_related('pegawai', 'layanan', 'sk_kp_terakhir', 'pendidikan')
            .prefetch_related('kinerja_dua_thn', 'pak')
            .order_by('-created_at')
        )
        if self.request.user.is_pangkat_admin:
            return queryset
        return queryset.filter(pegawai=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Usulan Kenaikan Pangkat',
            'title_page': 'Layanan Kenaikan Pangkat',
            'layanan': 'active',
            'selected': 'yanpangkat',
        })
        return context


class LayananNaikPangkatCreateView(LoginRequiredMixin, CreateView):
    model = LayananNaikPangkat
    form_class = LayananNaikPangkatForm
    template_name = 'layanan_pangkat/form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        layanan = JenisLayanan.objects.filter(url='yanpangkat', status=True).first()
        if not layanan:
            form.add_error(None, 'Jenis layanan kenaikan pangkat belum dikonfigurasi.')
            return self.form_invalid(form)

        form.instance.pegawai = self.request.user
        form.instance.layanan = layanan
        form.instance.status = 'pengajuan'
        form.instance.is_read = False
        response = super().form_valid(form)
        messages.success(self.request, 'Usulan kenaikan pangkat berhasil dikirim.')
        return response

    def get_success_url(self):
        return reverse('layanan_urls:layanan_pangkat_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Ajukan Kenaikan Pangkat',
            'title_page': 'Layanan Kenaikan Pangkat',
            'layanan': 'active',
            'selected': 'yanpangkat',
        })
        return context


class LayananNaikPangkatUpdateView(LoginRequiredMixin, UpdateView):
    model = LayananNaikPangkat
    form_class = LayananNaikPangkatForm
    template_name = 'layanan_pangkat/form.html'

    def get_queryset(self):
        return LayananNaikPangkat.objects.filter(
            pegawai=self.request.user,
            status='pengajuan',
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.pegawai = self.request.user
        form.instance.is_read = False
        messages.success(self.request, 'Usulan kenaikan pangkat berhasil diperbarui.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('layanan_urls:layanan_pangkat_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Ubah Usulan Kenaikan Pangkat',
            'title_page': 'Layanan Kenaikan Pangkat',
            'layanan': 'active',
            'selected': 'yanpangkat',
        })
        return context


class LayananNaikPangkatDetailView(LoginRequiredMixin, DetailView):
    model = LayananNaikPangkat
    template_name = 'layanan_pangkat/detail.html'
    context_object_name = 'usulan'

    def get_queryset(self):
        queryset = (
            LayananNaikPangkat.objects
            .select_related(
                'pegawai', 'layanan', 'sk_kp_terakhir', 'sk_jabfung',
                'pendidikan', 'pengangkatan', 'mutasi',
            )
            .prefetch_related('kinerja_dua_thn', 'pak', 'riwayatpanggol_set')
        )
        if self.request.user.is_pangkat_admin:
            return queryset
        return queryset.filter(pegawai=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'hasil_pangkat': self.object.riwayatpanggol_set.order_by('-id').first(),
            'card_title': 'Detail Usulan Kenaikan Pangkat',
            'title_page': 'Layanan Kenaikan Pangkat',
            'layanan': 'active',
            'selected': 'yanpangkat',
        })
        return context


class LayananNaikPangkatProcessView(
    LoginRequiredMixin, UserPassesTestMixin, FormView
):
    form_class = RiwayatPanggolHasilLayananForm
    template_name = 'layanan_pangkat/process.html'

    def dispatch(self, request, *args, **kwargs):
        self.usulan = get_object_or_404(
            LayananNaikPangkat.objects.select_related('pegawai', 'layanan'),
            pk=kwargs['pk'],
        )
        self.hasil = self.usulan.riwayatpanggol_set.order_by('-id').first()
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        return self.request.user.is_pangkat_admin

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.hasil
        return kwargs

    def form_valid(self, form):
        dokumen = DokumenSDM.objects.filter(
            Q(url='panggol') | Q(url='pangkat')
        ).first()
        if not dokumen:
            form.add_error(None, 'Jenis dokumen riwayat pangkat belum dikonfigurasi.')
            return self.form_invalid(form)

        old_file = None
        if self.hasil and self.hasil.file and 'file' in self.request.FILES:
            old_file = (self.hasil.file.storage, self.hasil.file.name)

        with transaction.atomic():
            hasil = form.save(commit=False)
            hasil.pegawai = self.usulan.pegawai
            hasil.dokumen = dokumen
            hasil.usulan = self.usulan
            hasil.save()

            self.usulan.status = 'selesai'
            self.usulan.is_read = False
            self.usulan.save(update_fields=['status', 'is_read', 'updated_at'])

            if old_file and old_file[1] != hasil.file.name:
                transaction.on_commit(
                    lambda storage=old_file[0], name=old_file[1]: storage.delete(name),
                    robust=True,
                )

        messages.success(
            self.request,
            'Hasil kenaikan pangkat berhasil disimpan ke Riwayat Pangkat/Golongan.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'layanan_urls:layanan_pangkat_detail',
            kwargs={'pk': self.usulan.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'usulan': self.usulan,
            'hasil_pangkat': self.hasil,
            'card_title': 'Proses Kenaikan Pangkat',
            'title_page': 'Layanan Kenaikan Pangkat',
            'layanan': 'active',
            'selected': 'yanpangkat',
        })
        return context


class LayananNaikJabatanListView(LoginRequiredMixin, ListView):
    model = LayananNaikJabatan
    template_name = 'layanan_jabatan/list.html'
    context_object_name = 'usulan_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            LayananNaikJabatan.objects
            .select_related('pegawai', 'layanan', 'kompetensi', 'pendidikan', 'pak')
            .prefetch_related('kinerja_dua_thn')
            .order_by('-created_at')
        )
        if self.request.user.is_jabatan_admin:
            return queryset
        return queryset.filter(pegawai=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Usulan Kenaikan Jabatan',
            'title_page': 'Layanan Kenaikan Jabatan',
            'layanan': 'active',
            'selected': 'yanjabatan',
        })
        return context


class SuratUsulanJabatanView(
    LoginRequiredMixin, UserPassesTestMixin, FormView
):
    form_class = SuratUsulanJabatanForm
    template_name = 'layanan_jabatan/surat_form.html'

    def test_func(self):
        return self.request.user.is_jabatan_admin

    def form_valid(self, form):
        periode = datetime.strptime(
            form.cleaned_data['periode'], '%Y-%m-%d'
        ).date()
        usulan = (
            LayananNaikJabatan.objects.filter(periode=periode)
            .select_related(
                'pegawai', 'pegawai__profil_user', 'pak', 'kompetensi',
            )
            .prefetch_related('kinerja_dua_thn')
            .order_by('pegawai__first_name', 'pegawai__last_name', 'id')
        )
        if not usulan.exists():
            form.add_error('periode', 'Tidak ada pengajuan pada periode tersebut.')
            return self.form_invalid(form)

        output = generate_usulan_jabatan_docx(
            usulan,
            periode=periode,
        )
        response = HttpResponse(
            output.getvalue(),
            content_type=(
                'application/vnd.openxmlformats-officedocument.'
                'wordprocessingml.document'
            ),
        )
        response['Content-Disposition'] = (
            f'attachment; filename="Usulan_Jabatan_{periode:%Y_%m}.docx"'
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Generate Surat Usulan Kenaikan Jabatan',
            'title_page': 'Surat Usulan Kenaikan Jabatan',
            'layanan': 'active',
            'selected': 'yanjabatan',
        })
        return context


class LayananNaikJabatanCreateView(LoginRequiredMixin, CreateView):
    model = LayananNaikJabatan
    form_class = LayananNaikJabatanForm
    template_name = 'layanan_jabatan/form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        layanan = JenisLayanan.objects.filter(url='yanjabatan', status=True).first()
        if not layanan:
            form.add_error(None, 'Jenis layanan kenaikan jabatan belum dikonfigurasi.')
            return self.form_invalid(form)

        form.instance.pegawai = self.request.user
        form.instance.layanan = layanan
        form.instance.status = 'pengajuan'
        form.instance.is_read = False
        response = super().form_valid(form)
        messages.success(self.request, 'Usulan kenaikan jabatan berhasil dikirim.')
        return response

    def get_success_url(self):
        return reverse('layanan_urls:layanan_jabatan_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Ajukan Kenaikan Jabatan',
            'title_page': 'Layanan Kenaikan Jabatan',
            'layanan': 'active',
            'selected': 'yanjabatan',
        })
        return context


class LayananNaikJabatanUpdateView(LoginRequiredMixin, UpdateView):
    model = LayananNaikJabatan
    form_class = LayananNaikJabatanForm
    template_name = 'layanan_jabatan/form.html'

    def get_queryset(self):
        return LayananNaikJabatan.objects.filter(
            pegawai=self.request.user,
            status='pengajuan',
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.pegawai = self.request.user
        form.instance.is_read = False
        messages.success(self.request, 'Usulan kenaikan jabatan berhasil diperbarui.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('layanan_urls:layanan_jabatan_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Ubah Usulan Kenaikan Jabatan',
            'title_page': 'Layanan Kenaikan Jabatan',
            'layanan': 'active',
            'selected': 'yanjabatan',
        })
        return context


class LayananNaikJabatanDetailView(LoginRequiredMixin, DetailView):
    model = LayananNaikJabatan
    template_name = 'layanan_jabatan/detail.html'
    context_object_name = 'usulan'

    def get_queryset(self):
        queryset = (
            LayananNaikJabatan.objects
            .select_related(
                'pegawai', 'layanan', 'kompetensi', 'pendidikan',
                'str_profesi', 'pak',
            )
            .prefetch_related('kinerja_dua_thn', 'riwayatjabatan_set')
        )
        if self.request.user.is_jabatan_admin:
            return queryset
        return queryset.filter(pegawai=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'hasil_jabatan': self.object.riwayatjabatan_set.order_by('-id').first(),
            'card_title': 'Detail Usulan Kenaikan Jabatan',
            'title_page': 'Layanan Kenaikan Jabatan',
            'layanan': 'active',
            'selected': 'yanjabatan',
        })
        return context


class LayananNaikJabatanProcessView(
    LoginRequiredMixin, UserPassesTestMixin, FormView
):
    form_class = RiwayatJabatanHasilLayananForm
    template_name = 'layanan_jabatan/process.html'

    def dispatch(self, request, *args, **kwargs):
        self.usulan = get_object_or_404(
            LayananNaikJabatan.objects.select_related('pegawai', 'layanan'),
            pk=kwargs['pk'],
        )
        self.hasil = self.usulan.riwayatjabatan_set.order_by('-id').first()
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        return self.request.user.is_jabatan_admin

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.hasil
        return kwargs

    def form_valid(self, form):
        dokumen = DokumenSDM.objects.filter(url='jabatan').first()
        if not dokumen:
            form.add_error(None, 'Jenis dokumen riwayat jabatan belum dikonfigurasi.')
            return self.form_invalid(form)

        old_file = None
        if self.hasil and self.hasil.file and 'file' in self.request.FILES:
            old_file = (self.hasil.file.storage, self.hasil.file.name)

        with transaction.atomic():
            hasil = form.save(commit=False)
            hasil.pegawai = self.usulan.pegawai
            hasil.dokumen = dokumen
            hasil.usulan = self.usulan
            hasil.save()
            form.save_m2m()

            self.usulan.status = 'selesai'
            self.usulan.is_read = False
            self.usulan.save(update_fields=['status', 'is_read', 'updated_at'])

            if old_file and old_file[1] != hasil.file.name:
                transaction.on_commit(
                    lambda storage=old_file[0], name=old_file[1]: storage.delete(name),
                    robust=True,
                )

        messages.success(
            self.request,
            'Hasil kenaikan jabatan berhasil disimpan ke Riwayat Jabatan.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'layanan_urls:layanan_jabatan_detail',
            kwargs={'pk': self.usulan.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'usulan': self.usulan,
            'hasil_jabatan': self.hasil,
            'card_title': 'Proses Kenaikan Jabatan',
            'title_page': 'Layanan Kenaikan Jabatan',
            'layanan': 'active',
            'selected': 'yanjabatan',
        })
        return context
