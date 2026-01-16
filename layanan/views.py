from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView, CreateView, DetailView, FormView
from django.db import transaction
# from django.views.generic import ListView, CreateView
from django.db.models import Sum, F, Q, Window
from django.db.models.functions import RowNumber
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from datetime import datetime, date, timedelta
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from typing import Optional
from django.core.exceptions import PermissionDenied
import os
import locale
import logging 
from .services import CheckCuti
from .utils import resolve_atasan_level3_for_level4

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
    RiwayatPengajuanCutiForm,
    RiwayatCutiUploadSuratForm,
    RiwayatCutiUploadDakungForm,
    RiwayatCutiForm,
    RiwayatCutiTundaForm,
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
    VerifikatorCutiForm,
    Verifikator1CutiForm,
    Verifikator2CutiForm,
    Verifikator3CutiForm, 
    FormLayananBerkala, 
    pengajuan_cuti_formset,
    update_pengajuan_cuti_formset,
    update_pengajuan_cuti_fullform_formset,
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
        
class NotifikasiView(View):
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
            
    def get(self, request, *args, **kwargs):
        get_layanan = request.GET.get('layanan')
        context={
            'data':get_layanan
        }
        return render(request, 'layanan_view_from_notif.html', context)
    
    def post(self, request, *args, **kwargs):
        id_layanan = kwargs.get('id')
        get_layanan = request.GET.get('layanan')
        get_case = request.GET.get('case')
        if get_layanan == 'yancuti':
            url = reverse('layanan_urls:layanan_cuti_update_view', kwargs={'status':'riwayat', 'id':id_layanan})
            data = self.get_cuti_object(id_layanan)
            data.is_read = True
            data.save()
            return redirect(f'{url}?case={get_case}')
        elif get_layanan == 'yanberkala':
            url = reverse('layanan_urls:layanan_berkala_update_view', kwargs={'id':id_layanan})
            data = self.get_berkala_object(id_layanan)
            data.is_read = True
            data.save()
            return redirect(f'{url}?case={get_case}')
        if get_layanan == 'yandiklat':
            url = reverse('layanan_urls:layanan_diklat_update_view', kwargs={'id':id_layanan})
            data = self.get_diklat_object(id_layanan)
            data.is_read = True
            data.save()
            return redirect(f'{url}?case={get_case}')
        if get_layanan == 'yaninovasi':
            url = reverse('layanan_urls:layanan_inovasi_update_view', kwargs={'id':id_layanan})
            data = self.get_inovasi_object(id_layanan)
            data.is_read = True
            data.save()
            return redirect(f'{url}?case={get_case}')


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
        if not self.request.user.is_superuser:
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
        return self.request.user.is_staff
    
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
            .order_by('-updated_at')
        )

        if user.is_superuser:
            return base_qs

        profil_admin = getattr(user, 'profil_admin', None)
        if not profil_admin:
            # bukan atasan / tidak punya scope → tidak ada bawahan
            return RiwayatCuti.objects.none()

        # hanya pegawai dengan penempatan aktif
        qs = base_qs.filter(
            pegawai__riwayat_penempatan__status=True
        ).exclude(pegawai=user)

        p = profil_admin

        if p.instalasi.exists():
            # atasan unit instalasi → bawahan: semua pegawai di instalasi tsb
            qs = qs.filter(
                pegawai__riwayat_penempatan__penempatan_level4__in=p.instalasi.all()
            )

        elif p.sub_bidang:
            # atasan sub_bidang → semua yg langsung di sub_bidang + instalasi di bawahnya
            qs = qs.filter(
                Q(pegawai__riwayat_penempatan__penempatan_level3=p.sub_bidang) |
                Q(pegawai__riwayat_penempatan__penempatan_level4__sub_bidang=p.sub_bidang)
            )

        elif p.bidang:
            # atasan bidang → semua level di bawah bidang tsb
            qs = qs.filter(
                Q(pegawai__riwayat_penempatan__penempatan_level2=p.bidang) |
                Q(pegawai__riwayat_penempatan__penempatan_level3__bidang=p.bidang) |
                Q(pegawai__riwayat_penempatan__penempatan_level4__sub_bidang__bidang=p.bidang)
            )

        elif p.unor:
            # atasan unor (level 1) → semua pegawai di unit tsb
            qs = qs.filter(
                Q(pegawai__riwayat_penempatan__penempatan_level1=p.unor) |
                Q(pegawai__riwayat_penempatan__penempatan_level2__unor=p.unor) |
                Q(pegawai__riwayat_penempatan__penempatan_level3__bidang__unor=p.unor) |
                Q(pegawai__riwayat_penempatan__penempatan_level4__sub_bidang__bidang__unor=p.unor)
            )
        else:
            return RiwayatCuti.objects.none()

        return qs.distinct()

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

    login_url = '/accounts/login/'
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
        if self.request.user.is_superuser:
            return None
        profil = getattr(self.request.user, 'profil_user', None)
        return getattr(profil, 'nip', None)

    # ---------- form utama ----------
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['action'] = 'add'
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        layanan_default = self.get_layanan_default()

        if not user.is_superuser:
            initial['pegawai'] = user
        initial['layanan'] = layanan_default
        initial['status'] = 'pengajuan'
        initial['tahun'] = date.today().year
        return initial

    # ---------- formset ----------
    def get_formset(self, tahun_pengajuan=None):
        dokumen_default = self.get_dokumen_default()
        user = self.request.user

        if tahun_pengajuan is None:
            tahun_pengajuan = date.today().year

        if self.request.method == 'POST':
            formset = pengajuan_cuti_formset(
                data=self.request.POST,
                files=self.request.FILES,
                form_kwargs={
                    'request': self.request,
                    'action': 'add',
                    'status': 'baru',
                    'tahun_pengajuan': tahun_pengajuan,
                    'check_cuti': self,
                },
            )
        else:
            initial_riwayat = {'dokumen': dokumen_default}
            if not user.is_superuser:
                initial_riwayat['pegawai'] = user

            formset = pengajuan_cuti_formset(
                initial=[initial_riwayat],
                form_kwargs={
                    'request': self.request,
                    'action': 'add',
                    'status': 'baru',
                    'tahun_pengajuan': tahun_pengajuan,
                    'check_cuti': self,
                },
            )
        return formset

    # ---------- context ----------
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        self.set_allow_cuti_tunda()

        if 'formset' not in context:
            context['formset'] = self.get_formset()

        context.update({
            'nip': self.get_nip_user(),
            'cek_sisa_cuti': self.cek_sisa_cuti(self.request.user),
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
            formset = self.get_formset(tahun_pengajuan=tahun_pengajuan)
            if formset.is_valid():
                return self.forms_valid(form, formset, tahun_pengajuan)
            else:
                return self.forms_invalid(form, formset)
        else:
            formset = self.get_formset(tahun_pengajuan=tahun_pengajuan)
            return self.forms_invalid(form, formset)

    def get_status_pegawai(self, pegawai):
        try:
            pengangkatan = RiwayatPengangkatan.objects.filter(pegawai=pegawai).order_by('-id').first()
            return pengangkatan.status_pegawai
        except RiwayatPengangkatan.DoesNotExist:
            return None
    
    def forms_valid(self, form, formset, tahun_pengajuan: int):
        request = self.request

        with transaction.atomic():
            # ============================================================
            # 1) Simpan LayananCuti
            # ============================================================
            self.object = form.save(commit=False)
            if not request.user.is_superuser:
                self.object.pegawai = request.user
            if not self.object.status:
                self.object.status = "pengajuan"
            if not self.object.tahun:
                self.object.tahun = tahun_pengajuan
            self.object.save()

            # ============================================================
            # 2) Proses formset (RiwayatCuti)
            # ============================================================
            data_form = formset.save(commit=False)
            if not data_form:
                messages.error(request, "Data detail cuti tidak boleh kosong.")
                transaction.set_rollback(True)
                return redirect(self.success_url)

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

            target_pegawai = getattr(data_form[0], "pegawai", None) or self.object.pegawai
            sisa_cuti = self.cek_sisa_cuti(target_pegawai)

            # ============================================================
            # 3) Guard: penerima pelimpahan aktif tidak boleh ajukan cuti tahunan
            # ============================================================
            if jenis_cuti == "Cuti Tahunan" and tgl_mulai_cuti and tgl_akhir_cuti:
                if self.is_penerima_memiliki_pelimpahan_aktif(target_pegawai, tgl_mulai_cuti, tgl_akhir_cuti):
                    messages.error(
                        request,
                        "Anda tidak dapat mengajukan Cuti Tahunan karena sedang menerima "
                        "pelimpahan tugas pada rentang tanggal tersebut."
                    )
                    transaction.set_rollback(True)
                    return redirect(self.success_url)

            # ============================================================
            # 4) Isi field umum tiap RiwayatCuti
            # ============================================================
            for item in data_form:
                if not item.pegawai_id:
                    item.pegawai = self.object.pegawai
                if not item.tahun_cuti:
                    item.tahun_cuti = self.object.tahun or tahun_pengajuan
                item.usulan = self.object

            # ============================================================
            # 5) CABANG: CUTI TAHUNAN
            # ============================================================
            if jenis_cuti == "Cuti Tahunan":
                # waktu pengajuan tetap divalidasi utk cuti tahunan (mau tunda saja / normal)
                status_pegawai = self.get_status_pegawai(target_pegawai) if self.get_status_pegawai(target_pegawai) else "PNS"
                if not self.cek_waktu_pengajuan_cuti(tgl_mulai_cuti, status_pegawai):
                    messages.error(request, "Mohon maaf waktu pengajuan cuti anda terlalu mepet atau tidak sesuai!")
                    transaction.set_rollback(True)
                    return redirect(self.success_url)

                # if lama_cuti <= 0: user boleh buat cuti dengan lama cuti 0 nanti akan divalidasi di saat verifikasi pimpinan
                #     messages.error(request, "Lama cuti wajib diisi dan harus lebih dari 0.")
                #     return redirect(self.success_url)

                # ---- Mode A: pakai cuti tunda SAJA (tidak ganggu jatah tahun ini) ----
                if pakai_tunda_saja:
                    if not cuti_tunda_dipilih:
                        messages.error(request, "Anda memilih 'pakai cuti tunda saja' tetapi belum memilih sumber cuti tunda.")
                        transaction.set_rollback(True)
                        return redirect(self.success_url)

                    eligible = self.get_cuti_tunda_eligible(target_pegawai, tahun_pengajuan)
                    valid_tunda = eligible.filter(
                        id__in=cuti_tunda_dipilih.values_list("id", flat=True)
                    )

                    # total sisa tunda yang tersedia dari pilihan user
                    total_sisa_valid = sum((s.sisa_hari_tunda or 0) for s in valid_tunda)
                    if total_sisa_valid < lama_cuti:
                        messages.error(
                            request,
                            f"Sisa cuti tunda yang dipilih tidak mencukupi. "
                            f"Total sisa tunda: {total_sisa_valid} hari, kebutuhan: {lama_cuti} hari."
                        )
                        transaction.set_rollback(True)
                        return redirect(self.success_url)

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
                # validasi jatah tahun ini
                if sisa_cuti < lama_cuti:
                    messages.error(request, "Maaf jatah cuti tahunan anda kurang atau habis!")
                    return redirect(self.success_url)

                cuti_baru_main = None
                for idx, item in enumerate(data_form):
                    setattr(item, "pakai_tunda_saja", False)
                    item.save()
                    if idx == 0:
                        cuti_baru_main = item

                # Klaim tunda (opsional) untuk menutup sebagian dari lama_cuti
                if cuti_tunda_dipilih and cuti_baru_main:
                    eligible = self.get_cuti_tunda_eligible(target_pegawai, tahun_pengajuan)
                    valid_tunda = eligible.filter(
                        id__in=cuti_tunda_dipilih.values_list("id", flat=True)
                    )

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
            elif jenis_cuti in ["Cuti Alasan Penting", "Cuti melahirkan", "Cuti Sakit"]:
                for item in data_form:
                    item.save()
                messages.success(request, "Pengajuan cuti anda sukses, dan segera akan ditindaklanjuti oleh bagian SDM.")
                return redirect(self.success_url)

            # ============================================================
            # 7) DEFAULT
            # ============================================================
            messages.error(request, "Mohon maaf waktu pengajuan cuti anda terlalu mepet atau tidak sesuai!")
            return redirect(self.success_url)

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
        # Sesuaikan dengan permission Anda
        return self.request.user.is_superuser or getattr(self.request.user, "is_staff", False)

    def dispatch(self, request, *args, **kwargs):
        self.cuti_klaim = get_object_or_404(RiwayatCuti, pk=kwargs["riwayat_id"])

        # Guard: harus Cuti Tahunan tahun berjalan yang valid
        if self.cuti_klaim.jenis_cuti != "Cuti Tahunan":
            messages.error(request, "Override hanya untuk cuti tahunan.")
            return redirect(self.get_back_url())

        if self.cuti_klaim.status_cuti not in ["Proses", "Selesai"]:
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
            klaim = form.save(commit=False)
            klaim.is_admin_override = True
            klaim.admin_override_by = self.request.user
            klaim.admin_override_at = timezone.now()
            klaim.catatan_admin = form.cleaned_data.get("catatan_admin", "")
            klaim.save()

            riwayat = klaim.cuti_klaim
            riwayat.lama_cuti = int(riwayat.lama_cuti or 0) + int(klaim.jumlah_hari_diklaim or 0)
            riwayat.save(update_fields=["lama_cuti"])
            
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

        # opsional: pastikan hanya pemilik cuti yang boleh buat pelimpahan
        if request.user.is_superuser and hasattr(self.riwayat_cuti, 'pelimpahan_tugas'):
            return redirect('layanan_urls:pelimpahan_detail', pk=self.riwayat_cuti.pelimpahan_tugas.pk)
        if request.user.is_superuser:
            messages.info(request, 'Pemohon belum membuat pelimpahan tugas.')
            return redirect('layanan_urls:layanan_cuti_listview')

        if self.riwayat_cuti.pegawai != request.user:
            messages.error(request, "Anda tidak berhak membuat pelimpahan untuk cuti ini.")
            return redirect('layanan_urls:layanan_cuti_listview')

        # jika sudah ada pelimpahan, redirect ke halaman detail
        if hasattr(self.riwayat_cuti, 'pelimpahan_tugas'):
            return redirect('layanan_urls:pelimpahan_detail', pk=self.riwayat_cuti.pelimpahan_tugas.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['riwayat_cuti'] = self.riwayat_cuti
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.riwayat_cuti = self.riwayat_cuti
        obj.pemberi_tugas = self.request.user
        # Default status ketika selesai isi form: menunggu persetujuan penerima
        obj.status = 'menunggu_penerima'
        obj.persetujuan_penerima = "belum"
        obj.persetujuan_atasan = "belum"
        
        # aturan: jika pemberi level4 => set atasan (level3) sebagai penyetuju
        # jika pemberi level3+ => persetujuan atasan tidak diperlukan => auto "disetujui"
        if obj.requires_atasan_approval():
            obj.atasan_penyetuju = resolve_atasan_level3_for_level4(obj.pemberi_tugas)
            obj.persetujuan_atasan = "belum"
        else:
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
        if u.is_superuser or u in [obj.pemberi_tugas, obj.penerima_tugas, obj.atasan_penyetuju]:
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
            status__in=['menunggu_penerima', 'menunggu_kepala', 'disetujui']
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
    
    def form_valid(self, form):
        obj = form.instance  # atau: obj = self.object

        aksi = form.cleaned_data["aksi"]
        obj.catatan_penerima = form.cleaned_data.get("catatan_penerima", "")

        if aksi == "tolak":
            obj.persetujuan_penerima = "ditolak"
            obj.status = "ditolak_penerima"
            obj.save(update_fields=["catatan_penerima", "persetujuan_penerima", "status"])
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

        # Filter: kepala yang berhak = atasan langsung dari pemohon level4 (SubBidang.nama_pimpinan)
        # Kita gunakan riwayat penempatan aktif pemohon -> penempatan_level4 -> nama_pimpinan
        qs = qs.filter(
            riwayat_cuti__pegawai__riwayat_penempatan__status=True,
            riwayat_cuti__pegawai__riwayat_penempatan__penempatan_level4__isnull=False,
            riwayat_cuti__pegawai__riwayat_penempatan__penempatan_level4__nama_pimpinan=user,
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

        self.object = form.save(commit=False)  # <-- penting: jangan langsung form.save()

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
    context_object_name = "layanan"
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

        # status ringkas untuk penilaian (gabungan)
        status_ringkas = {
            "layanan_status": layanan.status,  # draft/pengajuan/tindaklanjut/selesai
            "persetujuan": getattr(main, "status_persetujuan", None),  # belum/disetujui/ditolak
            "status_cuti": getattr(main, "status_cuti", None),  # Proses/Selesai/Tunda
        }

        # izin akses sederhana:
        # - pemohon boleh lihat detailnya sendiri
        # - superuser boleh lihat semua
        # - admin boleh (opsional) tambahkan rules profil_admin sesuai kebutuhan
        user = self.request.user
        can_view = user.is_staff or (layanan.pegawai_id == user.id)
        # jika Anda punya aturan admin, bisa diperluas di sini
        if not can_view:
            # biar aman, Anda bisa raise PermissionDenied
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Anda tidak berhak melihat detail pengajuan cuti ini.")

        context.update({
            "details": details,
            "main": main,
            "total_hari": total_hari,
            "status_ringkas": status_ringkas,

            # tampilan
            "title_page": "Detail Pengajuan Cuti",
            "card_title": "Detail Cuti Pegawai",
            "cuti": "active",
            "layanan": "active",
            "selected": "yancuti",
        })
        return context


#refactoring layanan cuti -- masih memikirkan logika cuti tahun sebelumnya jika tidak diajukan cuti tunda
class LayanananCutiInlineCreateView(LoginRequiredMixin, CheckCuti, CreateView):
    model = LayananCuti
    template_name = '6_layanan_cuti/layanan_cuti_inline_create.html'
    form_class = LayananCutiForm
    redirect_display = 'layanan_urls:layanan_cuti_view'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        layanan = JenisLayanan.objects.filter(url='yancuti')
        initial = {'layanan':layanan.first(), 'status':'pengajuan'}
        if self.request.user.is_authenticated and not self.request.user.is_superuser:
            initial['pegawai'] = self.request.user
        initial['pegawai'] = self.request.user
        kwargs['request'] = self.request
        kwargs['initial'] = initial
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dokumen = DokumenSDM.objects.filter(url='cuti')
        initial = {'dokumen':dokumen.first()}
        if self.request.POST:
            context['formset'] = pengajuan_cuti_formset(data=self.request.POST, form_kwargs={'request': self.request})
        else:
            context['formset'] = pengajuan_cuti_formset(form_kwargs={'request': self.request}, initial=[initial])
        context['cek_sisa_cuti'] = self.cek_sisa_cuti(self.request.user)
        context['cek_sisa_tunda_cuti'] = self.cek_sisa_tunda_cuti(self.request.user)
        context['card_title'] = 'Pengajuan Cuti'
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        aksi = self.request.POST.get("aksi")

        with transaction.atomic():
            # validasi cuti
            if form.is_valid() and formset.is_valid():
                for f in formset:
                    if f.instance.pk and f.has_changed():
                        f.add_error(None, "Data pengajuan cuti sebelumnya tidak boleh diubah.")
                        return self.form_invalid(form)

                tgl_mulai = next((f.cleaned_data.get('tgl_mulai_cuti') for f in formset if f.cleaned_data), None)
                lama_cuti = next((f.cleaned_data.get('lama_cuti') for f in formset if f.cleaned_data), None)

                if tgl_mulai and self.cek_waktu_pengajuan_cuti(tgl_mulai):
                    messages.error(self.request, 'Maaf, pengajuan cuti paling lambat 7 hari sebelumnya.')
                    return self.form_invalid(form)

                if lama_cuti and (self.cek_sisa_cuti(self.request.user) <= 0 or
                                  self.cek_sisa_cuti(self.request.user) < lama_cuti):
                    messages.warning(self.request, 'Maaf, sisa cuti tidak mencukupi.')
                    return self.form_invalid(form)

                data = form.save(commit=False)
                data.status = 'pengajuan' if aksi == 'ajukan' else 'draft'
                data.save()

                layanan_cuti = formset.save(commit=False)
                for item in layanan_cuti:
                    item.cuti = data
                    item.pegawai = form.cleaned_data.get('pegawai')
                    item.save()

                messages.success(self.request, 'Pengajuan cuti berhasil dikirim.')

        return super().form_valid(form)
    

class LayananCutiInlineFormView(LoginRequiredMixin, CheckCuti, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    redirect_display = 'layanan_urls:layanan_cuti_view'

    def get_user(self, nip):
        try: 
            data = Users.objects.get(profil_user__nip=nip)
            return data
        except Exception:
            return None
        
    def get(self, request, *args, **kwargs):
        status_pengajuan_cuti = kwargs.get('status')
        user = request.user
        self.set_allow_cuti_tunda()
        """
        proses allow cuti tinggal atasannya melakukan updating terhadap eksisting
        cuti merubah cuti tunda menjadi cuti proses atau cuti selesai
        """
        form_view = 'none'
        data_view = 'block'
        dokumen = DokumenSDM.objects.filter(url='cuti')
        layanan = JenisLayanan.objects.filter(url='yancuti')
        data = LayananCuti.objects.all().order_by('-updated_at')
        initial_riwayat = {'dokumen':dokumen.first()}
        initial = {'layanan':layanan.first(), 'status':'pengajuan'}
        nip = None
        card_title = 'Riwayat Pengajuan Cuti'
        if not request.user.is_superuser:
            initial_riwayat = {'pegawai':user, 'dokumen':dokumen.first()}
            initial = {'pegawai':user, 'layanan':layanan.first(), 'status':'pengajuan'}
            nip = get_nip(user)
            if nip:
                data = LayananCuti.objects.filter(pegawai__profil_user__nip=nip).order_by('-updated_at')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'layanan', 'selected':'yancuti'}))
        # allow_cuti_tunda = can_manage_cuti_tunda or cuti_tunda.exists()
        layanan_form = LayananCutiForm(initial=initial, request=request, action='add')
        form = pengajuan_cuti_formset(initial=[initial_riwayat], form_kwargs={'action':'add', 'status':status_pengajuan_cuti})
        card_title = 'Input Pengajuan Cuti'
        form_view = 'block'
        data_view = 'none'
        context={
            'nip':nip,
            'data':data,
            # 'cuti_tunda':cuti_tunda,
            # 'allow_cuti_tunda': allow_cuti_tunda,
            # 'can_manage_cuti_tunda': can_manage_cuti_tunda,
            'layanan_form':layanan_form,
            'status':status_pengajuan_cuti,
            'form':form,
            'cek_sisa_cuti':self.cek_sisa_cuti(user),
            'card_title':card_title,
            'form_view':form_view,
            'data_view':data_view,
            'cuti':'active',
            'layanan':'active',
            'title_page':'Layanan Cuti',
            'selected':'yancuti'
        }
        return render(request, '6_layanan_cuti/layanan_cuti_master.html', context)
    
    def post(self, request, *args, **kwargs):
        status_pengajuan_cuti = kwargs.get('status')
        self.set_allow_cuti_tunda()
        can_manage_cuti_tunda = self.can_manage_cuti_tunda(request.user)
        if status_pengajuan_cuti == 'baru' or status_pengajuan_cuti == 'tunda':
            if status_pengajuan_cuti == 'tunda' and not can_manage_cuti_tunda:
                messages.info(request, 'Penundaan cuti hanya dapat diatur oleh atasan langsung (kasi/kasubbag).')
                return redirect(reverse(self.redirect_display, kwargs={'status': 'baru'}))
            riwayat_form = LayananCutiForm(data=request.POST, files=request.FILES, request=request, action='add')
            form = pengajuan_cuti_formset(data=request.POST, files=request.FILES, form_kwargs={'action':'add'})

            if riwayat_form.is_valid() and form.is_valid():
                with transaction.atomic():
                    data_riwayat = riwayat_form.save(commit=False)
                    # print('form: ', form.cleaned_data[0].get('tgl_mulai_cuti'))
                    data_riwayat.tahun_cuti = form.cleaned_data[0].get('tahun') if form.cleaned_data[0].get('tahun') else date.today().year
                    data_riwayat.save()
                    data_form = form.save(commit=False)
                    # print('data_form: ', data_form[0])
                    target_pegawai = data_form[0].pegawai if hasattr(data_form[0], 'pegawai') and data_form[0].pegawai else request.user
                    sisa_cuti = self.cek_sisa_cuti(target_pegawai)
                    data_form[0].jenis_cuti = form.cleaned_data[0].get('jenis_cuti')
                    data_form[0].tgl_mulai_cuti = form.cleaned_data[0].get('tgl_mulai_cuti')
                    data_form[0].lama_cuti = form.cleaned_data[0].get('lama_cuti')
                    
                    if data_form[0].jenis_cuti == 'Cuti Tahunan' and self.cek_waktu_pengajuan_cuti(data_form[0].tgl_mulai_cuti):
                        if sisa_cuti > 0 and sisa_cuti >= data_form[0].lama_cuti:
                            for item_riwayat in data_form:
                                item_riwayat.usulan = data_riwayat
                                item_riwayat.save()
                            messages.success(request, 'Pengajuan cuti anda sukses, dan segera akan ditindaklanjuti oleh bagian SDM')
                            return redirect(reverse(self.redirect_display, kwargs={'status':'riwayat'}))
                        messages.error(request, 'Maaf anda belum isi lama cuti atau jatah cuti tahunan anda kurang atau habis!')
                        return redirect(reverse(self.redirect_display, kwargs={'status':status_pengajuan_cuti}))
                    elif data_form[0].jenis_cuti == 'Cuti Alasan Penting' or data_form[0].jenis_cuti == 'Cuti melahirkan' or data_form[0].jenis_cuti == 'Cuti Sakit':
                        for item_riwayat in data_form:
                            item_riwayat.usulan = data_riwayat
                            item_riwayat.save()
                        messages.success(request, 'Pengajuan cuti anda sukses, dan segera akan ditindaklanjuti oleh bagian SDM')
                        return redirect(reverse(self.redirect_display, kwargs={'status':'riwayat'}))
                    messages.error(request, 'Mohon maaf waktu pengajuan cuti anda terlalu mepet atau tidak sesuai!!')
                    return redirect(reverse(self.redirect_display, kwargs={'status':status_pengajuan_cuti}))
            messages.error(request, 'Maaf form tidak valid')
            return redirect(reverse(self.redirect_display, kwargs={'status':status_pengajuan_cuti}))
        return redirect(reverse(self.redirect_display, kwargs={'status':'riwayat'}))


class LayananCutiTundaView(LoginRequiredMixin, CheckCuti, ListView):
    model = LayananCuti
    template_name = '6_layanan_cuti/layanan_cuti_tunda.html'

    def get_queryset(self):
        tanggal = date.today()
        tahun_ini = tanggal.year
        two_year_before = tanggal.year - 2
        queryset = LayananCuti.objects.filter(pegawai=self.request.user, cuti_tunda=True, cuti__tahun_cuti__lte=tahun_ini, cuti__tahun_cuti__gt=two_year_before )
        if self.request.user.is_superuser:
            queryset = LayananCuti.objects.filter(cuti__status_cuti='Tunda', cuti__tahun_cuti__lte=tahun_ini, cuti__tahun_cuti__gt=two_year_before)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'status':'ambil-tunda',
            'cek_sisa_cuti':self.cek_sisa_cuti(self.request.user),
            'cek_sisa_tunda_cuti':self.cek_sisa_tunda_cuti(self.request.user),
            'card_title':'Daftar Cuti Tunda'
        })
        return context
    

