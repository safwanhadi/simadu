from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView, CreateView, DetailView, TemplateView
from django.db import transaction
# from django.views.generic import ListView, CreateView
from django.db.models import Sum, F, Q, Case, When, Value, Count, DateTimeField
from datetime import date
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime, date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from dateutil.relativedelta import relativedelta
from itertools import chain
import re
import os
import locale
from num2words import num2words

from .models import (
    JenisLayanan, 
    LayananCuti, 
    VerifikasiCuti, 
    LayananGajiBerkala, 
    LayananUsulanDiklat, 
    VerifikasiDiklat, 
    LayananUsulanInovasi
)
from myaccount.models import Users
from dokumen.models import (
    DokumenSDM, 
    RiwayatCuti, 
    RiwayatGajiBerkala, 
    RiwayatPenempatan, 
    RiwayatPanggol, 
    RiwayatDiklat, 
    RiwayatInovasi,
    Kompetensi
)
from .serializers import LayananGajiBerkalaSerializer
from dokumen.forms import (
    RiwayatPengajuanCutiForm,
    RiwayatCutiUploadSuratForm,
    RiwayatCutiUploadDakungForm,
    RiwayatCutiForm,
    RiwayatCutiTundaForm,
    RiwayatGajiBerkalaForm, 
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
    FormLayananCutiExisting,
    LayananCutiForm,
    VerifikatorCutiForm,
    Verifikator1CutiForm,
    Verifikator2CutiForm,
    Verifikator3CutiForm, 
    FormLayananBerkala, 
    pengajuan_cuti_formset,
    update_pengajuan_cuti_formset,
    pengajuan_cuti_fullform_formset,
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
    tindaklanjut_inovasi_formset
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

class CheckCuti:
    def cek_total_cuti_termasuk_sedang_proses(self, user):
        tanggal:date = date.today()
        total_cuti = 0
        riwayat_cuti = RiwayatCuti.objects.filter(pegawai = user)
        if riwayat_cuti:
            cek_total_cuti = riwayat_cuti.filter(jenis_cuti='Cuti Tahunan').values('tahun_cuti').annotate(
                cuti_tahunan = Sum(Case(When(Q(status_cuti__in=['Selesai', 'Proses', 'Tunda']) & Q(tahun_cuti=tanggal.year), then=F('lama_cuti')))),
            ).order_by('tahun_cuti')
            if cek_total_cuti.last() and cek_total_cuti.last()['cuti_tahunan'] is not None:
                total_cuti = cek_total_cuti.last()['cuti_tahunan']
        return total_cuti
    
    def cek_sisa_cuti(self, user) -> int:
        tanggal:date = date.today()
        sisa_cuti_tahunan = 12
        riwayat_cuti = RiwayatCuti.objects.filter(pegawai = user)
        if riwayat_cuti:
            cek_sisa_cuti = riwayat_cuti.filter(jenis_cuti='Cuti Tahunan').values('tahun_cuti').annotate(
                cuti_tahunan = Sum(Case(When(Q(status_cuti__in=['Selesai', 'Proses', 'Tunda']) & Q(tahun_cuti=tanggal.year), then=F('lama_cuti')))),
                sisa_cuti = 12 - F('cuti_tahunan')
            ).order_by('tahun_cuti')
            if cek_sisa_cuti.last() and cek_sisa_cuti.last()['sisa_cuti'] is not None:
                sisa_cuti_tahunan = cek_sisa_cuti.last()['sisa_cuti']
        return sisa_cuti_tahunan
    
    def cek_pegawai_cuti_perinstalasi(self, instalasi):
        data_cuti = {}
        jumlah = 0
        tanggal:date = date.today()
        cuti_pegawai = RiwayatCuti.objects.filter(Q(status_cuti__in=['Selesai', 'Proses'])&
                                                  Q(tgl_akhir_cuti__gte=tanggal)&
                                                  Q(pegawai__riwayatpenempatan__status=True)&
                                                  Q(pegawai__riwayatpenempatan__penempatan_level4__instalasi=instalasi)|
                                                  Q(pegawai__riwayatpenempatan__penempatan_level3__sub_bidang=instalasi)|
                                                  Q(pegawai__riwayatpenempatan__penempatan_level2__bidang=instalasi)|
                                                  Q(pegawai__riwayatpenempatan__penempatan_level1__unor=instalasi))
        total_cuti_pegawai = cuti_pegawai.aggregate(
            jlh = Count(F('pegawai'))
        )
        if total_cuti_pegawai.get("jlh") is not None:
            jumlah = total_cuti_pegawai.get("jlh")
        data_cuti.update({
            'jumlah':jumlah,
            'pegawai':cuti_pegawai
        })
        return data_cuti
    
    def cek_sisa_tunda_cuti(self, user) -> int:
        tanggal = date.today()
        year_before = tanggal.year - 1
        two_years_before = tanggal.year - 2
        tahun_cuti = [year_before, two_years_before]
        cuti_tertunda:int = 0
        riwayat_cuti = RiwayatCuti.objects.filter(pegawai = user, status_cuti='Tunda')
        if riwayat_cuti:
            cek_sisa_cuti = riwayat_cuti.annotate(
                cuti_tahunan = Sum(Case(When(Q(jenis_cuti='Cuti Tahunan') & Q(tahun_cuti__in = tahun_cuti), then=F('lama_cuti')))),
            )
            if cek_sisa_cuti.first() is not None:
                cuti_tertunda: int = cek_sisa_cuti.first().cuti_tahunan
        return cuti_tertunda
    
    def cek_waktu_pengajuan_cuti_tunda(self, tahun_cuti) -> bool:
        tanggal_sekarang = date.today()
        pengajuan_cuti_tunda = False
        if tanggal_sekarang.year == tahun_cuti:
            pengajuan_cuti_tunda = True
            return pengajuan_cuti_tunda
        return pengajuan_cuti_tunda
        
    def cek_waktu_pengajuan_cuti(self, tanggal_mulai_cuti):
        tanggal_sekarang = date.today()
        pengajuan_cuti = False
        # tanggal_cuti = get_date_from_string(tanggal_mulai_cuti)
        rentang_waktu = relativedelta(tanggal_mulai_cuti, tanggal_sekarang)
        if rentang_waktu.years == 0 and rentang_waktu.days >= 7:
            pengajuan_cuti = True
            return pengajuan_cuti
        return pengajuan_cuti

notfoundview = 'riwayat_urls:notfound_view'

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
        form_view = 'none'
        data_view = 'block'
        dokumen = DokumenSDM.objects.filter(url='cuti')
        layanan = JenisLayanan.objects.filter(url='yancuti')
        data = LayananCuti.objects.all().order_by('-updated_at')
        initial_riwayat = {'dokumen':dokumen.first()}
        initial = {'layanan':layanan.first(), 'status':'pengajuan'}
        nip = None
        card_title = 'Riwayat Pengajuan Cuti'
        cuti_tunda = RiwayatCuti.objects.filter(jenis_cuti='Cuti Tahunan', status_cuti='Tunda')
        if not request.user.is_superuser:
            cuti_tunda = RiwayatCuti.objects.filter(pegawai=user, jenis_cuti='Cuti Tahunan', status_cuti='Tunda')
            initial_riwayat = {'pegawai':user, 'dokumen':dokumen.first()}
            initial = {'pegawai':user, 'layanan':layanan.first(), 'status':'pengajuan'}
            nip = get_nip(user)
            if nip:
                data = LayananCuti.objects.filter(pegawai__profil_user__nip=nip).order_by('-updated_at')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'layanan', 'selected':'yancuti'}))
        riwayat_form = RiwayatPengajuanCutiForm(initial=initial_riwayat, request=request, status=status_pengajuan_cuti, action='add')
        form = pengajuan_cuti_formset(initial=[initial], form_kwargs={'action':'add'})
        if status_pengajuan_cuti == 'baru' or status_pengajuan_cuti == 'tunda':
            card_title = 'Input Pengajuan Cuti'
            form_view = 'block'
            data_view = 'none'
        context={
            'nip':nip,
            'data':data,
            'cuti_tunda':cuti_tunda,
            'riwayat_form':riwayat_form,
            'status':status_pengajuan_cuti,
            'form':form,
            'cek_sisa_cuti':self.cek_sisa_cuti(user),
            'cek_sisa_tunda_cuti':self.cek_sisa_tunda_cuti(user),
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
        if status_pengajuan_cuti == 'baru' or status_pengajuan_cuti == 'tunda':
            riwayat_form = RiwayatPengajuanCutiForm(data=request.POST, files=request.FILES, request=request, action='add')
            form = pengajuan_cuti_formset(data=request.POST, files=request.FILES, form_kwargs={'action':'add'})
        
            if riwayat_form.is_valid() and form.is_valid():
                data = riwayat_form.save(commit=False)
                data.jenis_cuti = riwayat_form.cleaned_data.get('jenis_cuti')
                data.tgl_mulai_cuti = riwayat_form.cleaned_data.get('tgl_mulai_cuti')
                data.tgl_akhir_cuti = riwayat_form.cleaned_data.get('tgl_akhir_cuti')
                data.lama_cuti = riwayat_form.cleaned_data.get('lama_cuti')
                data.status_cuti = riwayat_form.cleaned_data.get('status_cuti')
                if data.jenis_cuti == 'Cuti Tahunan' and self.cek_waktu_pengajuan_cuti(data.tgl_mulai_cuti):
                    if self.cek_sisa_cuti(request.user) > 0 and self.cek_sisa_cuti(request.user) >= data.lama_cuti:
                        data.save()
                        layanan_cuti = form.save(commit=False)
                        for item_layanan in layanan_cuti:
                            item_layanan.cuti = data
                            item_layanan.save()
                        messages.success(request, 'Pengajuan cuti anda sukses, dan segera akan ditindaklanjuti oleh bagian SDM')
                        return redirect(reverse(self.redirect_display, kwargs={'status':'riwayat'}))
                    messages.error(request, 'Maaf anda belum isi lama cuti atau jatah cuti tahunan anda kurang atau habis!')
                    return redirect(reverse(self.redirect_display, kwargs={'status':status_pengajuan_cuti}))
                elif data.jenis_cuti == 'Cuti Tahunan' and data.status_cuti == 'Tunda' and self.cek_waktu_pengajuan_cuti_tunda(data.tahun_cuti):
                    if self.cek_sisa_cuti(request.user) > 0 and self.cek_sisa_cuti(request.user) >= data.lama_cuti:
                        data.cuti_tunda = True
                        data.save()
                        layanan_cuti = form.save(commit=False)
                        for item_layanan in layanan_cuti:
                            item_layanan.cuti = data
                            item_layanan.status = 'selesai'
                            item_layanan.save()
                        messages.success(request, 'Pengajuan cuti TUNDA anda sukses, dan segera akan ditindaklanjuti oleh bagian SDM')
                        return redirect(reverse(self.redirect_display, kwargs={'status':'riwayat'}))
                    messages.error(request, 'Maaf anda belum isi lama cuti atau jatah cuti tunda anda kurang atau habis!')
                    return redirect(reverse(self.redirect_display, kwargs={'status':status_pengajuan_cuti}))
                elif data.jenis_cuti == 'Cuti Alasan Penting' or data.jenis_cuti == 'Cuti melahirkan' or data.jenis_cuti == 'Cuti Sakit':
                    data.save()
                    layanan_cuti = form.save(commit=False)
                    for item_layanan in layanan_cuti:
                        item_layanan.cuti = data
                        item_layanan.save()
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
    

class LayananUpdateCUtiTundaView(LoginRequiredMixin, UpdateView, CheckCuti):
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

#code ini tidak digunakan tapi bisa dijadikan referensi
class LayananCutiUpdateViewAIRESULT(LoginRequiredMixin, CheckCuti, UpdateView):
    model = LayananCuti
    template_name = '6_layanan_cuti/layanan_cuti_master.html'
    form_class = RiwayatPengajuanCutiForm
    second_form_class = VerifikatorCutiForm
    third_form_class = RiwayatCutiUploadSuratForm

    def get_object(self, queryset=None):
        id = self.kwargs.get('id')
        return LayananCuti.objects.get(id=id)

    def get_verification_object(self):
        layanan_cuti = self.get_object()
        return VerifikasiCuti.objects.get_or_create(layanan_cuti=layanan_cuti)[0]

    def get_riwayat_object(self):
        layanan_cuti = self.get_object()
        return RiwayatCuti.objects.get(id=layanan_cuti.cuti.id)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['action'] = 'edit'
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        get_case = self.request.GET.get('case')
        get_level = self.request.GET.get('level')
        layanan_instance = self.get_object()
        verifikasi_cuti = self.get_verification_object()
        riwayat_instance = self.get_riwayat_object()
        instalasi = layanan_instance.pegawai.riwayatpenempatan_set.filter(status=True).last()
        nama_verifikator = None

        if get_case == 'tindaklanjut':
            context['form'] = update_pengajuan_cuti_formset(instance=riwayat_instance, form_kwargs={'case': 'tindaklanjut'})
            context['riwayat_form'] = RiwayatPengajuanCutiForm(instance=riwayat_instance, request=self.request, case='tindaklanjut')
            if get_level == '1':
                context['verifikator_form'] = Verifikator1CutiForm(instance=verifikasi_cuti)
            elif get_level == '2':
                context['verifikator_form'] = Verifikator2CutiForm(instance=verifikasi_cuti)
            elif get_level == '3':
                context['verifikator_form'] = Verifikator3CutiForm(instance=verifikasi_cuti)
            if instalasi and instalasi.nama_atasan['nip_atasan1'] != "N/A":
                nama_verifikator = instalasi.nama_atasan
                nama_verifikator.update({
                    'direktur': instalasi.penempatan_level1.nama_pimpinan.full_name_2,
                    'nip_direktur': instalasi.penempatan_level1.nama_pimpinan.profil_user.nip if instalasi.penempatan_level1.nama_pimpinan and hasattr(instalasi.penempatan_level1.nama_pimpinan, 'profil_user') else None
                })
            context['card_title'] = 'Proses Pengajuan Cuti'
            context['data_view'] = 'block'
            context['form_view'] = 'none'
        elif get_case == 'final':
            context['form'] = update_pengajuan_cuti_formset(instance=riwayat_instance)
            context['riwayat_form'] = RiwayatCutiUploadSuratForm(instance=riwayat_instance)
            context['card_title'] = 'Upload Surat Cuti'
            context['data_view'] = 'block'
            context['form_view'] = 'none'
        elif get_case == 'detail':
            context['card_title'] = 'Detail Pengajuan Cuti'
            context['data_view'] = 'block'
            context['form_view'] = 'none'
        else:
            context['form'] = update_pengajuan_cuti_formset(instance=riwayat_instance, form_kwargs={'action': 'edit'})
            context['riwayat_form'] = RiwayatPengajuanCutiForm(instance=riwayat_instance, request=self.request, action='edit')
            context['verifikator_form'] = VerifikatorCutiForm(instance=verifikasi_cuti)

        context.update({
            'update_form': True,
            'nip': get_nip(self.request.user),
            'cek_sisa_cuti': self.cek_sisa_cuti(self.request.user),
            'cek_sisa_tunda_cuti': self.cek_sisa_tunda_cuti(self.request.user),
            'cek_sisa_cuti_pegawai': self.cek_sisa_cuti(layanan_instance.pegawai),
            'cek_sisa_tunda_cuti_pegawai': self.cek_sisa_tunda_cuti(layanan_instance.pegawai),
            'cek_total_cuti_tahunan': self.cek_total_cuti_termasuk_sedang_proses(layanan_instance.pegawai),
            'cek_total_pegawai_cuti': self.cek_pegawai_cuti_perinstalasi(instalasi.penempatan if instalasi else None),
            'status': self.kwargs.get('status'),
            'data_detail': layanan_instance,
            'nama_verifikator': nama_verifikator,
            'case': get_case,
            'cuti': 'active',
            'layanan': 'active',
            'title_page': 'Layanan Cuti',
            'selected': 'yancuti'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        layanan_instance = self.get_object()
        verifikasi_cuti = self.get_verification_object()
        riwayat_instance = self.get_riwayat_object()
        get_case = self.request.GET.get('case')
        get_level = self.request.GET.get('level')
        verifikator_form = context['verifikator_form']

        if verifikator_form.is_valid():
            verifikator = verifikator_form.save(commit=False)
            if get_level == '1':
                verifikator.verifikator1 = self.request.user
                layanan_instance.status = 'pengajuan'
                layanan_instance.save()
            elif get_level == '2':
                verifikator.verifikator2 = self.request.user
            elif get_level == '3':
                verifikator.verifikator3 = self.request.user
                verifikator.tanggal = date.today()
            verifikator.save()
            return redirect(f'{self.request.path}?case=tindaklanjut#close')

        if form.is_valid():
            data_riwayat = form.save(commit=False)
            if data_riwayat.file_pengajuan and riwayat_instance.file_pengajuan and riwayat_instance.file_pengajuan != data_riwayat.file_pengajuan and os.path.exists(riwayat_instance.file_pengajuan.path):
                os.remove(riwayat_instance.file_pengajuan.path)
            if data_riwayat.file_pendukung and riwayat_instance.file_pendukung and riwayat_instance.file_pendukung != data_riwayat.file_pendukung and os.path.exists(riwayat_instance.file_pendukung.path):
                os.remove(riwayat_instance.file_pendukung.path)
            data_riwayat.save()
            for item in context['form']:
                if item.is_valid():
                    data_usulan = item.save(commit=False)
                    data_status = ['tindaklanjut', 'selesai']
                    if get_case == 'tindaklanjut' and not any(data == layanan_instance.status for data in data_status):
                        data_usulan.status = context['form'].cleaned_data[0].get('status')
                        if data_usulan.status == 'tidak ditindaklanjuti':
                            data_riwayat.lama_cuti = 0
                            data_riwayat.save()
                    elif get_case == 'final':
                        data_usulan.status = 'selesai'
                    data_usulan.cuti = data_riwayat
                    data_usulan.save()
            messages.success(self.request, 'Data berhasil disimpan!')
            return redirect(reverse('layanan_urls:layanan_cuti_view', kwargs={'status': 'riwayat'}))

        for formitem in context['form']:
            for field, errors in formitem.errors.items():
                for error in errors:
                    messages.error(self.request, error)
        for field, errors in form.errors.items():
            for error in errors:
                if error:
                    messages.error(self.request, error)
                else:
                    messages.error(self.request, 'Maaf data gagal disimpan!')
        return redirect(reverse('layanan_urls:layanan_cuti_view', kwargs={'status': 'riwayat'}))
        
        
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
            data = RiwayatCuti.objects.get(id=id)
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
        id_riwayat = None
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
            instalasi = layanan_instance.pegawai.riwayatpenempatan_set.filter(status=True).last()
            if instalasi is not None:
                penempatan = instalasi.penempatan
        else:
            nip = get_nip(request.user)  
        if layanan_instance is not None:
            id_riwayat = layanan_instance.cuti.id if hasattr(layanan_instance, 'cuti') else None
        riwayat_instance = self.get_riwayat_object(id_riwayat)
        form = update_pengajuan_cuti_formset(instance=riwayat_instance, form_kwargs={'action':'edit'})
        riwayat_form = RiwayatPengajuanCutiForm(instance=riwayat_instance, request=request, action='edit')
        verifikator_form = VerifikatorCutiForm(instance=verifikasi_cuti) 
        if get_case == 'tindaklanjut':
            form = update_pengajuan_cuti_formset(instance=riwayat_instance, form_kwargs={'case': 'tindaklanjut'})
            riwayat_form = RiwayatPengajuanCutiForm(instance=riwayat_instance, request=request, case='tindaklanjut')
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
            form = update_pengajuan_cuti_formset(instance=riwayat_instance)
            riwayat_form = RiwayatCutiUploadSuratForm(instance=riwayat_instance)
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
            'riwayat_form': riwayat_form,
            'form':form,
            'verifikator_form':verifikator_form,
            'cek_sisa_cuti':self.cek_sisa_cuti(request.user),
            'cek_sisa_tunda_cuti':self.cek_sisa_tunda_cuti(request.user),
            'cek_sisa_cuti_pegawai':self.cek_sisa_cuti(user),
            'cek_sisa_tunda_cuti_pegawai':self.cek_sisa_tunda_cuti(user),
            'cek_total_cuti_tahunan': self.cek_total_cuti_termasuk_sedang_proses(user),
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
        riwayat_instance = None
        layanan_instance = self.get_object(id)
        verifikasi_cuti = self.get_verification_object(id)
        id_riwayat = None
        if layanan_instance is not None:
            id_riwayat = layanan_instance.cuti.id if hasattr(layanan_instance, 'cuti') else None
        riwayat_existing = self.get_riwayat_object(id_riwayat)
        riwayat_instance = self.get_riwayat_object(id_riwayat)
        riwayat_form = RiwayatPengajuanCutiForm(data=request.POST, files=request.FILES, instance=riwayat_instance, request=request, action='edit')
        form = update_pengajuan_cuti_formset(data=request.POST, files=request.FILES, instance=riwayat_instance)
        verifikator_form = VerifikatorCutiForm(data=request.POST, files=request.FILES, instance=verifikasi_cuti)
        if get_case == 'tindaklanjut':
            form = update_pengajuan_cuti_formset(data=request.POST, files=request.FILES, instance=riwayat_instance, form_kwargs={'case': 'tindaklanjut'})
            riwayat_form = RiwayatPengajuanCutiForm(data=request.POST, files=request.FILES, instance=riwayat_instance, request=request, case='tindaklanjut')
            if get_level == '1':
                verifikator_form = Verifikator1CutiForm(data=request.POST, files=request.FILES, instance=verifikasi_cuti)
            elif get_level == '2':
                verifikator_form = Verifikator2CutiForm(data=request.POST, files=request.FILES, instance=verifikasi_cuti)
            elif get_level == '3':
                verifikator_form = Verifikator3CutiForm(data=request.POST, files=request.FILES, instance=verifikasi_cuti)
        elif get_case == 'final':
            form = update_pengajuan_cuti_formset(data=request.POST, files=request.FILES, instance=riwayat_instance)
            riwayat_form = RiwayatCutiUploadSuratForm(data=request.POST, files=request.FILES, instance=riwayat_instance)
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
            data_riwayat = riwayat_form.save(commit=False)
            if data_riwayat.file_pengajuan and riwayat_existing.file_pengajuan and riwayat_existing.file_pengajuan != data_riwayat.file_pengajuan and os.path.exists(riwayat_existing.file_pengajuan.path):
                os.remove(riwayat_existing.file_pengajuan.path)
            if data_riwayat.file_pendukung and riwayat_existing.file_pendukung and riwayat_existing.file_pendukung != data_riwayat.file_pendukung and os.path.exists(riwayat_existing.file_pendukung.path):
                os.remove(riwayat_existing.file_pendukung.path)
            data_riwayat.save()
            for item in form:
                if item.is_valid():
                    data_usulan = item.save(commit=False)
                    data_status = ['tindaklanjut', 'selesai']
                    if get_case == 'tindaklanjut' and not any(data == layanan_instance.status for data in data_status):
                        data_usulan.status = form.cleaned_data[0].get('status')
                        if data_usulan.status == 'tidak ditindaklanjut':
                            data_riwayat.lama_cuti = 0
                            data_riwayat.save()
                    elif get_case == 'final':
                        data_usulan.status = 'selesai'
                    data_usulan.inovasi = data_riwayat
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
    
        
class LayananGajiBerkalaView(LoginRequiredMixin, GajiBerkalaCheck, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    redirect_display = 'layanan_urls:layanan_berkala_view'        
    def get(self, request, **kwargs):
        selected_nip = request.GET.get('nip')
        user = request.user
        layanan = JenisLayanan.objects.filter(url='yanberkala')
        data_berkala = LayananGajiBerkala.objects.all()
        initial = {'layanan':layanan.first(), 'status':'belum', 'status_cuti':'Proses'}
        nip = None
        if not user.is_superuser:
            nip = get_nip(user)
            if nip:
                initial = {'pegawai':user, 'layanan':layanan.first(), 'status':'belum', 'status_cuti':'Proses'}
                data_berkala = LayananGajiBerkala.objects.filter(pegawai__profil_user__nip=nip)
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'layanan', 'selected':'yanberkala'}))
        if selected_nip:
            nip = selected_nip
            data_berkala = LayananGajiBerkala.objects.filter(pegawai__profil_user__nip=nip)
        form = FormLayananBerkala(initial=initial, request=request)
        context={
            'nip':nip,
            'status_berkala':self.check_status(nip),
            'next_berkala':self.next_berkala(nip),
            'form':form,
            'data':data_berkala,
            'form_view':'none',
            'data_view':'block',
            'layanan':'active',
            'title_page':'Layanan Gaji Berkala',
            'selected':'yanberkala',
        }
        return render(request, '3_layanan_berkala/layanan_berkala_master.html', context)
    
    def post(self, request):
        form = FormLayananBerkala(data=request.POST, files=request.FILES, request=request)
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
        

class LayananGajiBerkalaAPIView(APIView):
    def get_object(self, id):
        try: 
            layanan = LayananGajiBerkala.objects.get(id=id)
            return layanan
        except Exception:
            return None
        
    def get(self, request, **kwargs):
        data_id = kwargs.get('id')
        data = self.get_object(data_id)
        serializer = LayananGajiBerkalaSerializer(data)
        return Response(serializer.data)
    
    def post(self, request, **kwargs):
        data_id = kwargs.get('id')
        instance = self.get_object(data_id)
        serializer = LayananGajiBerkalaSerializer(data=request.POST, instance=instance, partial=True)
        if serializer.is_valid():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    

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
            berkala = form.save()
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
        form = RiwayatGajiBerkalaForm(instance=instance, status=status_post)
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
        form = RiwayatGajiBerkalaForm(data=request.POST, files=request.FILES, status=status_post, instance=instance)
        layanan = LayananGajiBerkala.objects.filter(id=layanan_id)
        url_reverse = reverse('layanan_urls:layanan_berkala_admin_view', kwargs={"layanan_id":layanan_id, "nip":nip})
        if form.is_valid():
            data_submitted = form.save(commit=False)
            if data_submitted.file:
                if berkala_existing.file is not None and berkala_existing.file != data_submitted.file and os.path.exists(berkala_existing.file.path):
                    os.remove(berkala_existing.file.path)
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