class LayananCreateCutiFromCutiTunda(LoginRequiredMixin, CheckCuti, CreateView):
    model = RiwayatCuti
    template_name = '6_layanan_cuti/layanan_cuti_tunda_ambil.html'
    form_class = RiwayatCutiTundaForm
    
    def get_success_url(self):
        return reverse('layanan_urls:layanan_cuti_view', kwargs={'status':'riwayat'})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['layanan_form'] = pengajuan_cuti_formset(data=self.request.POST)
        else:
            layanan_data = self.get_object()
            layanan_cuti = LayananCuti.objects.filter(cuti=layanan_data).last()
            initial=[{'pegawai':layanan_cuti.pegawai, 'layanan':layanan_cuti.layanan, 'jenis_jabatan':layanan_cuti.jenis_jabatan, 'cuti_tunda':1, 'status':'pengajuan'}] 
            context['layanan_form'] = pengajuan_cuti_formset(initial=initial)
        context['status'] = 'ambil-tunda'
        context['cek_sisa_cuti'] = self.cek_sisa_cuti(self.request.user)
        context['cek_sisa_tunda_cuti'] = self.cek_sisa_tunda_cuti(self.request.user)
        context['card_title'] = 'Ambil Cuti Tunda'
        return context 
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        data = self.get_object()
        kwargs['request'] = self.request
        if data is not None:
            kwargs['initial'] = {
                'pegawai': data.pegawai, 'jenis_cuti': data.jenis_cuti, 'lama_cuti': data.lama_cuti, 'tahun_cuti': data.tahun_cuti,
                'tgl_mulai_cuti': data.tgl_mulai_cuti, 'tgl_akhir_cuti': data.tgl_akhir_cuti, 'status_cuti': 'Proses',
                'dokumen': data.dokumen, 'alasan_cuti': data.alasan_cuti
            }
        return kwargs
    
    def update_lama_cuti(self, lama_cuti, data):
        if data.lama_cuti >= lama_cuti:
            data.lama_cuti = data.lama_cuti-lama_cuti
            data.save()#save riwayat cuti setelah lama cuti diupdate
            return data
        else:
            return None
    
    def form_valid(self, form):
        context = self.get_context_data()
        layanan_form = context['layanan_form']
        if form.is_valid() and layanan_form.is_valid() and not self.cek_waktu_pengajuan_cuti(form.cleaned_data.get('tgl_mulai_cuti')):
            messages.error(self.request, 'Maaf waktu pengajuan paling lambat 7 hari sebelum cuti!')
            return super().form_invalid(form)
        elif form.is_valid() and layanan_form.is_valid():
            #cek apakah lama cuti yang akan diambil lebih kecil atau sama dengan lama cuti tunda yang ada
            data = self.update_lama_cuti(form.cleaned_data.get('lama_cuti'), self.get_object())
            #jika lebih kecil maka lama sisa cuti tunda akan diupdate dan cuti baru yang akan diambil dibuatkan baru
            if data is not None and data.lama_cuti > 0:
                self.object = form.save(commit=False)
                self.object.status_cuti = 'Proses'
                self.object.save()
                for layanan in layanan_form:
                    item_layanan = layanan.save(commit=False)
                    item_layanan.cuti = self.object
                    item_layanan.cuti_tunda=0
                    item_layanan.status='pengajuan'
                    item_layanan.save()
                return super().form_valid(form)
            #jika sama maka data cuti tunda diupdate tanpa membuat cuti baru
            elif data is not None and data.lama_cuti == 0:
                data.lama_cuti = form.cleaned_data.get('lama_cuti')
                data.status_cuti = 'Proses'
                data.save()
                data_layanan = LayananCuti.objects.filter(cuti=self.get_object()).last()
                data_layanan.cuti_tunda = 0
                data_layanan.status='pengajuan'
                data_layanan.save()
            return redirect(reverse('layanan_urls:layanan_cuti_view', kwargs={'status':'riwayat'}))
        messages.error(self.request, 'Maaf terdapat kesalahan dalam pengisian form')
        return self.form_invalid(form)
    

class UploadFileCutiView(LoginRequiredMixin, View, CheckCuti):
    def get_object(self, id):
        try:
            data = RiwayatCuti.objects.get(id=id)
            return data
        except RiwayatCuti.DoesNotExist:
            return None
        
    def post(self, request, *args, **kwargs):
        id = kwargs.get('id')
        data_object = self.get_object(id)
        file = data_object.file if data_object else None
        form = RiwayatCutiTundaForm(data=request.POST, files=request.FILES, instance=self.get_object(id))
        if form.is_valid():
            form.cleaned_data.get('file')
            data = form.save(commit=False)
            data.status_cuti = 'Selesai'
            delete_existing_object(data, data_object, file)
            data.save()
            messages.success(request, 'Perubahan data cuti tunda berhasil disimpan.')
            return redirect(reverse('layanan_urls:layanan_cuti_tunda_view'))
        messages.error(request, 'Maaf terdapat kesalahan dalam pengisian form.')
        return redirect(reverse('layanan_urls:layanan_cuti_tunda_update', kwargs={'id':id}))
    
    
class LayananUpdateCUtiTundaView(LoginRequiredMixin, CheckCuti, UpdateView):    
    model = RiwayatCuti
    template_name = '6_layanan_cuti/layanan_cuti_tunda_ambil.html'
    form_class = RiwayatCutiTundaForm
    success_url = reverse_lazy('layanan_urls:layanan_cuti_tunda_view')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        riwayat_instance = self.get_object()
        context['layanan_form'] = update_pengajuan_cuti_fullform_formset(self.request.POST or None, instance=riwayat_instance)           
        context['status'] = 'ambil-tunda'
        context['cek_sisa_cuti'] = self.cek_sisa_cuti(self.request.user)
        context['cek_sisa_tunda_cuti'] = self.cek_sisa_tunda_cuti(self.request.user)
        context['card_title'] = 'Ambil Cuti Tunda'
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        layanan_form = context['layanan_form']
        if form.is_valid() and layanan_form.is_valid():
            self.object = form.save()
            for layanan in layanan_form:
                item_layanan = layanan.save(commit=False)
                item_layanan.cuti = self.object
                item_layanan.save()
            return super().form_valid(form)
        print('Form is invalid: ', form.errors)
        print('Layanan Form is invalid: ', layanan_form.errors)
        return self.render_to_response(self.get_context_data(form=form))
        
        
class LayananCutiUpdateView(LoginRequiredMixin, CheckCuti, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id):
        try:
            data = LayananCuti.objects.get(id=id)
            return data
        except LayananCuti.DoesNotExist:
            return None
        
    def get_verification_object(self, id):
        try:
            layanan_cuti = LayananCuti.objects.get(id=id)
            data, _ = VerifikasiCuti.objects.get_or_create(layanan_cuti=layanan_cuti)
            return data
        except LayananCuti.DoesNotExist:
            return None

    def get_riwayat_object(self, id):
        try:
            layanan_cuti = LayananCuti.objects.get(id=id)
            data = RiwayatCuti.objects.get(usulan__id=layanan_cuti.pk)
            return data
        except RiwayatCuti.DoesNotExist:
            return None
        
    def get(self, request, *args, **kwargs):
        get_case = request.GET.get('case')
        get_level = request.GET.get('level')
        selected_nip = kwargs.get('nip')
        status_pengajuan_cuti = kwargs.get('status')
        id = kwargs.get('id')
        nip = None
        card_title = 'Edit Pengajuan Cuti'
        form_view = 'block'
        data_view = 'none'
        user = request.user
        layanan_instance = self.get_object(id)
        verifikasi_cuti = self.get_verification_object(id)
        instalasi = None
        nama_verifikator=None
        penempatan = None
        if request.user.is_staff:
            nip = selected_nip
            user = layanan_instance.pegawai if layanan_instance is not None else None
            instalasi = layanan_instance.pegawai.riwayat_penempatan.filter(status=True).last()
            if instalasi is not None:
                penempatan = instalasi.penempatan
        else:
            nip = get_nip(request.user)  
        riwayat_instance = self.get_riwayat_object(id)
        form = update_pengajuan_cuti_formset(instance=layanan_instance, form_kwargs={'action':'edit'})
        layanan_form = LayananCutiForm(instance=layanan_instance, request=request, action='edit')
        verifikator_form = VerifikatorCutiForm(instance=verifikasi_cuti) 
        if get_case == 'tindaklanjut':
            form = update_pengajuan_cuti_formset(instance=layanan_instance, form_kwargs={'case': 'tindaklanjut'})
            layanan_form = LayananCutiForm(instance=layanan_instance, request=request, case='tindaklanjut')
            if get_level == '1':
                verifikator_form = Verifikator1CutiForm(instance=verifikasi_cuti)
            elif get_level == '2':
                verifikator_form = Verifikator2CutiForm(instance=verifikasi_cuti)
            elif get_level == '3':
                verifikator_form = Verifikator3CutiForm(instance=verifikasi_cuti)
            if instalasi is not None and instalasi.nama_atasan['nip_atasan1'] != "N/A":
                nama_verifikator = instalasi.nama_atasan
                nama_verifikator.update({
                    'direktur':instalasi.penempatan_level1.nama_pimpinan.full_name_2,
                    'nip_direktur':instalasi.penempatan_level1.nama_pimpinan.profil_user.nip if instalasi.penempatan_level1.nama_pimpinan and hasattr(instalasi.penempatan_level1.nama_pimpinan, 'profil_user') else None
                })
            else:
                nama_verifikator = ""
            card_title = 'Proses Pengajuan Cuti'
            data_view = 'block'
            form_view = 'none'
        elif get_case == 'final':
            form = update_pengajuan_cuti_formset(instance=layanan_instance)
            layanan_form = RiwayatCutiUploadSuratForm(instance=layanan_instance)
            card_title = 'Upload Surat Cuti'
            data_view = 'block'
            form_view = 'none'
        elif get_case == 'detail':
            card_title = 'Detail Pengajuan Cuti'
            data_view = 'block'
            form_view = 'none'
        context={
            'update_form':True,
            'nip':nip,
            'riwayat_form': layanan_form,
            'form':form,
            'verifikator_form':verifikator_form,
            'cek_sisa_cuti':self.cek_sisa_cuti(request.user),
            'cek_sisa_tunda_cuti':self.cek_sisa_tunda_cuti(request.user),
            'cek_sisa_cuti_pegawai':self.cek_sisa_cuti(user),
            'cek_sisa_tunda_cuti_pegawai':self.cek_sisa_tunda_cuti(user),
            # 'cek_total_cuti_tahunan': self.cek_total_cuti_termasuk_sedang_proses(user),
            'cek_total_pegawai_cuti': self.cek_pegawai_cuti_perinstalasi(penempatan),
            'status':status_pengajuan_cuti,
            'data_detail':layanan_instance,
            'nama_verifikator':nama_verifikator,
            'card_title':card_title,
            'form_view':form_view,
            'data_view':data_view,
            'case':get_case,
            'cuti':'active',
            'layanan':'active',
            'title_page':'Layanan Cuti',
            'selected':'yancuti'
        }
        return render(request, '6_layanan_cuti/layanan_cuti_master.html', context)
    
    def post(self, request, *args, **kwargs):
        status_pengajuan_cuti = kwargs.get('status')
        get_case = request.GET.get('case')
        get_level = request.GET.get('level')
        id = kwargs.get('id')
        layanan_instance = self.get_object(id)
        verifikasi_cuti = self.get_verification_object(id)
        aksi = request.POST.get("aksi", "verifikasi")
        riwayat_instance = self.get_riwayat_object(id)
        riwayat_form = LayananCutiForm(data=request.POST, files=request.FILES, instance=layanan_instance, request=request, action='edit')
        form = update_pengajuan_cuti_formset(data=request.POST, files=request.FILES, instance=layanan_instance)
        verifikator_form = VerifikatorCutiForm(data=request.POST, files=request.FILES, instance=verifikasi_cuti)
        if get_case == 'tindaklanjut':
            if aksi == 'aksi':
                riwayat_instance.status_cuti='Tunda'
                riwayat_instance.save()
            else:
                form = update_pengajuan_cuti_formset(data=request.POST, files=request.FILES, instance=layanan_instance, form_kwargs={'case': 'tindaklanjut'})
                riwayat_form = LayananCutiForm(data=request.POST, files=request.FILES, instance=layanan_instance, request=request, case='tindaklanjut')
                if get_level == '1':
                    verifikator_form = Verifikator1CutiForm(data=request.POST, files=request.FILES, instance=verifikasi_cuti)
                elif get_level == '2':
                    verifikator_form = Verifikator2CutiForm(data=request.POST, files=request.FILES, instance=verifikasi_cuti)
                elif get_level == '3':
                    verifikator_form = Verifikator3CutiForm(data=request.POST, files=request.FILES, instance=verifikasi_cuti)
        elif get_case == 'final':
            form = update_pengajuan_cuti_formset(data=request.POST, files=request.FILES, instance=layanan_instance)
            riwayat_form = RiwayatCutiUploadSuratForm(data=request.POST, files=request.FILES, instance=layanan_instance)
        url_redirect = reverse('layanan_urls:layanan_cuti_update_view', kwargs={'status':status_pengajuan_cuti, 'id':id})
        if verifikator_form.is_valid():
            verifikator = verifikator_form.save(commit=False)
            if get_level == '1':
                verifikator.verifikator1 = request.user
                layanan_instance.status = 'pengajuan'
                layanan_instance.save()
            elif get_level == '2':
                verifikator.verifikator2 = request.user
            elif get_level == '3':
                verifikator.verifikator3 = request.user
                verifikator.tanggal = date.today()
            verifikator.save()
            return redirect(f'{url_redirect}?case=tindaklanjut#close')
        if riwayat_form.is_valid() and form.is_valid():
            data_submitted = riwayat_form.save(commit=False)
            file1 = riwayat_instance.file_pengajuan if riwayat_instance is not None and hasattr(riwayat_instance, 'file_pengajuan') else None
            delete_existing_object(data_submitted, riwayat_instance, file1)
            file2 = riwayat_instance.file_pendukung if riwayat_instance is not None and hasattr(riwayat_instance, 'file_pendukung') else None
            delete_existing_object(data_submitted, riwayat_instance, file2)
            
            data_submitted.save()
            for item in form:
                if item.is_valid():
                    data_usulan = item.save(commit=False)
                    data_status = ['tindaklanjut', 'selesai']
                    if get_case == 'tindaklanjut' and not any(data == layanan_instance.status for data in data_status):
                        data_usulan.status = form.cleaned_data[0].get('status')
                        if data_usulan.status == 'tidak ditindaklanjut':
                            data_usulan.lama_cuti = 0
                            data_usulan.save()
                    elif get_case == 'final':
                        data_usulan.status = 'selesai'
                    data_usulan.save()
            messages.success(request, 'Data berhasil disimpan!') 
            return redirect(reverse('layanan_urls:layanan_cuti_view', kwargs={'status':'riwayat'}))
        for formitem in form:
            for field, errors in formitem.errors.items():
                    for error in errors:
                        messages.error(request, error)
        for field, errors in riwayat_form.errors.items():
                for error in errors:
                    if error:
                        messages.error(request, error)
                    else:
                        messages.error(request, 'Maaf data gagal disimpan!')
        return redirect(reverse('layanan_urls:layanan_cuti_view', kwargs={'status':'riwayat'}))


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
            self._verifikasi_obj, _ = VerifikasiCuti.objects.get_or_create(
                layanan_cuti=self.get_layanan_cuti()
            )
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
        rp = self.get_riwayat_penempatan_aktif()
        chain = []

        if not rp:
            return chain

        # Pegawai level 4 (Instalasi) → diverifikasi: Kasi/SubBidang, Kabid, Unor
        if rp.penempatan_level4:
            inst = rp.penempatan_level4
            sb = inst.sub_bidang
            b = sb.bidang
            u = b.unor

            chain.append({
                "level": 1,
                "user": sb.nama_pimpinan,
                "label": f"{sb.pimpinan} {sb.sub_bidang}",
            })
            chain.append({
                "level": 2,
                "user": b.nama_pimpinan,
                "label": f"{b.pimpinan} {b.bidang}",
            })
            chain.append({
                "level": 3,
                "user": u.nama_pimpinan,
                "label": f"{u.pimpinan} {u.unor}",
            })

        # Pegawai level 3 (SubBidang) → diverifikasi: Kabid, Unor
        elif rp.penempatan_level3:
            sb = rp.penempatan_level3
            b = sb.bidang
            u = b.unor

            chain.append({
                "level": 1,
                "user": b.nama_pimpinan,
                "label": f"{b.pimpinan} {b.bidang}",
            })
            chain.append({
                "level": 2,
                "user": u.nama_pimpinan,
                "label": f"{u.pimpinan} {u.unor}",
            })

        # Pegawai level 2 (Bidang) → diverifikasi: Unor, SatkerInduk
        elif rp.penempatan_level2:
            b = rp.penempatan_level2
            u = b.unor
            sk = u.satker_induk

            chain.append({
                "level": 1,
                "user": u.nama_pimpinan,
                "label": f"{u.pimpinan} {u.unor}",
            })
            chain.append({
                "level": 2,
                "user": sk.nama_pimpinan,
                "label": f"{sk.pimpinan} {sk.satuan_kerja}",
            })

        # Pegawai level 1 (Unor) → diverifikasi: SatkerInduk, (opsional) InstansiDaerah
        elif rp.penempatan_level1:
            u = rp.penempatan_level1
            sk = u.satker_induk
            inst = sk.instansi_daerah

            chain.append({
                "level": 1,
                "user": sk.nama_pimpinan,
                "label": f"{sk.pimpinan} {sk.satuan_kerja}",
            })
            chain.append({
                "level": 2,
                "user": inst.nama_pimpinan,
                "label": f"{inst.pimpinan} {inst.instansi}",
            })

        # kalau mau handle langsung pegawai di SatkerInduk: bisa ditambah branch lain

        return chain

    @property
    def verifikator_chain(self):
        if not hasattr(self, "_verifikator_chain"):
            self._verifikator_chain = self.build_verifikator_chain()
        return self._verifikator_chain

    @property
    def current_level(self):
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied

        # ✅ SUPERADMIN = MONITOR (TIDAK VERIFIKASI)
        if self.is_monitor_user():
            return None  # <- PENTING

        for item in self.verifikator_chain:
            atasan = item["user"]
            if atasan and atasan.pk == user.pk:
                return item["level"]

        raise PermissionDenied(
            "Anda tidak memiliki kewenangan untuk memverifikasi cuti ini."
        )
    
    def is_monitor_user(self) -> bool:
        u = self.request.user
        return u.is_authenticated and u.is_superuser

    def dispatch(self, request, *args, **kwargs):
        # Panggil current_level utk validasi akses di awal
        if self.is_monitor_user():
            return super().dispatch(request, *args, **kwargs)
        
        _ = self.current_level
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
        if self.is_monitor_user():
            return Verifikator3CutiForm  # read-only

        level = self.current_level
        if level == 1:
            return Verifikator1CutiForm
        elif level == 2:
            return Verifikator2CutiForm
        return Verifikator3CutiForm

    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.is_monitor_user():
            for f in form.fields.values():
                f.disabled = True
        return form

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     kwargs.setdefault("request", self.request)
    #     return kwargs
    
    def post(self, request, *args, **kwargs):
        if self.is_monitor_user():
            messages.info(request, "Mode monitoring: Anda tidak dapat mengubah verifikasi.")
            return redirect(request.path)  # stay di halaman yang sama
        return super().post(request, *args, **kwargs)

    def _update_verifikator_user(self, verifikasi: VerifikasiCuti):
        """Set field verifikator1/2/3 dengan user login pada level-nya."""
        user = self.request.user
        level = self.current_level

        if level == 1 and hasattr(verifikasi, "verifikator1") and not verifikasi.verifikator1:
            verifikasi.verifikator1 = user
        elif level == 2 and hasattr(verifikasi, "verifikator2") and not verifikasi.verifikator2:
            verifikasi.verifikator2 = user
        elif level == 3 and hasattr(verifikasi, "verifikator3") and not verifikasi.verifikator3:
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
        if ada_keputusan and layanan.status in ("draft", "pengajuan"):
            layanan.status = "tindaklanjut"

        if riwayat and riwayat.status_persetujuan not in ("disetujui", "ditolak"):
            riwayat.status_persetujuan = "belum"

        # 1) Jika ADA TOLAK -> final ditolak
        if any(k == "tolak" for k in keputusan_values):
            layanan.status = "tidak ditindaklanjut"
            if riwayat:
                riwayat.status_persetujuan = "ditolak"
                # agar tidak ikut hitung pemakaian, paling aman:
                # biarkan status_cuti tetap 'Proses'? (jangan)
                # kalau Anda belum punya status khusus "Ditolak", set saja:
                riwayat.status_cuti = "Selesai"
            layanan.save()
            if riwayat:
                riwayat.save()
            return

        # 2) Jika ADA TUNDA -> final jadi saldo tunda
        if any(k == "tunda" for k in keputusan_values):
            layanan.status = "selesai"
            if riwayat:
                riwayat.status_persetujuan = "disetujui"
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
            layanan.status = "selesai"
            if riwayat:
                riwayat.status_persetujuan = "disetujui"
                # status_cuti: boleh tetap Proses sampai surat keluar, atau Selesai
                riwayat.status_cuti = "Proses"
            layanan.save()
            if riwayat:
                riwayat.save()
            return

        # 4) selain itu -> masih proses
        layanan.status = layanan.status or "tindaklanjut"
        layanan.save()
        if riwayat:
            riwayat.save()

    def form_valid(self, form):
        if self.is_monitor_user():
            messages.info(self.request, "Mode monitoring: tidak ada perubahan yang disimpan.")
            return redirect(self.request.path)
        
        verifikasi: VerifikasiCuti = form.save(commit=False)

        # set verifikatorX = user login
        self._update_verifikator_user(verifikasi)

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
        
        current_level = None if self.is_monitor_user() else self.current_level

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
        ctx["layanan_disetujui"] = (layanan.status == "selesai")

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
                "is_current": (current_level == lvl),
            })

        ctx.update({
            "title_page": "Verifikasi Pengajuan Cuti",
            "layanan": layanan,
            "riwayat": riwayat,
            "chain_display": chain_display,
            "current_level": self.current_level,
            "active_tab": "bawahan",
            "cek_sisa_cuti_pegawai": self.cek_sisa_cuti(layanan.pegawai),
            "cek_sisa_tunda_cuti_pegawai": self.cek_sisa_tunda_cuti(layanan.pegawai),
        })
        return ctx


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
            data3 = second_last_date[0].get('tmt_gaji')+relativedelta(months=24)
            return data3
        return None
    

class BerkalaListView(ListView):
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
    login_url = '/accounts/login/'
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
    

class LayananGajiBerkalaAdminView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

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
        if request.user.is_superuser:
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


class LayananGajiBerkalaAdminAddView(LoginRequiredMixin, View):    
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
        
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
        if request.user.is_superuser:
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
        

class LayananGajiBerkalaUpload(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

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


class PengalihanDiklatCreateView(LoginRequiredMixin, CreateView):
    model = LayananUsulanDiklat
    form_class = FormPengalihanUsulanDiklat
    template_name = '7_layanan_diklat/layanan_diklat_pengalihan.html'
    success_url = reverse_lazy('layanan_urls:layanan_diklat_staf_view')
    
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

        
class PenugasanDiklatCreateView(LoginRequiredMixin, CreateView):
    model = LayananUsulanDiklat
    form_class = FormPenugasanUsulanDiklat
    template_name = '7_layanan_diklat/layanan_diklat_form.html'
    success_url = reverse_lazy('layanan_urls:layanan_diklat_staf_view')
    
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

class LayananUsulanDiklatStaffView(LoginRequiredMixin, ListView):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    template_name = '7_layanan_diklat/layanan_diklat_list.html'
    model = LayananUsulanDiklat
    
    def get_queryset(self):
        queryset = None
        if self.request.user.is_staff and not self.request.user.is_superuser:
            penempatan_admin = self.request.user.riwayatpenempatan_set.filter(status=True).last()
            if penempatan_admin:
                queryset=self.model.objects.filter(
                        riwayatdiklat__pegawai__riwayatpenempatan__penempatan_level3__sub_bidang=penempatan_admin.penempatan, riwayatdiklat__pegawai__riwayatpenempatan__status=True
                    ).order_by('-id').exclude(riwayatdiklat__pegawai=self.request.user).distinct()|self.model.objects.filter(
                        riwayatdiklat__pegawai__riwayatpenempatan__penempatan_level2__bidang=penempatan_admin.penempatan, riwayatdiklat__pegawai__riwayatpenempatan__status=True
                    ).order_by('-id').exclude(riwayatdiklat__pegawai=self.request.user).distinct()|self.model.objects.filter(
                        riwayatdiklat__pegawai__riwayatpenempatan__penempatan_level1__unor=penempatan_admin.penempatan, riwayatdiklat__pegawai__riwayatpenempatan__status=True
                    ).order_by('-id').exclude(riwayatdiklat__pegawai=self.request.user).distinct()  
        elif self.request.user.is_superuser:
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
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    model = LayananUsulanDiklat
    
    def get_queryset(self):
        nip = get_nip(self.request.user)
        if not self.request.user.is_superuser and nip:
            queryset = LayananUsulanDiklat.objects.filter(riwayatdiklat__pegawai__profil_user__nip=nip).order_by('-id')
        else:
            queryset = LayananUsulanDiklat.objects.all().order_by('-id')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nip = get_nip(self.request.user)
        context['card_title'] = 'Riwayat Usulan Diklat'
        if not self.request.user.is_superuser and nip:
            context['card_title'] = 'Riwayat Diklat Saya'
        context['diklat']='active'
        context['layanan']='active'
        context['title_page']='Layanan Diklat'
        context['selected']='yandiklat'
        return context
    
    def get_template_names(self):
        if self.request.user.is_superuser:
            return ['7_layanan_diklat/layanan_diklat_list.html']
        return ['7_layanan_diklat/layanan_diklat_perorang.html']
    
    
class LayananUsulanDiklatCreateView(LoginRequiredMixin, CreateView):
    login_url = '/accounts/login/'
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
        if not self.request.user.is_superuser:
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
                data_riwayat.pegawai.set(riwayat_form.cleaned_data[0].get('pegawai'))
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
    login_url = '/accounts/login/'
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
        if not user.is_superuser:
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
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    model = LayananUsulanDiklat
    success_url = reverse_lazy('layanan_urls:layanan_diklat_list_view')
    
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
            penempatan = data.pegawai.first().riwayatpenempatan_set.filter(status=True).last() if data.pegawai.first() is not None else None 
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
            nama_verifikator.update({
                'direktur':instalasi.penempatan_level1.nama_pimpinan.full_name_2,
                'nip_direktur':instalasi.penempatan_level1.nama_pimpinan.profil_user.nip if instalasi.penempatan_level1.nama_pimpinan and hasattr(instalasi.penempatan_level1.nama_pimpinan, 'profil_user') else None
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


class CatatanSDMUsulanLayananDiklatUpdateView(LoginRequiredMixin, UpdateView):
    model = LayananUsulanDiklat
    form_class = FormCatatanSDMUsulanLayananDiklat
    template_name = '7_layanan_diklat/layanan_diklat_catatan_sdm.html'
    
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
    login_url = '/accounts/login/'
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
        if not request.user.is_superuser:
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
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id):
        try:
            data = LayananUsulanInovasi.objects.get(id=id)
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
        if request.user.is_superuser:
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
        elif request.user.is_superuser:
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
        elif request.user.is_superuser:
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

