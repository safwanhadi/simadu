from django.db.models import Q, Count, F, Case, When, Sum
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, DetailView, DeleteView, UpdateView, CreateView
# from rest_framework.views import 
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.storage import default_storage
from django.db import transaction
# from django.utils.text import slugify
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from itertools import chain, zip_longest
from functools import lru_cache
import os

from layanan.views import GajiBerkalaCheck, CheckCuti
from layanan.models import (
    JenisLayanan
)
from .models import (
    DokumenSDM,
    RiwayatPendidikan, 
    RiwayatPanggol,
    RiwayatPengangkatan,
    RiwayatBekerja,
    RiwayatPenempatan,
    RiwayatProfesi,
    RiwayatSIPProfesi,
    RiwayatJabatan,
    UjiKompetensi,
    Kompetensi,
    RiwayatGajiBerkala,
    RiwayatKinerja,
    RiwayatOrganisasi,
    RiwayatDiklat,
    RiwayatCuti,
    RiwayatHukuman,
    RiwayatPenghargaan,
    RiwayatKeluarga,
    OrangTua,
    Pasangan,
    Anak,
    RiwayatInovasi,
    RiwayatPenugasan
    )
from myaccount.models import ProfilSDM, Users
from .forms import (
    RiwayatPendidikanForm,
    UrutkanDokumenSDMForm,
    urutkan_dokumen_pendidikan,
    RiwayatPanggolForm,
    urutkan_dokumen_panggol,
    RiwayatJabatanForm,
    urutkan_dokumen_jabatan,
    KompetensiForm,
    urutkan_dokumen_kompetensi,
    RiwayatPengangkatanForm,
    urutkan_dokumen_pengangkatan,
    RiwayatPenempatanForm,
    urutkan_dokumen_penempatan,
    RiwayatPenempatanLainnyaForm,
    RiwayatGajiBerkalaForm,
    urutkan_dokumen_berkala,
    RiwayatKinerjaForm,
    urutkan_dokumen_kinerja,
    RiwayatPenghargaanForm,
    urutkan_dokumen_penghargaan,
    RiwayatHukumanForm,
    urutkan_dokumen_hukuman,
    RiwayatCutiForm,
    urutkan_dokumen_cuti,
    RiwayatOrganisasiForm,
    urutkan_dokumen_organisasi,
    UrutkanRiwayatProfesiForm,
    RiwayatProfesiForm,
    urutkan_dokumen_profesi,
    RiwayatSIPProfesiForm,
    urutkan_dokumen_sip,
    profesi_formset,
    profesi_update_formset,
    RiwayatBekerjaForm,
    urutkan_dokumen_bekerja,
    RiwayatKeluargaForm,
    RiwayatKeluargaPasanganForm,
    RiwayatKeluargaOrangTuaForm,
    RiwayatKeluargaAnakForm,
    urutkan_dokumen_keluarga,
    UjiKompetensiForm,
    RiwayatDiklatForm,
    urutkan_dokumen_diklat,
    urutkan_dokumen_inovasi,
    RiwayatPenugasanForm,
    urutkan_dokumen_penugasan
)

# Create your views here.

class NotFoundPage(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        bagian = kwargs.get('bagian')
        selected = kwargs.get('selected')
        if bagian == 'riwayat':
            context = {
                'riwayat':'active',
                'selected':selected
            }
        else:
            context = {
                'layanan':'active',
                'selected':selected
            }
        return render(request, 'riwayat_404.html', context)
    

def file_kepegawaian(request, nip):
    data = None
    if request.user.is_superuser:
        profil = ProfilSDM.objects.filter(nip=nip).last()
        pendidikan = RiwayatPendidikan.objects.filter(pegawai__profil_user__nip=nip).last()
        panggol = RiwayatPanggol.objects.filter(pegawai__profil_user__nip=nip).last()
        jabatan = RiwayatJabatan.objects.filter(pegawai__profil_user__nip=nip).last()
        pengangkatan_cpns = RiwayatPengangkatan.objects.filter(pegawai__profil_user__nip=nip, status_pegawai='CPNS').last()
        pengangkatan = RiwayatPengangkatan.objects.filter(pegawai__profil_user__nip=nip).last()
        penempatan = RiwayatPenempatan.objects.filter(pegawai__profil_user__nip=nip).last()
        berkala = RiwayatGajiBerkala.objects.filter(pegawai__profil_user__nip=nip).last()
        kinerja = RiwayatKinerja.objects.filter(pegawai__profil_user__nip=nip).last()
        penghargaan = RiwayatPenghargaan.objects.filter(pegawai__profil_user__nip=nip).last()
        hukuman = RiwayatHukuman.objects.filter(pegawai__profil_user__nip=nip).last()
        cuti = RiwayatCuti.objects.filter(pegawai__profil_user__nip=nip).last()
        diklat = RiwayatDiklat.objects.filter(pegawai__profil_user__nip=nip).last()
        organisasi = RiwayatOrganisasi.objects.filter(pegawai__profil_user__nip=nip).last()
        profesi = RiwayatProfesi.objects.filter(pegawai__profil_user__nip=nip).last()
        bekerja = RiwayatBekerja.objects.filter(pegawai__profil_user__nip=nip).last()
        keluarga = RiwayatKeluarga.objects.filter(pegawai__profil_user__nip=nip).last()
        data = {'profil':profil,
                'pendidikan':pendidikan, 
                'panggol':panggol, 
                'jabatan':jabatan, 
                'pengangkatan_cpns':pengangkatan_cpns, 
                'pengangkatan':pengangkatan, 
                'penempatan':penempatan, 
                'berkala':berkala, 
                'kinerja':kinerja, 
                'penghargaan':penghargaan, 
                'hukuman':hukuman, 
                'cuti':cuti, 
                'diklat':diklat, 
                'organisasi':organisasi, 
                'profesi':profesi, 
                'bekerja':bekerja, 
                'keluarga':keluarga}
        return data
    else:
        profil = ProfilSDM.objects.filter(user=request.user).last()
        pendidikan = RiwayatPendidikan.objects.filter(pegawai=request.user).last()
        panggol = RiwayatPanggol.objects.filter(pegawai=request.user).last()
        jabatan = RiwayatJabatan.objects.filter(pegawai=request.user).last()
        pengangkatan_cpns = RiwayatPengangkatan.objects.filter(pegawai=request.user, status_pegawai='CPNS').last()
        pengangkatan = RiwayatPengangkatan.objects.filter(pegawai=request.user).last()
        penempatan = RiwayatPenempatan.objects.filter(pegawai=request.user).last()
        berkala = RiwayatGajiBerkala.objects.filter(pegawai=request.user).last()
        kinerja = RiwayatKinerja.objects.filter(pegawai=request.user).last()
        penghargaan = RiwayatPenghargaan.objects.filter(pegawai=request.user).last()
        hukuman = RiwayatHukuman.objects.filter(pegawai=request.user).last()
        cuti = RiwayatCuti.objects.filter(pegawai=request.user).last()
        diklat = RiwayatDiklat.objects.filter(pegawai=request.user).last()
        organisasi = RiwayatOrganisasi.objects.filter(pegawai=request.user).last()
        profesi = RiwayatProfesi.objects.filter(pegawai=request.user).last()
        bekerja = RiwayatBekerja.objects.filter(pegawai=request.user).last()
        keluarga = RiwayatKeluarga.objects.filter(pegawai=request.user).last()
        data = {'profil':profil,
                'pendidikan':pendidikan, 
                'panggol':panggol, 
                'jabatan':jabatan, 
                'pengangkatan_cpns':pengangkatan_cpns, 
                'pengangkatan':pengangkatan, 
                'penempatan':penempatan, 
                'berkala':berkala, 
                'kinerja':kinerja, 
                'penghargaan':penghargaan, 
                'hukuman':hukuman, 
                'cuti':cuti, 
                'diklat':diklat, 
                'organisasi':organisasi, 
                'profesi':profesi, 
                'bekerja':bekerja, 
                'keluarga':keluarga}
        return data


def cek_dokumen(nip):
    data = []
    user = Users.objects.filter(profil_user__nip=nip).last()
    riwayat_pengangkatan = user.riwayatpengangkatan_set.last() if hasattr(user, 'riwayatpengangkatan_set') else None
    status_pegawai = riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else None
    pendidikan = RiwayatPendidikan.objects.filter(pegawai__profil_user__nip=nip).last()
    if pendidikan is not None and pendidikan.file_ijazah and pendidikan.file_transkrip:
        data.append({'dokumen':pendidikan.dokumen, 'pegawai':pendidikan.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
    else:
        data.append({'dokumen':'pendidikan', 'pegawai':nip, 'status':'kosong'})
    if status_pegawai == 'PNS':
        panggol = RiwayatPanggol.objects.filter(pegawai__profil_user__nip=nip, pegawai__riwayatpengangkatan__status_pegawai='PNS').last()
        if panggol is not None and panggol.file:
            data.append({'dokumen':panggol.dokumen, 'pegawai':panggol.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
        else:
            data.append({'dokumen':'panggol', 'pegawai':nip, 'status':'kosong'})
        berkala = RiwayatGajiBerkala.objects.filter(pegawai__profil_user__nip=nip, pegawai__riwayatpengangkatan__status_pegawai='PNS').last()
        if berkala is not None and berkala.file:
            data.append({'dokumen':berkala.dokumen, 'pegawai':berkala.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
        else:
            data.append({'dokumen':'berkala', 'pegawai':nip, 'status':'kosong'})
        kinerja = RiwayatKinerja.objects.filter(pegawai__profil_user__nip=nip, pegawai__riwayatpengangkatan__status_pegawai='PNS').last()
        if kinerja is not None and kinerja.file:
            data.append({'dokumen':kinerja.dokumen, 'pegawai':kinerja.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
        else:
            data.append({'dokumen':'kinerja', 'pegawai':nip, 'status':'kosong'})
    jabatan = RiwayatJabatan.objects.filter(pegawai__profil_user__nip=nip).last()
    if jabatan is not None and jabatan.file:
        data.append({'dokumen':jabatan.dokumen, 'pegawai':jabatan.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
    else:
        data.append({'dokumen':'jabatan', 'pegawai':nip, 'status':'kosong'})
    pengangkatan = RiwayatPengangkatan.objects.filter(pegawai__profil_user__nip=nip).last()
    if pengangkatan is not None and pengangkatan.file_sk:
        data.append({'dokumen':pengangkatan.dokumen, 'pegawai':pengangkatan.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
    else:
        data.append({'dokumen':'pengangkatan', 'pegawai':nip, 'status':'kosong'})
    penempatan = RiwayatPenempatan.objects.filter(pegawai__profil_user__nip=nip).last()
    if penempatan is not None and penempatan.file:
        data.append({'dokumen':penempatan.dokumen, 'pegawai':penempatan.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
    else:
        data.append({'dokumen':'penempatan', 'pegawai':nip, 'status':'kosong'})
    penghargaan = RiwayatPenghargaan.objects.filter(pegawai__profil_user__nip=nip).last()
    if penghargaan is not None and penghargaan.file:
        data.append({'dokumen':penghargaan.dokumen, 'pegawai':penghargaan.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
    else:
        data.append({'dokumen':'penghargaan', 'pegawai':nip, 'status':'kosong'})
    diklat = RiwayatDiklat.objects.filter(pegawai__profil_user__nip=nip).last()
    if diklat is not None and diklat.file:
        data.append({'dokumen':diklat.dokumen, 'pegawai':diklat.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
    else:
        data.append({'dokumen':'diklat', 'pegawai':nip, 'status':'kosong'})
    organisasi = RiwayatOrganisasi.objects.filter(pegawai__profil_user__nip=nip).last()
    if organisasi is not None and organisasi.file:
        data.append({'dokumen':organisasi.dokumen, 'pegawai':organisasi.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
    else:
        data.append({'dokumen':'organisasi', 'pegawai':nip, 'status':'kosong'})
    profesi = RiwayatProfesi.objects.filter(pegawai__profil_user__nip=nip).last()
    if profesi is not None and profesi.file_str:
        data.append({'dokumen':profesi.dokumen, 'pegawai':profesi.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
    else:
        data.append({'dokumen':'profesi', 'pegawai':nip, 'status':'kosong'})
    bekerja = RiwayatBekerja.objects.filter(pegawai__profil_user__nip=nip).last()
    if bekerja is not None and bekerja.file:
        data.append({'dokumen':bekerja.dokumen, 'pegawai':bekerja.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
    else:
        data.append({'dokumen':'bekerja', 'pegawai':nip, 'status':'kosong'})
    keluarga = RiwayatKeluarga.objects.filter(pegawai__profil_user__nip=nip).last()
    if keluarga is not None and keluarga.file:
        data.append({'dokumen':keluarga.dokumen, 'pegawai':keluarga.pegawai, 'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else '', 'status':'terisi'})
    else:
        data.append({'dokumen':'keluarga', 'pegawai':nip, 'status':'kosong'})
    return data

def cek_kelengkapan_user(nip):
    # kelengkapan_list_comp = [item for item in cek_dokumen(nip) if item['pegawai'].profil_user.nip == nip]
    kelengkapan = []
    for item in cek_dokumen(nip):
        if item['pegawai'] == nip:
            user = Users.objects.filter(profil_user__nip=item['pegawai']).last()
            riwayat_pengangkatan = user.riwayatpengangkatan_set.last() if hasattr(user, 'riwayatpengangkatan_set') else None
            status_pegawai = {'status_pegawai':riwayat_pengangkatan.status_pegawai if hasattr(riwayat_pengangkatan, 'status_pegawai') else ''}
            item['pegawai'] = user
            item.update(status_pegawai)
            kelengkapan.append(item)
        elif item['pegawai'].profil_user.nip == nip:
            kelengkapan.append(item)
    return kelengkapan

def cek_kelengkapan():
    users = Users.objects.all().exclude(is_superuser=True)
    kelengkapan_user = []
    for user in users:
        kelengkapan = cek_dokumen(user.profil_user.nip if hasattr(user, 'profil_user') else user)
        data = [{'dokumen':item['dokumen'], 'user':item['pegawai']} for item in kelengkapan if isinstance(item['dokumen'], str)]
        if len(data) != 0:
            data_len = len(data)-1
            if isinstance(data[data_len]['user'], str):
                datauser = users.filter(profil_user__nip=data[0]['user']).last()
                data[0]['user'] = datauser
                kelengkapan_user.append(data[0])
    return kelengkapan_user
    
# start = time.time()
class RiwayatHomeView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        nip = request.GET.get('nip')
        if nip:
            user = nip
        jenis_dok = DokumenSDM.objects.all().order_by('id')
        jabatan = 'fungsional'
        file_kepeg = file_kepegawaian(request, user)
        data_peg = Users.objects.all().exclude(is_superuser=True)
        context={
            'nip':nip,
            'data_peg':data_peg,
            'file_kepeg':file_kepeg,
            'jabatan':jabatan,
            'jenis_dok':jenis_dok,
            'riwayat':'active',
            'page':'Riwayat',
            'selected':'riwayat',
            'title_page':'Menu'
        }
        return render(request, 'riwayat_home.html', context)

class RiwayatKelengkapan(LoginRequiredMixin, View):
    def get(self, request):
        data_peg = Users.objects.all().exclude(is_superuser=True)
        get_nip_user = request.GET.get('nip')
        user = request.user
        nip = get_nip(user)
        if get_nip_user is not None:
            nip = get_nip_user
        kelengkapan = None
        if not request.user.is_superuser or get_nip_user:
            nip = nip
            kelengkapan = cek_kelengkapan_user(nip)
        elif request.user.is_superuser:
            kelengkapan = cek_kelengkapan()
        context={
            'nip':get_nip_user,
            'data_peg':data_peg,
            'kelengkapan':kelengkapan,
            'riwayat':'active',
            'page':'Riwayat',
            'selected':'kelengkapan',
            'title_page':'Kelengkapan'
        }
        return render(request, 'kelengkapan.html', context)


def get_user(user):
    try:
        user = ProfilSDM.objects.get(user = user)
        return user.nip
    except ProfilSDM.DoesNotExist:
        # messages.error(request, 'Maaf data profil anda belum diupdate!')
        return None
    
def get_user_bynip(nip):
    try:
        user = ProfilSDM.objects.get(nip=nip)
        user = user.user
        return user
    except ProfilSDM.DoesNotExist:
        return None 
    
def get_nip(user):
    try:
        nip = user.profil_user.nip
        return nip
    except Exception:
        return None
    
notfoundview = 'riwayat_urls:notfound_view'
save_success_message = "Data berhasi disimpan!"
form_not_valid_message = "Maaf pengisian form tidak valid"

class UrutkanRiwayatPendidikanView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '1_riwayat_pendidikan/riwayat_pendidikan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_pendidikan')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_pendidikan(self.request.POST, instance=self.object)
        else:
            urutkan_dokumen_form = urutkan_dokumen_pendidikan(instance=self.object, queryset=self.object.riwayatpendidikan_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatPendidikanView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Pendidikan',
            'riwayat':'active',
            'selected':'pendidikan',
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)
        

class RiwayatPendidikanView(LoginRequiredMixin, View):   
    def get(self, request):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatPendidikan.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(nama='Riwayat Pendidikan')
        initial = {'dokumen':dok.first()}
        nip = None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok.first()}
            if nip:
                data = RiwayatPendidikan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'pendidikan'}))
        if selected_nip:
            nip = selected_nip
            user = get_user_bynip(nip)
            data = RiwayatPendidikan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatPendidikanForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Pendidikan',
            'nip':nip,
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'pendidikan',
        }
        return render(request, '1_riwayat_pendidikan/riwayat_pendidikan_master.html', context)

    def post(self, request):
        form = RiwayatPendidikanForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_pendidikan'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_pendidikan'))


class RiwayatPendidikanUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatPendidikan.objects.get(id=id)
            return data
        except RiwayatPendidikan.DoesNotExist:
            messages.error(request, 'Maaf data tidak ditemukan!')
            return None
    
    def get(self, request, **kwargs):
        id = kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='pendidikan')
        detail = self.get_object(id, request=request)
        form = RiwayatPendidikanForm(instance=detail, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Pendidikan',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
        }
        return render(request, '1_riwayat_pendidikan/riwayat_pendidikan_master.html', context)

    def post(self, request, **kwargs):
        id = kwargs.get('id')
        #data detail digunakan menjadi data statis yang tidak terpengaruh dengan isian form input
        data_detail = self.get_object(id)
        #data instance akan berubah mengikuti isian form input
        instance = self.get_object(id)
        form = RiwayatPendidikanForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_pendidikan = form.save(commit=False)
            if riwayat_pendidikan.file_srt_penyetaraan and data_detail.file_srt_penyetaraan and riwayat_pendidikan.file_srt_penyetaraan != data_detail.file_srt_penyetaraan and os.path.isfile(data_detail.file_srt_penyetaraan.path):
                os.remove(data_detail.file_srt_penyetaraan.path)
            if riwayat_pendidikan.file_ijazah and data_detail.file_ijazah and riwayat_pendidikan.file_ijazah != data_detail.file_ijazah and os.path.isfile(data_detail.file_ijazah.path):
                os.remove(data_detail.file_ijazah.path)
            if riwayat_pendidikan.file_transkrip and data_detail.file_transkrip and riwayat_pendidikan.file_transkrip != data_detail.file_transkrip and os.path.isfile(data_detail.file_transkrip.path):
                os.remove(data_detail.file_transkrip.path)
            riwayat_pendidikan.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_pendidikan'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_update_pendidikan', kwargs={'id':id}))


class RiwayatPendidikanDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatPendidikan
    template_name = '1_riwayat_pendidikan/riwayat_pendidikan_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_pendidikan')
    success_message = 'Data berhasil dihapus!'

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='pendidikan')
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatPendidikan.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatPendidikan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatPendidikanDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Pendidikan',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'pendidikan',
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file_ijazah:
            if os.path.isfile(self.object.file_ijazah.path):
                os.remove(self.object.file_ijazah.path)
        if self.object.file_transkrip:
            if os.path.isfile(self.object.file_transkrip.path):
                os.remove(self.object.file_transkrip.path)
        return super().form_valid(form)


class CheckRiwayatPanggol:
    def get_four_year_before(self, start_year) -> dict:
        end_year = start_year - relativedelta(months=22)
        date_interval = relativedelta(end_year, start_year)
        return {
            'interval_tahun': date_interval.years,
            'interval_bulan': date_interval.months
            }
    def get_four_year_after(self, start_year):
        today = date.today()
        date_interval = relativedelta(today, start_year)
        #convert tahun ke bulan
        interval_year = date_interval.years * 12
        interval_month = date_interval.months
        interval = interval_year + interval_month
        return {
            'interval': interval,
            'interval_year': date_interval.years,
            'interval_month': date_interval.months
            } 
    
    def check_status(self, nip) -> bool:
        data = RiwayatPanggol.objects.filter(pegawai__profil_user__nip=nip).values('tmt_gol').last()
        get_periode = DokumenSDM.objects.get(url='panggol')
        try:
            status = None
            if self.get_four_year_after(data.get('tmt_gol')).get('interval') >= get_periode.periode_min:
                status = True
            else:
                status = False
            # if statement with one line = True if self.get_two_year_after(data.get('tgl_srt_gaji')).get('interval_tahun') >= 1 and self.get_two_year_after(data.get('tgl_srt_gaji')).get('interval_bulan') >= 9 else False
            return status
        except Exception:
            return True
    
    def next_panggol(self, nip) -> date:
        data = RiwayatPanggol.objects.filter(pegawai__profil_user__nip=nip).values('tmt_gol')
        interval_date = DokumenSDM.objects.get(url='panggol')
        second_last_date = data.order_by('-tmt_gol')
        if nip and len(second_last_date) >= 2:
            #jika TMT data pertama kosong akan tereksekusi data sebelumnya
            if second_last_date[0].get('tmt_gol') is not None:
                data1 = second_last_date[0].get('tmt_gol')+relativedelta(months=interval_date.periode_max)
                return data1
            data2 = second_last_date[1].get('tmt_gol')+relativedelta(months=interval_date.periode_max)
            return data2
        elif nip and len(second_last_date) == 1:
            data3 = second_last_date[0].get('tmt_gol')+relativedelta(months=interval_date.periode_max)
            return data3
        return None

    
template_panggol = 'riwayat_panggol/riwayat_panggol_master.html'

class RiwayatPanggolView(LoginRequiredMixin, CheckRiwayatPanggol, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_user(self, id):
        try:
            data = Users.objects.get(id=id)
            return data
        except Users.DoesNotExist:
            return None
        
    def get(self, request):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatPanggol.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='panggol')
        initial = {'dokumen':dok.first()}
        nip = None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok.first()}
            if nip:
                data = RiwayatPanggol.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'panggol'}))
            
        if selected_nip:
            nip = selected_nip
            data = RiwayatPanggol.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatPanggolForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'status_panggol':self.check_status(nip),
            'next_panggol':self.next_panggol(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Panggol',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'panggol'
        }
        return render(request, '2_riwayat_panggol/riwayat_panggol_master.html', context)
    
    def post(self, request):
        form = RiwayatPanggolForm(data=request.POST, files=request.FILES, request=request)
        pegawai = form.data.get('pegawai')
        user = request.user
        selected_nip = request.GET.get('nip')
        nip = None
        if not request.user.is_superuser:
            nip = get_nip(user)
                      
        if request.user.is_superuser and selected_nip:
            nip = selected_nip
        else:
            user = self.get_user(pegawai)
            nip = get_nip(user)

        if form.is_valid():
            if self.check_status(nip):
                form.save()
                messages.success(request, save_success_message)
                return redirect(reverse('riwayat_urls:riwayat_panggol'))
            else:
                messages.warning(request, 'Anda belum saatnya naik pangkat!')
                return redirect(reverse('riwayat_urls:riwayat_panggol'))
            
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_panggol'))


class RiwayatPanggolUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data= RiwayatPanggol.objects.get(id=id)
            return data
        except RiwayatPanggol.DoesNotExist:
            messages.error(request, f'Maaf data dengan id "{id}" tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        id=kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='panggol')
        detail = self.get_object(id, request=request)
        form = RiwayatPanggolForm(instance=detail, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Panggol',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'panggol'
        }
        return render(request, '2_riwayat_panggol/riwayat_panggol_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        form = RiwayatPanggolForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_panggol = form.save(commit=False)
            if riwayat_panggol.file and data_detail.file and data_detail.file != riwayat_panggol.file and os.path.isfile(data_detail.file.path):
                os.remove(data_detail.file.path)
            riwayat_panggol.save()
            # form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_panggol'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_panggol'))


class UrutkanRiwayatPanggolView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '2_riwayat_panggol/riwayat_panggol_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_panggol')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        user = self.request.user
        if nip:
            user = get_user_bynip(nip)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_panggol(self.request.POST, instance=self.object)
        else:
            if self.request.user.is_superuser:
                urutkan_dokumen_form = urutkan_dokumen_panggol(instance=self.object, queryset=self.object.riwayatpanggol_set.filter(pegawai__profil_user__nip=nip))
            else:
                urutkan_dokumen_form = urutkan_dokumen_panggol(instance=self.object, queryset=self.object.riwayatpanggol_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatPanggolView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user':user,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Panggol',
            'riwayat':'active',
            'selected':'panggol'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)


class RiwayatPanggolDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatPanggol
    template_name = '2_riwayat_panggol/riwayat_panggol_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_panggol')
    success_message = 'Data berhasil dihapus!'

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='panggol')
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatPanggol.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatPanggol.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatPanggolDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Panggol',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'panggol'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        return super().form_valid(form)


class RiwayatUjiKomView(LoginRequiredMixin, View):
    def get_user(self, id):
        try:
            data = Users.objects.get(id=id)
            return data
        except Users.DoesNotExist:
            return None
        
    def get(self, request):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = UjiKompetensi.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='ujikomp')
        initial = {'dokumen':dok.first()}
        nip = None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok.first()}
            if nip:
                data = UjiKompetensi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'ujikomp'}))
        if selected_nip:
            nip = selected_nip
            data = UjiKompetensi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = UjiKompetensiForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'status_panggol':self.check_status(nip),
            'next_panggol':self.next_panggol(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Panggol',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'ujikomp'
        }
        return render(request, '2_riwayat_panggol/riwayat_panggol_master.html', context)
    
    def post(self, request):
        form = UjiKompetensiForm(request.POST, request.FILES, request=request)
        pegawai = form.data.get('pegawai')
        user = request.user
        selected_nip = request.GET.get('nip')
        nip = None
        if not request.user.is_superuser:
            nip = get_nip(user)
                      
        if request.user.is_superuser and selected_nip:
            nip = selected_nip
        else:
            user = self.get_user(pegawai)
            nip = get_nip(user)

        if form.is_valid():
            if self.check_status(nip):
                form.save()
                messages.success(request, save_success_message)
                return redirect(reverse('riwayat_urls:riwayat_panggol'))
            else:
                messages.warning(request, 'Anda belum saatnya naik pangkat!')
                return redirect(reverse('riwayat_urls:riwayat_panggol'))
            
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_panggol'))


class CheckRiwayatJabatan:
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
        data = RiwayatJabatan.objects.filter(pegawai__profil_user__nip=nip).values('tmt_jabatan').last()
        try:
            status = None
            if self.get_two_year_after(data.get('tmt_jabatan')).get('interval_tahun') >= 2:
                status = True
            elif self.get_two_year_after(data.get('tmt_jabatan')).get('interval_tahun') == 1 and self.get_two_year_after(data.get('tmt_jabatan')).get('interval_bulan') >= 9:
                status = True
            else:
                status = False
            # if statement with one line = True if self.get_two_year_after(data.get('tgl_srt_gaji')).get('interval_tahun') >= 1 and self.get_two_year_after(data.get('tgl_srt_gaji')).get('interval_bulan') >= 9 else False
            return status
        except Exception:
            return True
    
    def next_jabatan(self, nip) -> date:
        data = RiwayatJabatan.objects.filter(pegawai__profil_user__nip=nip).values('tmt_jabatan')
        second_last_date = data.order_by('-tmt_jabatan')
        if nip and len(second_last_date) >= 2:
            #jika TMT data pertama kosong akan tereksekusi data sebelumnya
            if second_last_date[0].get('tmt_jabatan') is not None:
                data1 = second_last_date[0].get('tmt_jabatan')+relativedelta(months=24)
                return data1
            data2 = second_last_date[1].get('tmt_jabatan')+relativedelta(months=24)
            return data2
        elif nip and len(second_last_date) == 1:
            data3 = second_last_date[0].get('tmt_jabatan')+relativedelta(months=24)
            return data3
        return None
        

class RiwayatJabatanView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_jabatan_object(self, user, request=None):
        try:
            data = RiwayatJabatan.objects.get(pegawai=user)
            return data
        except Exception:
            if request:
                messages.error(request, 'Maaf data riwayat jabatan tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        jabatan = request.GET.get('jabatan')
        get_form = request.GET.get('form')
        user = request.user
        form_view = 'none'
        data_view = 'block'
        if get_form:
            form_view = 'block'
            data_view = 'none'
        selected_nip = request.GET.get('nip')
        dok = DokumenSDM.objects.filter(url='jabatan')
        initial = {'dokumen':dok.first()}
        data = RiwayatJabatan.objects.all().order_by('no_urut_dokumen').exclude(pegawai__is_superuser=True)
        if jabatan is not None:
            data = RiwayatJabatan.objects.filter(jns_jabatan__icontains=jabatan).exclude(pegawai__is_superuser=True)
        nip = None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok.first()}
            if nip:
                data = RiwayatJabatan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'jabatan'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatJabatan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form_detail = RiwayatJabatanForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'jabatan':jabatan,
            'data':data,
            'form':form_detail,
            'nip':nip,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Jabatan',
            'form_view':form_view,
            'data_view':data_view,
            'riwayat':'active',
            'selected':'jabatan'
        }
        return render(request, '3_riwayat_jabatan/riwayat_jabatan_master.html', context)
    
    def post(self, request, *args, **kwargs):
        jabatan = request.GET.get('jabatan')
        form_detail = RiwayatJabatanForm(data=request.POST, files=request.FILES, request=request)
        if form_detail.is_valid():
            form_detail.save()
            messages.success(request, save_success_message)
            return redirect(f"{reverse('riwayat_urls:riwayat_jabatan')}?jabatan={jabatan}")
        else:
            messages.error(request, form_not_valid_message)
            return redirect(f"{reverse('riwayat_urls:riwayat_jabatan')}?jabatan={jabatan}")


class RiwayatJabatanUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatJabatan.objects.get(id=id)
            return data
        except RiwayatJabatan.DoesNotExist:
            messages.error(request, f'Maaf data pegawai tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        id = kwargs.get('id')
        jabatan = kwargs.get('jabatan')
        selected_nip = request.GET.get('nip')
        dok = DokumenSDM.objects.filter(url='jabatan')
        if request.user.is_superuser:
            nip = selected_nip
        detail_jabatan = self.get_object(id, request)
        form = RiwayatJabatanForm(instance=detail_jabatan, request=request)

        context={
            'update_form':True,
            'jabatan':jabatan,
            'form':form,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Jabatan',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'jabatan'
        }
        return render(request, '3_riwayat_jabatan/riwayat_jabatan_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        jabatan = kwargs.get('jabatan')
        riwayat = self.get_object(id, request)
        instance = self.get_object(id, request)
        form = RiwayatJabatanForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            data_jabatan = form.save(commit=False)
            if data_jabatan.file and riwayat.file and data_jabatan.file != riwayat.file and os.path.isfile(riwayat.file.path):
                os.remove(riwayat.file.path)
            if data_jabatan.file_pemberhentian and riwayat.file_pemberhentian and data_jabatan.file_pemberhentian != riwayat.file_pemberhentian and os.path.isfile(riwayat.file_pemberhentian.path):
                os.remove(riwayat.file_pemberhentian.path)
            data_jabatan.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_jabatan'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_jabatan'))


class UrutkanRiwayatJabatanView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '3_riwayat_jabatan/riwayat_jabatan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_jabatan')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_jabatan(self.request.POST, instance=self.object)
        else:
            urutkan_dokumen_form = urutkan_dokumen_jabatan(instance=self.object, queryset=self.object.riwayatjabatan_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatJabatanView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Jabatan',
            'riwayat':'active',
            'selected':'jabatan'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)


class RiwayatJabatanDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatJabatan
    template_name = '3_riwayat_jabatan/riwayat_jabatan_master.html'
    success_message = 'Data berhasil dihapus!'

    def get_success_url(self) -> str:
        jabatan = self.request.GET.get('jabatan')
        return f"{reverse_lazy('riwayat_urls:riwayat_jabatan')}?jabatan={jabatan}"

    def get_context_data(self, **kwargs):
        jabatan = self.request.GET.get('jabatan')
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='jabatan')
        nip = None
        if self.request.user.is_superuser and jabatan:
            data = RiwayatJabatan.objects.filter(jns_jabatan__icontains=jabatan).order_by('no_urut_dokumen')
        elif self.request.user.is_superuser:
            data = RiwayatJabatan.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatJabatan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatJabatanDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Jabatan',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'jabatan'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        if self.object.file_pemberhentian:
            if os.path.isfile(self.object.file_pemberhentian.path):
                os.remove(self.object.file_pemberhentian.path)
        return super().form_valid(form)
    

class RiwayatPengangkatanView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatPengangkatan.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='pengangkatan')
        initial = {'dokumen':dok.first()}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok.first()}
            if nip:
                data = RiwayatPengangkatan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'pengangkatan'}))
        
        if selected_nip:
            nip = selected_nip        
            data = RiwayatPengangkatan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatPengangkatanForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Pengangkatan',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'pengangkatan'
        }
        return render(request, '4_riwayat_pengangkatan/riwayat_pengangkatan_master.html', context)
    
    def post(self, request):
        form = RiwayatPengangkatanForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_pengangkatan'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_pengangkatan'))
    

class RiwayatPengangkatanUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatPengangkatan.objects.get(id=id)
            return data
        except RiwayatPengangkatan.DoesNotExist:
            messages.error(request, 'Maaf data tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        id = kwargs.get('id')
        detail = self.get_object(id, request)
        dok = DokumenSDM.objects.filter(url='pengangkatan')
        form = RiwayatPengangkatanForm(instance=detail, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Pengangkatan',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'pengangkatan'
        }
        return render(request, '4_riwayat_pengangkatan/riwayat_pengangkatan_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        data_detail = self.get_object(id, request)
        instance = self.get_object(id, request)
        form = RiwayatPengangkatanForm(request.POST, request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_pengangkatan = form.save(commit=False)
            if riwayat_pengangkatan.file_karpeg and data_detail.file_karpeg and data_detail.file_karpeg != riwayat_pengangkatan.file_karpeg and os.path.isfile(data_detail.file_karpeg.path):
                os.remove(data_detail.file_karpeg.path)
            if riwayat_pengangkatan.file_sk and data_detail.file_sk and data_detail.file_sk != riwayat_pengangkatan.file_sk and os.path.isfile(data_detail.file_sk.path):
                os.remove(data_detail.file_sk.path)
            if riwayat_pengangkatan.file_latsar and data_detail.file_latsar and data_detail.file_latsar != riwayat_pengangkatan.file_latsar and os.path.isfile(data_detail.file_latsar.path):
                os.remove(data_detail.file_latsar.path)
            if riwayat_pengangkatan.file_spmt and data_detail.file_spmt and data_detail.file_spmt != riwayat_pengangkatan.file_spmt and os.path.isfile(data_detail.file_spmt.path):
                os.remove(data_detail.file_spmt.path)
            riwayat_pengangkatan.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_pengangkatan'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_pengangkatan'))


class UrutkanRiwayatPengangkatanView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '4_riwayat_pengangkatan/riwayat_pengangkatan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_pengangkatan')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_pengangkatan(self.request.POST, instance=self.object)
        else:
            urutkan_dokumen_form = urutkan_dokumen_pengangkatan(instance=self.object, queryset=self.object.riwayatpengangkatan_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatPengangkatanView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Pengangkatan',
            'riwayat':'active',
            'selected':'pengangkatan'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)


class RiwayatPengangkatanDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatPengangkatan
    template_name = '4_riwayat_pengangkatan/riwayat_pengangkatan_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_pengangkatan')
    success_message = 'Data berhasil dihapus!'

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='pengangkatan')
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatPengangkatan.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatPengangkatan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatPengangkatanDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Pengangkatan',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'pengangkatan'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file_karpeg:
            if os.path.isfile(self.object.file_karpeg.path):
                os.remove(self.object.file_karpeg.path)
        if self.object.file_sk:
            if os.path.isfile(self.object.file_sk.path):
                os.remove(self.object.file_sk.path)
        if self.object.file_latsar:
            if os.path.isfile(self.object.file_latsar.path):
                os.remove(self.object.file_latsar.path)
        if self.object.file_spmt:
            if os.path.isfile(self.object.file_spmt.path):
                os.remove(self.object.file_spmt.path)
        return super().form_valid(form)
    

class RiwayatPenempatanView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id):
        try:
            data = RiwayatPenempatan.objects.get(id=id)
            return data
        except RiwayatPenempatan.DoesNotExist:
            return None

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        get_form = request.GET.get('f')
        get_id = kwargs.get('id')
        data = RiwayatPenempatan.objects.all().order_by('no_urut_dokumen').order_by('-status')
        dok = DokumenSDM.objects.filter(url='penempatan')
        initial = {'dokumen':dok.first()}
        form_view = 'none'
        data_view = 'block'
        if bool(get_form):
            form_view = 'block'
            data_view = 'none'
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok.first()}
            if nip:
                data = RiwayatPenempatan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen').order_by('-status')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'penempatan'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatPenempatan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen').order_by('-status')
        form = RiwayatPenempatanForm(initial=initial)
        update_form = False
        if get_id:
            update_form = True
            instance = self.get_object(get_id)
            form = RiwayatPenempatanForm(instance=instance)
        context={
            'update_form':update_form,
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'get_id':get_id,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penempatan',
            'form_view':form_view,
            'data_view':data_view,
            'riwayat':'active',
            'selected':'penempatan'
        }
        return render(request, '5_riwayat_penempatan/riwayat_penempatan_master.html', context)
    
    def post(self, request, **kwargs):
        get_id = kwargs.get('id')
        detail = self.get_object(get_id)
        instance = self.get_object(get_id)
        form = RiwayatPenempatanForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            riwayat_penempatan = form.save(commit=False)
            riwayat_penempatan.pegawai = form.cleaned_data.get('pegawai')
            if form.cleaned_data.get('status'):
                RiwayatPenempatan.objects.filter(pegawai=riwayat_penempatan.pegawai).update(status=False)
            if detail and riwayat_penempatan.file and detail.file and detail.file != riwayat_penempatan.file and os.path.isfile(detail.file.path):
                os.remove(detail.file.path)
            riwayat_penempatan.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_penempatan'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_penempatan'))
    

#Riwayat penempatan instansi sebelumnya
class RiwayatPenempatanInstansiBeforeCreateView(SuccessMessageMixin, CreateView):
    model = RiwayatPenempatan
    form_class = RiwayatPenempatanLainnyaForm
    template_name = '5_riwayat_penempatan/riwayat_penempatan_form_create_view.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penempatan')
    success_message = "Data berhasil disimpan!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['pegawai'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        dok = DokumenSDM.objects.filter(url='penempatan').first()
        if not self.request.user.is_superuser:
            initial['pegawai'] = self.request.user
        initial['dokumen'] = dok
        initial['status'] = False
        return initial

    def get_context_data(self, **kwargs):
        context = super(RiwayatPenempatanInstansiBeforeCreateView, self).get_context_data(**kwargs)
        context.update({
            'riwayat':'active',
            'selected':'penempatan',
        })
        return context


class RiwayatPenempatanInstansiBeforUpdateView(SuccessMessageMixin, UpdateView):
    model = RiwayatPenempatan
    form_class = RiwayatPenempatanLainnyaForm
    template_name = '5_riwayat_penempatan/riwayat_penempatan_form_create_view.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penempatan')
    success_message = "Data berhasil diupdate!"

    def form_valid(self, form):
        # Get the old file
        old_file = self.get_object().file
        # Save the new file
        response = super().form_valid(form)
        # Delete the old file if a new file has been uploaded
        if self.object.file != old_file:
            if default_storage.isfile(old_file.name):
                default_storage.delete(old_file.name)
        return response
    
    def get_context_data(self, **kwargs):
        context = super(RiwayatPenempatanInstansiBeforUpdateView, self).get_context_data(**kwargs)
        context.update({
            'riwayat':'active',
            'selected':'penempatan',
        })
        return context


class UrutkanRiwayatPenempatanView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '5_riwayat_penempatan/riwayat_penempatan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penempatan')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_penempatan(self.request.POST, instance=self.object)
        else:
            urutkan_dokumen_form = urutkan_dokumen_penempatan(instance=self.object, queryset=self.object.riwayatpenempatan_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatPenempatanView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penempatan',
            'riwayat':'active',
            'selected':'penempatan'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatPenempatanDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatPenempatan
    template_name = '5_riwayat_penempatan/riwayat_penempatan_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penempatan')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='penempatan')
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatPenempatan.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatPenempatan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatPenempatanDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penempatan',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'penempatan'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        return super().form_valid(form)
    

class RiwayatGajiBerkalaView(LoginRequiredMixin, GajiBerkalaCheck, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatGajiBerkala.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='berkala')
        initial = {'dokumen':dok.first()}
        nip=None
        if not request.user.is_superuser:
            nip = get_user(user)
            initial = {'pegawai':user, 'dokumen':dok.first()}
            if nip:
                data = RiwayatGajiBerkala.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'berkala'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatGajiBerkala.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatGajiBerkalaForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok.first(),
            'status_berkala':self.check_status(nip),
            'next_berkala':self.next_berkala(nip),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Gaji Berkala',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'berkala'
        }
        return render(request, '6_riwayat_berkala/riwayat_berkala_master.html', context)
    
    def post(self, request):
        form = RiwayatGajiBerkalaForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_berkala'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_berkala'))


class RiwayatGajiBerkalaUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatGajiBerkala.objects.get(id=id)
            return data
        except RiwayatGajiBerkala.DoesNotExist:
            messages.error(request, 'Maaf riwayat gaji berkala belum ada!')
            return None
        
    def get(self, request, **kwargs):
        id = kwargs.get('id')
        detail = self.get_object(id, request)
        dok = DokumenSDM.objects.filter(url='berkala')
        form = RiwayatGajiBerkalaForm(instance=detail, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Gaji Berkala',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'berkala'
        }
        return render(request, '6_riwayat_berkala/riwayat_berkala_master.html', context)
    
    def post(self, request, **kwargs):
        id=kwargs.get('id')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        form = RiwayatGajiBerkalaForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_berkala = form.save(commit=False)
            if riwayat_berkala.file and data_detail.file and data_detail.file != riwayat_berkala.file and os.path.isfile(data_detail.file.path):
                os.remove(data_detail.file.path)
            riwayat_berkala.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_berkala'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_berkala'))
   

class UrutkanRiwayatGajiBerkalaView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '6_riwayat_berkala/riwayat_berkala_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_berkala')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_berkala(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_berkala(instance=self.object, queryset=self.object.gaji_berkala.filter(pegawai__profil_user__nip=nip))
            else :
                urutkan_dokumen_form = urutkan_dokumen_berkala(instance=self.object, queryset=self.object.gaji_berkala.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatGajiBerkalaView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Berkala',
            'riwayat':'active',
            'selected':'berkala'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatGajiBerkalaDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatGajiBerkala
    template_name = '6_riwayat_berkala/riwayat_berkala_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_berkala')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='berkala')
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatGajiBerkala.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatGajiBerkala.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatGajiBerkalaDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok.first(),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Gaji Berkala',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'berkala'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        return super().form_valid(form)


class RiwayatKinerjaView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatKinerja.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='kinerja').first()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok}
            if nip:
                data = RiwayatKinerja.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'kinerja'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatKinerja.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatKinerjaForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Kinerja',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'kinerja'
        }
        return render(request, '7_riwayat_kinerja/riwayat_kinerja_master.html', context)
    
    def post(self, request):
        form = RiwayatKinerjaForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_kinerja'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_kinerja'))


class RiwayatKinerjaUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatKinerja.objects.get(id=id)
            return data
        except RiwayatKinerja.DoesNotExist:
            messages.error(request, 'Maaf data detail kinerja tidak ditemukan!')
            return None

    def get(self, request, **kwargs):
        id = kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='kinerja').first()
        instance = self.get_object(id, request)
        form = RiwayatKinerjaForm(instance=instance, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Kinerja',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'kinerja'
        }
        return render(request, '7_riwayat_kinerja/riwayat_kinerja_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        form = RiwayatKinerjaForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_kinerja = form.save(commit=False)
            if riwayat_kinerja.file and data_detail.file and data_detail.file != riwayat_kinerja.file and os.path.isfile(data_detail.file.path):
                os.remove(data_detail.file.path)
            riwayat_kinerja.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_kinerja'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_kinerja'))


class UrutkanRiwayatKinerjaView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '7_riwayat_kinerja/riwayat_kinerja_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_kinerja')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        context = super(UrutkanRiwayatKinerjaView, self).get_context_data(**kwargs)
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_kinerja(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_kinerja(instance=self.object, queryset=self.object.riwayatkinerja_set.filter(pegawai__profil_user__nip=nip))
            else:
                urutkan_dokumen_form = urutkan_dokumen_kinerja(instance=self.object, queryset=self.object.riwayatkinerja_set.filter(pegawai=self.request.user))
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Kinerja',
            'riwayat':'active',
            'selected':'kinerja'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)


class RiwayatKinerjaDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatKinerja
    template_name = '7_riwayat_kinerja/riwayat_kinerja_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_kinerja')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='kinerja').first()
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatKinerja.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatKinerja.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatKinerjaDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Kinerja',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'kinerja'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        return super().form_valid(form)
    

class RiwayatPenghargaanView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatPenghargaan.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='penghargaan').first()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok}
            if nip:
                data = RiwayatPenghargaan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'penghargaan'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatPenghargaan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatPenghargaanForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penghargaan',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'penghargaan'
        }
        return render(request, '8_riwayat_penghargaan/riwayat_penghargaan_master.html', context)
    
    def post(self, request):
        form = RiwayatPenghargaanForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_penghargaan'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_penghargaan'))
    

class RiwayatPenghargaanUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id):
        try:
            data = RiwayatPenghargaan.objects.get(id=id)
            return data
        except RiwayatPenghargaan.DoesNotExist:
            return None
        
    def get(self, request, **kwargs):
        id = kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='penghargaan').first()
        instance = self.get_object(id)
        form = RiwayatPenghargaanForm(instance=instance, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penghargaan',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'penghargaan':'penghargaan'
        }
        return render(request, '8_riwayat_penghargaan/riwayat_penghargaan_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        form = RiwayatPenghargaanForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_penghargaan = form.save(commit=False)
            if riwayat_penghargaan.file and data_detail.file and data_detail.file != riwayat_penghargaan.file and os.path.isfile(data_detail.file.path):
                os.remove(data_detail.file.path)
            riwayat_penghargaan.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_penghargaan'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_penghargaan'))


class UrutkanRiwayatPenghargaanView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '8_riwayat_penghargaan/riwayat_penghargaan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penghargaan')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_penghargaan(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_penghargaan(instance=self.object, queryset=self.object.riwayatpenghargaan_set.filter(pegawai__profil_user__nip=nip))
            else:    
                urutkan_dokumen_form = urutkan_dokumen_penghargaan(instance=self.object, queryset=self.object.riwayatpenghargaan_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatPenghargaanView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penghargaan',
            'riwayat':'active',
            'selected':'penghargaan'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatPenghargaanDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatPenghargaan
    template_name = '8_riwayat_penghargaan/riwayat_penghargaan_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penghargaan')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='penghargaan').first()
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatPenghargaan.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatPenghargaan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatPenghargaanDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penghargaan',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'penghargaan':'penghargaan'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        return super().form_valid(form)
    

class RiwayatHukumanView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatHukuman.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='hukuman').first()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok}
            if nip:
                data = RiwayatHukuman.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'hukuman'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatHukuman.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatHukumanForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Hukuman',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'hukuman'
        }
        return render(request, '9_riwayat_hukuman/riwayat_hukuman_master.html', context)
    
    def post(self, request, **kwargs):
        form = RiwayatHukumanForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_hukuman'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_hukuman'))
    

class RiwayatHukumanUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id):
        try:
            data = RiwayatHukuman.objects.get(id=id)
            return data
        except RiwayatHukuman.DoesNotExist:
            return None
        
    def get(self, request, **kwargs):
        id = kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='hukuman').first()
        instance = self.get_object(id)
        form = RiwayatHukumanForm(instance=instance, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Hukuman',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'hukuman'
        }
        return render(request, '9_riwayat_hukuman/riwayat_hukuman_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        form = RiwayatHukumanForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_hukuman = form.save(commit=False)
            if riwayat_hukuman.file and data_detail.file and data_detail.file != riwayat_hukuman.file and os.path.isfile(data_detail.file.path):
                os.remove(data_detail.file.path)
            riwayat_hukuman.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_hukuman'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_hukuman'))


class UrutkanRiwayatHukumanView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '9_riwayat_hukuman/riwayat_hukuman_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_hukuman')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_hukuman(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_hukuman(instance=self.object, queryset=self.object.riwayathukuman_set.filter(pegawai__profil_user__nip=nip))
            else:
                urutkan_dokumen_form = urutkan_dokumen_hukuman(instance=self.object, queryset=self.object.riwayathukuman_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatHukumanView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Hukuman',
            'riwayat':'active',
            'selected':'hukuman'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatHukumanDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatHukuman
    template_name = '9_riwayat_hukuman/riwayat_hukuman_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_hukuman')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='hukuman').first()
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatHukuman.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatHukuman.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatHukumanDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Hukuman',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'hukuman'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        return super().form_valid(form)
    

class RiwayatCutiView(LoginRequiredMixin, CheckCuti, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatCuti.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='cuti').first()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok}
            if nip:
                data = RiwayatCuti.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'cuti'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatCuti.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatCutiForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'cek_sisa_cuti':self.cek_sisa_cuti(user),
            'cek_sisa_tunda_cuti':self.cek_sisa_tunda_cuti(user),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Cuti',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'cuti'
        }
        return render(request, '10_riwayat_cuti/riwayat_cuti_master.html', context)
    
    def post(self, request, **kwargs):
        form = RiwayatCutiForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_cuti'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_cuti'))


class RiwayatCutiUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatCuti.objects.get(id=id)
            return data
        except RiwayatCuti.DoesNotExist:
            messages.error(request, 'detail data yang akan diedit tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        id = kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='cuti').first()
        instance = self.get_object(id, request)
        form = RiwayatCutiForm(instance=instance, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Cuti',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'cuti'
        }
        return render(request, '10_riwayat_cuti/riwayat_cuti_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        action = request.GET.get('delete')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        if request.user.is_superuser and action == 'delete':
            data_detail.delete()
            return redirect(reverse('riwayat_urls:riwayat_cuti'))
        form = RiwayatCutiForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_cuti = form.save(commit=False)
            if riwayat_cuti.file and data_detail.file and data_detail.file != riwayat_cuti.file and os.path.isfile(data_detail.file.path):
                os.remove(data_detail.file.path)
            riwayat_cuti.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_cuti'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_cuti'))


class UrutkanRiwayatCutiView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '10_riwayat_cuti/riwayat_cuti_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_cuti')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_cuti(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_cuti(instance=self.object, queryset=self.object.riwayatcuti_set.filter(pegawai__profil_user__nip=nip))
            else:    
                urutkan_dokumen_form = urutkan_dokumen_cuti(instance=self.object, queryset=self.object.riwayatcuti_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatCutiView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Cuti',
            'riwayat':'active',
            'selected':'cuti'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.objSect
                urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatDiklatListView(LoginRequiredMixin, ListView):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    model = Users
    template_name = '11_riwayat_diklat/riwayat_diklat_list_pegawai.html'
    context_object_name = 'data'
    
    def get_queryset(self):
        queryset=self.model.objects.none()
        data = self.model.objects.filter(riwayatdiklat__isnull=False)
        if self.request.user.is_superuser:
            queryset = data.values('id', 'riwayatdiklat__tgl_mulai__year', 'first_name', 'last_name', 'profil_user__nip').annotate(
                frekuensi_diklat = Count('riwayatdiklat', distinct=True),
                jam_diklat = Sum('riwayatdiklat__jam_pelajaran', distinct=True)
            ).distinct()
            return queryset
        if self.request.user.is_staff:
            queryset = data.filter(riwayatpenempatan__penempatan_level3__sub_bidang=self.request.user.riwayatpenempatan_set.filter(status=True).last().penempatan
            ).values('id', 'riwayatdiklat__tgl_mulai__year', 'first_name', 'last_name', 'profil_user__nip').annotate(
                frekuensi_diklat=Count('riwayatdiklat', distinct=True),
                jam_diklat=Sum('riwayatdiklat__jam_pelajaran', distinct=True) 
            ).distinct()|data.filter(riwayatpenempatan__penempatan_level2__bidang=self.request.user.riwayatpenempatan_set.filter(status=True).last().penempatan
            ).values('id', 'riwayatdiklat__tgl_mulai__year', 'first_name', 'last_name', 'profil_user__nip').annotate(
                frekuensi_diklat=Count('riwayatdiklat', distinct=True),
                jam_diklat=Sum('riwayatdiklat__jam_pelajaran', distinct=True)
            ).distinct()|data.filter(riwayatpenempatan__penempatan_level1__unor=self.request.user.riwayatpenempatan_set.filter(status=True).last().penempatan
            ).values('id', 'riwayatdiklat__tgl_mulai__year', 'first_name', 'last_name', 'profil_user__nip').annotate(
                frekuensi_diklat=Count('riwayatdiklat', distinct=True),
                jam_diklat=Sum('riwayatdiklat__jam_pelajaran', distinct=True)
            ).distinct()
            return queryset
        else:
            queryset = data.filter(pk=self.request.user.pk).values('id', 'riwayatdiklat__tgl_mulai__year', 'first_name', 'last_name', 'profil_user__nip').annotate(
                frekuensi_diklat=Count('riwayatdiklat', distinct=True),
                jam_diklat = Sum('riwayatdiklat__jam_pelajaran', distinct=True)
            )
        return queryset
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page']='Home'
        context['sub_page']='Riwayat'
        context['title_page']='Diklat'
        context['form_view']='none'
        context['data_view']='block'
        context['riwayat']='active'
        context['selected']='diklat'
        return context
    

class RiwayatDiklatDetailView(LoginRequiredMixin, DeleteView):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    model = Users
    template_name = '11_riwayat_diklat/riwayat_diklat_list_perorang.html'
    context_object_name = 'data'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page']='Home'
        context['sub_page']='Riwayat'
        context['title_page']='Diklat'
        context['form_view']='none'
        context['data_view']='block'
        context['riwayat']='active'
        context['selected']='diklat'
        return context
            

class RiwayatDiklatCreateView(LoginRequiredMixin, CreateView):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    model = RiwayatDiklat
    form_class = RiwayatDiklatForm
    template_name = '11_riwayat_diklat/riwayat_diklat_form.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_diklat')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request']=self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page']='Home'
        context['sub_page']='Riwayat'
        context['title_page']='Diklat'
        context['form_view']='none'
        context['data_view']='block'
        context['riwayat']='active'
        context['selected']='diklat'
        return context
    
    def form_invalid(self, form):
        messages.error(self.request, 'Maaf terjadi kesalahan, harap hubungi admin!')
        print('error: ', form.errors)
        return super().form_invalid(form)
                
class RiwayatDiklatView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatDiklat.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='diklat').first()
        users = Users.objects.all()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok}
            if nip:
                data = RiwayatDiklat.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'diklat'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatDiklat.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatDiklatForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data':users,
            'form':form,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Diklat',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'diklat'
        }
        return render(request, '11_riwayat_diklat/riwayat_diklat_master.html', context)
    
    def post(self, request, **kwargs):
        form = RiwayatDiklatForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save() #save dimodifikasi untuk menyimpan pelatihan yang bersifat kompetensi ke dalam MODEL KOMPETENSI
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_diklat'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_diklat'))


class RiwayatDiklatPegawaiView(LoginRequiredMixin, ListView):
    model = RiwayatDiklat
    template_name = '11_riwayat_diklat/riwayat_diklat_pegawai.html'
    context_object_name = 'data'
    
    def get_queryset(self):
        user = self.request.user
        nip = get_nip(user)
        if self.request.user.is_superuser:
            data = Users.objects.all().annotate(
                frekuensi_diklat=Count('riwayatdiklat'),
                jam_diklat=Sum('riwayatdiklat__jam_pelajaran')
            )
        elif self.request.user.is_staff:
            data = Users.objects.filter(riwayatpenempatan__penempatan_level3__sub_bidang=self.request.user.riwayatpenempatan_set.filter(status=True).last().penempatan).annotate(
                frekuensi_diklat=Count('riwayatdiklat', distinct=True),
                jam_diklat=Sum('riwayatdiklat__jam_pelajaran', distinct=True) 
            ).distinct()|Users.objects.filter(riwayatpenempatan__penempatan_level2__bidang=self.request.user.riwayatpenempatan_set.filter(status=True).last().penempatan).annotate(
                frekuensi_diklat=Count('riwayatdiklat', distinct=True),
                jam_diklat=Sum('riwayatdiklat__jam_pelajaran', distinct=True)
            ).distinct()|Users.objects.filter(riwayatpenempatan__penempatan_level1__unor=self.request.user.riwayatpenempatan_set.filter(status=True).last().penempatan).annotate(
                frekuensi_diklat=Count('riwayatdiklat', distinct=True),
                jam_diklat=Sum('riwayatdiklat__jam_pelajaran', distinct=True)
            ).distinct()
        else:
            data = Users.objects.filter(profil_user__nip=nip).annotate(
                frekuensi_diklat=Count('riwayatdiklat'),
                jam_diklat=Sum('riwayatdiklat__jam_pelajaran')
            )
        return data
    
    def get_context_data(self, **kwargs):
        context = super(RiwayatDiklatPegawaiView, self).get_context_data(**kwargs)
        context.update({
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Diklat',
            'riwayat':'active',
            'selected':'diklat'
        })
        return context
    
    
class RiwayatDiklatUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatDiklat.objects.get(id=id)
            return data
        except RiwayatDiklat.DoesNotExist:
            messages.error(request, 'Mohon maaf detail data yang akan diupdate tidak ditemukan!')

    def get(self, request, **kwargs):
        id = kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='diklat').first()
        instance = self.get_object(id, request)
        form = RiwayatDiklatForm(instance=instance, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Diklat',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'diklat'
        }
        return render(request, '11_riwayat_diklat/riwayat_diklat_master.html', context)
    
    def post(self, request, **kwargs):
        id=kwargs.get('id')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        form = RiwayatDiklatForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            # riwayat_diklat = form.save(commit=False)
            # if riwayat_diklat and riwayat_diklat.file and data_detail.file and data_detail.file != riwayat_diklat.file and os.path.isfile(data_detail.file.path):
            #     os.remove(data_detail.file.path)
            # riwayat_diklat.save()
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_diklat'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_diklat'))
        

class UrutkanRiwayatDiklatView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '11_riwayat_diklat/riwayat_diklat_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_diklat')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_diklat(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_diklat(instance=self.object, queryset=self.object.riwayatdiklat_set.filter(pegawai__profil_user__nip=nip))
            else:    
                urutkan_dokumen_form = urutkan_dokumen_diklat(instance=self.object, queryset=self.object.riwayatdiklat_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatDiklatView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Diklat',
            'riwayat':'active',
            'selected':'diklat'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatDiklatDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatDiklat
    template_name = '11_riwayat_diklat/riwayat_diklat_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_diklat')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='diklat').first()
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatDiklat.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatDiklat.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatDiklatDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Diklat',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'diklat'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        return super().form_valid(form)
    

class RiwayatKompetensiView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = Kompetensi.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='kompetensi').first()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':get_user_bynip(nip), 'dokumen':dok}
            if nip:
                data = Kompetensi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'kompetensi'}))
        if selected_nip:
            nip = selected_nip
            data = Kompetensi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = KompetensiForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Kompetensi',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'kompetensi'
        }
        return render(request, '18_riwayat_kompetensi/riwayat_kompetensi_master.html', context)
    
    def post(self, request, **kwargs):
        form = KompetensiForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_kompetensi'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_kompetensi'))
        

class RiwayatKomptensiUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = Kompetensi.objects.get(id=id)
            return data
        except Kompetensi.DoesNotExist:
            messages.error(request, 'Mohon maaf detail data yang akan diupdate tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        id=kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='kompetensi').first()
        instance = self.get_object(id, request)
        form = KompetensiForm(instance=instance, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Kompetensi',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'kompetensi'
        }
        return render(request, '18_riwayat_kompetensi/riwayat_kompetensi_master.html', context)
    
    def post(self, request, **kwargs):
        id=kwargs.get('id')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        form = KompetensiForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_kompetensi = form.save(commit=False)
            if riwayat_kompetensi.file_sert and data_detail.file_sert and data_detail.file_sert != riwayat_kompetensi.file_sert and os.path.isfile(data_detail.file_sert.path):
                os.remove(data_detail.file_sert.path)
            riwayat_kompetensi.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_kompetensi'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_kompetensi'))


class UrutkanRiwayatKompetensiView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '18_riwayat_kompetensi/riwayat_kompetensi_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_kompetensi')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_kompetensi(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_kompetensi(instance=self.object, queryset=self.object.kompetensi_set.filter(pegawai__profil_user__nip=nip))
            else:
                urutkan_dokumen_form = urutkan_dokumen_kompetensi(instance=self.object, queryset=self.object.kompetensi_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatKompetensiView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Kompetensi',
            'riwayat':'active',
            'selected':'kompetensi'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)


class RiwayatKompetensiDeleteView(SuccessMessageMixin, DeleteView):
    model = Kompetensi
    template_name = '18_riwayat_kompetensi/riwayat_kompetensi_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_kompetensi')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='kompetensi').first()
        nip = None
        if self.request.user.is_superuser:
            data = Kompetensi.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = Kompetensi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatKompetensiDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok,
            'sub_page':'Riwayat',
            'title_page':'Kompetensi',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'kompetensi'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file_sert:
            if os.path.isfile(self.object.file_sert.path):
                os.remove(self.object.file_sert.path)
        return super().form_valid(form)


class RiwayatOrganisasiView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatOrganisasi.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='organisasi').first()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':get_user_bynip(nip), 'dokumen':dok}
            if nip:
                data = RiwayatOrganisasi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'organisasi'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatOrganisasi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatOrganisasiForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Organisasi',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'organisasi'
        }
        return render(request, '12_riwayat_organisasi/riwayat_organisasi_master.html', context)
    
    def post(self, request, **kwargs):
        form = RiwayatOrganisasiForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_organisasi'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_organisasi'))


class RiwayatOrganisasiUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatOrganisasi.objects.get(id=id)
            return data
        except RiwayatOrganisasi.DoesNotExist:
            messages.error(request, 'Mohon maaf detail data yang akan diupdate tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        id=kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='organisasi').first()
        instance = self.get_object(id, request)
        form = RiwayatOrganisasiForm(instance=instance, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Organisasi',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'organisasi'
        }
        return render(request, '12_riwayat_organisasi/riwayat_organisasi_master.html', context)
    
    def post(self, request, **kwargs):
        id=kwargs.get('id')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        form = RiwayatOrganisasiForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_organisasi = form.save(commit=False)
            if riwayat_organisasi.file and data_detail.file and data_detail.file != riwayat_organisasi.file and os.path.isfile(data_detail.file.path):
                os.remove(data_detail.file.path)
            riwayat_organisasi.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_organisasi'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_organisasi'))
    

class UrutkanRiwayatOrganisasiView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '12_riwayat_organisasi/riwayat_organisasi_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_organisasi')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_organisasi(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_organisasi(instance=self.object, queryset=self.object.riwayatorganisasi_set.filter(pegawai__profil_user__nip=nip))
            else:
                urutkan_dokumen_form = urutkan_dokumen_organisasi(instance=self.object, queryset=self.object.riwayatorganisasi_set.filter(pegawai=self.request.user))    
        context = super(UrutkanRiwayatOrganisasiView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Organisasi',
            'riwayat':'active',
            'selected':'organisasi'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatOrganisasiDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatOrganisasi
    template_name = '12_riwayat_organisasi/riwayat_organisasi_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_organisasi')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='organisasi')
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatOrganisasi.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatOrganisasi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatOrganisasiDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Organisasi',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'organisasi'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        return super().form_valid(form)


class RiwayatProfesiView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatProfesi.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='profesi').first()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok}
            if nip:
                data = RiwayatProfesi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'profesi'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatProfesi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatProfesiForm(initial=initial, request=request)
        context={
            'user':get_user_bynip(nip),
            'data_str':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Profesi',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'str':True,
            'selected':'profesi'
        }
        return render(request, '13_riwayat_profesi/riwayat_profesi_master.html', context)
    
    def post(self, request, **kwargs):
        form = RiwayatProfesiForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_profesi'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_profesi'))
    

class RiwayatProfesiUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatProfesi.objects.get(id=id)
            return data
        except RiwayatProfesi.DoesNotExist:
            # messages.error(request, 'Mohon maaf detail data yang akan diupdate tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        id=kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='profesi').first()
        instance=self.get_object(id, request)
        form = RiwayatProfesiForm(instance=instance, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Profesi',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'profesi'
        }
        return render(request, '13_riwayat_profesi/riwayat_profesi_master.html', context)
    
    def post(self, request, **kwargs):
        id=kwargs.get('id')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        form = RiwayatProfesiForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_profesi = form.save(commit=False)
            if riwayat_profesi.file_str and data_detail.file_str and data_detail.file_str != riwayat_profesi.file_str and os.path.isfile(data_detail.file_str.path):
                os.remove(data_detail.file_str.path)
            riwayat_profesi.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_profesi'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_profesi'))
        

class RiwayatProfesiDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatProfesi
    template_name = '13_riwayat_profesi/riwayat_profesi_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_profesi')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='profesi').first()
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatProfesi.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatProfesi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatProfesiDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data_str':data,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Profesi',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'profesi'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file_str:
            if os.path.isfile(self.object.file_str.path):
                os.remove(self.object.file_str.path)
        for child in self.object.riwayatsipprofesi_set.all():
            if child.file_sip and os.path.isfile(child.file_sip.path):
                os.remove(child.file_sip.path)
        return super().form_valid(form)


class RiwayatSIPProfesiView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_str_object(self, id):
        try:
            data = RiwayatProfesi.objects.get(id=id)
            return data
        except RiwayatProfesi.DoesNotExist:
            return None
        
    def get(self, request, **kwargs):
        id_str = kwargs.get('id')
        str_obj = self.get_str_object(id_str)
        data = RiwayatSIPProfesi.objects.filter(riwayat_profesi=str_obj)
        initial = {'riwayat_profesi':str_obj}
        form = RiwayatSIPProfesiForm(initial=initial)
        context={
            'data_sip':data,
            'form':form,
            'str_obj': str_obj,
            'id_str':str_obj.id if str_obj is not None else None,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Profesi',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'sip':True,
            'selected':'profesi'
        }
        return render(request, '13_riwayat_profesi/riwayat_profesi_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        form = RiwayatSIPProfesiForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_sipprofesi', kwargs={'id':id}))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_sipprofesi', kwargs={'id':id}))


class RiwayatSIPProfesiUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_str_object(self, id):
        try:
            data = RiwayatProfesi.objects.get(id=id)
            return data
        except RiwayatProfesi.DoesNotExist:
            return None

    def get_object(self, id):
        try:
            data = RiwayatSIPProfesi.objects.get(id=id)
            return data
        except RiwayatSIPProfesi.DoesNotExist:
            return None
    
    def get(self, request, **kwargs):
        id = kwargs.get('id')
        id_str = kwargs.get('id_str')
        instance = self.get_object(id)
        form = RiwayatSIPProfesiForm(instance=instance)
        context={
            'update_form':True,
            'form':form,
            'id_str':id_str,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Profesi',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'sip':True,
            'selected':'profesi'
        }
        return render(request, '13_riwayat_profesi/riwayat_profesi_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        id_str = kwargs.get('id_str')
        str_obj = self.get_str_object(id_str)
        data_detail = self.get_object(id)
        instance=self.get_object(id)
        form = RiwayatSIPProfesiForm(data=request.POST, files=request.FILES, instance=instance)
        if form.is_valid():
            riwayat_sipprofesi = form.save(commit=False)
            if riwayat_sipprofesi.file_sip and data_detail.file_sip and data_detail.file_sip != riwayat_sipprofesi.file_sip and os.path.isfile(data_detail.file_sip.path):
                os.remove(data_detail.file_sip.path)
            riwayat_sipprofesi.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_sipprofesi', kwargs={'id':str_obj.id}))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_sipprofesi', kwargs={'ud':str_obj.id}))


class UrutkanRiwayatSIPProfesiView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = RiwayatProfesi
    template_name = '13_riwayat_profesi/riwayat_sip_urutkan_dokumen.html'
    success_message = 'Urutan data berhasil diupdate!'

    def get_form_class(self):
        form = UrutkanRiwayatProfesiForm
        return form
    
    def get_success_url(self) -> str:
        id_str = self.kwargs.get('pk')
        return reverse_lazy('riwayat_urls:riwayat_sipprofesi', kwargs={'id':id_str})

    def get_context_data(self, **kwargs):
        context = super(UrutkanRiwayatSIPProfesiView, self).get_context_data(**kwargs)
        id_str = self.kwargs.get('pk')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_sip(self.request.POST, instance=self.object)
        else:
            urutkan_dokumen_form = urutkan_dokumen_sip(instance=self.object, queryset=self.object.riwayatsipprofesi_set.filter(riwayat_profesi__id=id_str))
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'id_str':id_str,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Profesi',
            'riwayat':'active',
            'selected':'profesi'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatSIPDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatSIPProfesi
    template_name = '13_riwayat_profesi/riwayat_profesi_master.html'
    success_message = "Data berhasil dihapus!"

    def get_success_url(self, **kwargs) -> str:
        success_url = reverse_lazy('riwayat_urls:riwayat_sipprofesi', kwargs={'id':self.kwargs.get('id_str')})
        return success_url
    
    def get_context_data(self, **kwargs):
        id_str = self.kwargs.get('id_str')
        data = RiwayatSIPProfesi.objects.filter(riwayat_profesi__id=id_str).order_by('no_urut_dokumen')
        context = super(RiwayatSIPDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data_sip':data,
            'id_str':id_str,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Profesi',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'sip':True,
            'selected':'profesi'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file_sip:
            if os.path.isfile(self.object.file_sip.path):
                os.remove(self.object.file_sip.path)
        return super().form_valid(form)


class RiwayatBekerjaView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        data = RiwayatBekerja.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='bekerja').first()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok}
            if nip:
                data = RiwayatBekerja.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'bekerja'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatBekerja.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatBekerjaForm(initial=initial, request=request)
        context={
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Bekerja',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'bekerja'
        }
        return render(request, '14_riwayat_bekerja/riwayat_bekerja_master.html', context)
    
    def post(self, request, **kwargs):
        form = RiwayatBekerjaForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_bekerja'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_bekerja'))


class RiwayatBekerjaUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatBekerja.objects.get(id=id)
            return data
        except RiwayatBekerja.DoesNotExist:
            messages.error(request, 'Mohon maaf detail data yang akan diupdate tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        id=kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='bekerja').first()
        instance=self.get_object(id, request)
        form = RiwayatBekerjaForm(instance=instance, request=request)
        context={
            'update_form':True,
            'form':form,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Bekerja',
            'form_view':'block',
            'data_view':'none',
            'riwayat':'active',
            'selected':'bekerja'
        }
        return render(request, '14_riwayat_bekerja/riwayat_bekerja_master.html', context)
    
    def post(self, request, **kwargs):
        id=kwargs.get('id')
        data_detail = self.get_object(id)
        instance = self.get_object(id)
        form = RiwayatBekerjaForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_bekerja = form.save(commit=False)
            if riwayat_bekerja.file and data_detail.file and data_detail.file != riwayat_bekerja.file and os.path.isfile(data_detail.file.path):
                os.remove(data_detail.file.path)
            riwayat_bekerja.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_bekerja'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_bekerja'))


class UrutkanRiwayatBekerjaView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '14_riwayat_bekerja/riwayat_bekerja_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_bekerja')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_bekerja(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_bekerja(instance=self.object, queryset=self.object.riwayatbekerja_set.filter(pegawai__profil_user__nip=nip))
            else:
                urutkan_dokumen_form = urutkan_dokumen_bekerja(instance=self.object, queryset=self.object.riwayatbekerja_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatBekerjaView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Bekerja',
            'riwayat':'active',
            'selected':'bekerja'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)


class RiwayatBekerjaDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatBekerja
    template_name = '14_riwayat_bekerja/riwayat_bekerja_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_bekerja')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='bekerja').first()
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatBekerja.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatBekerja.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatBekerjaDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Bekerja',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'bekerja'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        return super().form_valid(form)


class RiwayatKeluargaView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        get_form = request.GET.get('form')
        user = request.user
        form_view = 'none'
        data_view = 'block'
        if get_form == 'block':
            form_view = 'block'
            data_view = 'none'
        selected_nip = request.GET.get('nip')
        data = RiwayatKeluarga.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='keluarga').first()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok}
            if nip:
                data = RiwayatKeluarga.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'keluarga'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatKeluarga.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = RiwayatKeluargaForm(initial=initial)
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Keluarga',
            'form_view':form_view,
            'data_view':data_view,
            'riwayat':'active',
            'selected':'keluarga'
        }
        return render(request, '15_riwayat_keluarga/riwayat_keluarga_master.html', context)
    
    def post(self, request, **kwargs):
        form = RiwayatKeluargaForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_keluarga'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_keluarga'))


class RiwayatKeluargaUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = RiwayatKeluarga.objects.get(id=id)
            return data
        except RiwayatKeluarga.DoesNotExist:
            return None
        
    def get(self, request, **kwargs):
        id =kwargs.get('id')
        dok = DokumenSDM.objects.filter(url='keluarga').first()
        get_form = request.GET.get('form')
        form_view = 'block'
        data_view = 'none'
        if get_form == 'block':
            form_view = 'block'
            data_view = 'none'
        instance = self.get_object(id, request)
        form = RiwayatKeluargaForm(instance=instance, request=request)
        context={
            'update_form':True,
            'form':form,
            'detail':instance,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Keluarga',
            'form_view':form_view,
            'data_view':data_view,
            'riwayat':'active',
            'selected':'keluarga'
        }
        return render(request, '15_riwayat_keluarga/riwayat_keluarga_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        data_detail = self.get_object(id)
        instance=self.get_object(id)
        form = RiwayatKeluargaForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            riwayat_keluarga = form.save(commit=False)
            if riwayat_keluarga.file and data_detail.file and data_detail.file != riwayat_keluarga.file and os.path.isfile(data_detail.file.path):
                os.remove(data_detail.file.path)
            riwayat_keluarga.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_keluarga'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_keluarga'))
        

class RiwayatKeluargaDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatKeluarga
    template_name = '15_riwayat_keluarga/riwayat_keluarga_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_keluarga')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='keluarga').first()
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatKeluarga.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatKeluarga.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatKeluargaDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Keluarga',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'keluarga'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file:
            if os.path.isfile(self.object.file.path):
                os.remove(self.object.file.path)
        return super().form_valid(form)


class RiwayatAnggotaKeluargaView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data=RiwayatKeluarga.objects.get(id=id)
            return data
        except RiwayatKeluarga.DoesNotExist:
            messages.error(request, 'Mohon maaf detail riwayat keluarga tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        keluarga_id = kwargs.get('keluarga_id')
        get_status:str = kwargs.get('status')
        get_form = request.GET.get('form')
        form_view = 'none'
        data_view = 'block'
        if get_form == 'block':
            form_view = 'block'
            data_view = 'none'
        status = 'pasangan'
        if get_status:
            status = get_status.lower()
        initial = {'keluarga':self.get_object(keluarga_id, request)}
        if status == 'pasangan':
            data = Pasangan.objects.filter(keluarga=keluarga_id)
            form = RiwayatKeluargaPasanganForm(initial=initial)
        elif status == 'anak':
            data = Anak.objects.filter(keluarga=keluarga_id)
            form = RiwayatKeluargaAnakForm(initial=initial)
        else:
            data = OrangTua.objects.filter(keluarga=keluarga_id)
            form = RiwayatKeluargaOrangTuaForm(initial=initial)

        context={
            'pegawai':self.get_object(keluarga_id),
            'keluarga_id':keluarga_id,
            'data':data,
            'form':form,
            'status':status,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Keluarga',
            'form_view':form_view,
            'data_view':data_view,
            'riwayat':'active',
            'selected':'keluarga'
        }
        return render(request, '16_riwayat_anggota_keluarga/riwayat_anggota_keluarga_master.html', context)
    
    def post(self, request, **kwargs):
        keluarga_id = kwargs.get('keluarga_id')
        status = kwargs.get('status')
        if status == 'orang-tua':
            form = RiwayatKeluargaOrangTuaForm(data=request.POST, files=request.FILES)
        elif status == 'pasangan':
            form = RiwayatKeluargaPasanganForm(data=request.POST, files=request.FILES)
        else:
            form = RiwayatKeluargaAnakForm(data=request.POST, files=request.FILES)

        if form.is_valid():
            if status == 'pasangan':
                form.save()
            else:
                form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_anggota_keluarga', kwargs={'status':status, 'keluarga_id':keluarga_id}))
        messages.error(request, form_not_valid_message)
        return redirect(reverse('riwayat_urls:riwayat_anggota_keluarga', kwargs={'status':status, 'keluarga_id':keluarga_id}))


class RiwayatAnggotaKeluargaUpdateView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data=RiwayatKeluarga.objects.get(id=id)
            return data
        except RiwayatKeluarga.DoesNotExist:
            messages.error(request, 'Mohon maaf detail riwayat keluarga tidak ditemukan!')
            return None
        
    def get_instance(self, id, status):
        try:
            if status == 'pasangan':
                data = Pasangan.objects.get(id=id)
            elif status == 'anak':
                data = Anak.objects.get(id=id)
            else:
                data = OrangTua.objects.get(id=id)
            return data
        except Exception:
            return None
        
    def get(self, request, **kwargs):
        id = kwargs.get('id')
        keluarga_id = kwargs.get('keluarga_id')
        get_status:str = kwargs.get('status')
        get_form = request.GET.get('form')
        form_view = 'block'
        data_view = 'none'
        if get_form == 'block':
            form_view = 'block'
            data_view = 'none'
        status = 'pasangan'
        if get_status:
            status = get_status.lower()
        instance = self.get_instance(id, status)
        if status == 'pasangan':
            form = RiwayatKeluargaPasanganForm(instance=instance)
        elif status == 'anak':
            form = RiwayatKeluargaAnakForm(instance=instance)
        else:
            form = RiwayatKeluargaOrangTuaForm(instance=instance)

        context={
            'update_form':True,
            'pegawai':self.get_object(keluarga_id),
            'keluarga_id':keluarga_id,
            'form':form,
            'status':status,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Keluarga',
            'form_view':form_view,
            'data_view':data_view,
            'riwayat':'active',
            'selected':'keluarga'
        }
        return render(request, '16_riwayat_anggota_keluarga/riwayat_anggota_keluarga_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        keluarga_id = kwargs.get('keluarga_id')
        status = kwargs.get('status')
        data_detail = self.get_instance(id, status)
        instance = self.get_instance(id, status)
        if status == 'orang-tua':
            form = RiwayatKeluargaOrangTuaForm(data=request.POST, files=request.FILES, instance=instance)
        elif status == 'pasangan':
            form = RiwayatKeluargaPasanganForm(data=request.POST, files=request.FILES, instance=instance)
        else:
            form = RiwayatKeluargaAnakForm(data=request.POST, files=request.FILES, instance=instance)

        if form.is_valid():
            if status == 'pasangan':
                riwayat_pasangan = form.save(commit=False)
                if riwayat_pasangan.file_akte_nikah and data_detail.file_akte_nikah and data_detail.file_akte_nikah != riwayat_pasangan.file_akte_nikah and os.path.isfile(data_detail.file_akte_nikah.path):
                    os.remove(data_detail.file_akte_nikah.path)
                riwayat_pasangan.save()
            else:
                form.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_anggota_keluarga', kwargs={'status':status, 'keluarga_id':keluarga_id}))
        messages.error(request, form_not_valid_message)
        return redirect(reverse('riwayat_urls:riwayat_anggota_keluarga', kwargs={'status':status, 'keluarga_id':keluarga_id}))


class RiwayatOrangTuaDeleteView(SuccessMessageMixin, DeleteView):
    model = OrangTua
    template_name = '16_riwayat_anggota_keluarga/riwayat_anggota_keluarga_master.html'
    success_message = "Data berhasil dihapus!"

    def get_success_url(self, *args, **kwargs) -> str:
        keluarga_id = kwargs.get('keluarga_id')
        status = kwargs.get('status')
        return reverse_lazy('riwayat_urls:riwayat_anggota_keluarga', kwargs={'status':status, 'keluarga_id':keluarga_id})

    def get_context_data(self, **kwargs):
        status = kwargs.get('status')
        keluarga_id = kwargs.get('keluarga_id')
        data = OrangTua.objects.filter(keluarga=keluarga_id)
        context = super(RiwayatOrangTuaDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'keluarga_id':keluarga_id,
            'status':status,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Keluarga',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'keluarga'
        })
        return context


class RiwayatInovasiView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        user = request.user
        selected_nip = request.GET.get('nip')
        dok = DokumenSDM.objects.filter(url='inovasi').first()
        data = RiwayatInovasi.objects.all().order_by('no_urut_dokumen')
        nip=None
        if not request.user.is_superuser:
            nip = get_nip(user)
            if nip:
                data = RiwayatInovasi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'inovasi'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatInovasi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        form = None
        context={
            'user':get_user_bynip(nip),
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Inovasi',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'inovasi'
        }
        return render(request, '17_riwayat_inovasi/riwayat_inovasi_master.html', context)
    

class RiwayatInovasiDeleteView(SuccessMessageMixin, DeleteView):
    model = RiwayatInovasi
    template_name = '17_riwayat_inovasi/riwayat_inovasi_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_inovasi')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='inovasi').first()
        nip = None
        if self.request.user.is_superuser:
            data = RiwayatInovasi.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            data = RiwayatInovasi.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context = super(RiwayatInovasiDeleteView, self).get_context_data(**kwargs)
        context.update({
            'data':data,
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Inovasi',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'inovasi'
        })
        return context
    
    def form_valid(self, form):
        # Delete the associated file
        if self.object.file_sk:
            if os.path.isfile(self.object.file_sk.path):
                os.remove(self.object.file_sk.path)
        return super().form_valid(form)


class UrutkanRiwayatInovasiView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '17_riwayat_inovasi/riwayat_inovasi_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_inovasi')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_inovasi(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_inovasi(instance=self.object, queryset=self.object.riwayatinovasi_set.filter(pegawai__profil_user__nip=nip))
            else:
                urutkan_dokumen_form = urutkan_dokumen_inovasi(instance=self.object, queryset=self.object.riwayatinovasi_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatInovasiView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Inovasi',
            'riwayat':'active',
            'selected':'inovasi'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatPenugasanListView(LoginRequiredMixin, ListView):
    model=RiwayatPenugasan
    template_name='19_riwayat_penugasan/riwayat_penugasan_master.html'

    def get_queryset(self):
        user = self.request.user
        queryset = RiwayatPenugasan.objects.all().order_by('no_urut_dokumen')
        nip = get_nip(user)
        if nip and not user.is_superuser:
            queryset = RiwayatPenugasan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        return queryset

    def get_context_data(self, **kwargs):
        context = super(RiwayatPenugasanListView, self).get_context_data(**kwargs)
        dok = DokumenSDM.objects.filter(url='penugasan').first()
        selected_nip = self.request.GET.get('nip')
        user = self.request.user
        nip = get_nip(user)
        if self.request.user.is_superuser:
            nip = selected_nip
        context.update({
            'nip':nip,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penugasan',
            'riwayat':'active',
            'selected':'penugasan'
        })
        return context


class RiwayatPenugasanCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = RiwayatPenugasan
    template_name='19_riwayat_penugasan/riwayat_penugasan_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penugasan')
    form_class = RiwayatPenugasanForm
    success_message = 'Data berhasil disimpan!'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        dok = DokumenSDM.objects.filter(url='penugasan').first()
        kwargs['user'] = self.request.user
        if self.request.user.is_superuser:
            kwargs['initial_values'] = {'dokumen':dok}
        else:
            kwargs['initial_values'] = {'pegawai':self.request.user, 'dokumen':dok }
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(RiwayatPenugasanCreateView, self).get_context_data(**kwargs)
        dok = DokumenSDM.objects.filter(url='penugasan').first()
        context.update({
            'add_form':True,
            'dok':dok,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penugasan',
            'riwayat':'active',
            'selected':'penugasan'
        })
        return context


class RiwayatPenugasanUpdateView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = RiwayatPenugasan
    template_name='19_riwayat_penugasan/riwayat_penugasan_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penugasan')
    form_class = RiwayatPenugasanForm
    success_message = 'Data berhasil diupdate!'

    def get_context_data(self, **kwargs):
        context = super(RiwayatPenugasanUpdateView, self).get_context_data(**kwargs)
        dok = DokumenSDM.objects.filter(url='penugasan').first()
        context.update({
            'update_form':True,
            'dok':dok,
            'add_form':True,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penugasan',
            'riwayat':'active',
            'selected':'penugasan'
        })
        return context
    

class RiwayatPenugasanDeleteView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = RiwayatPenugasan
    template_name='19_riwayat_penugasan/riwayat_penugasan_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penugasan')
    success_message = 'Data berhasil dihapus!'

    def get_context_data(self, **kwargs):
        context = super(RiwayatPenugasanDeleteView, self).get_context_data(**kwargs)
        dok = DokumenSDM.objects.filter(url='penugasan').first()
        user = self.request.user
        nip = None
        object_list = None
        if self.request.user.is_superuser:
            object_list = RiwayatPenugasan.objects.all().order_by('no_urut_dokumen')
        else:
            nip = get_nip(user)
            object_list = RiwayatPenugasan.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        context.update({
            'nip':nip,
            'dok':dok,
            'object_list':object_list,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penugasan',
            'riwayat':'active',
            'selected':'penugasan'
        })
        return context


class UrutkanRiwayatPenugasanView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '19_riwayat_penugasan/riwayat_penugasan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penugasan')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = self.request.GET.get('nip')
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_penugasan(self.request.POST, instance=self.object)
        else:
            if nip:
                urutkan_dokumen_form = urutkan_dokumen_penugasan(instance=self.object, queryset=self.object.riwayatpenugasan_set.filter(pegawai__profil_user__nip=nip))
            else:
                urutkan_dokumen_form = urutkan_dokumen_penugasan(instance=self.object, queryset=self.object.riwayatpenugasan_set.filter(pegawai=self.request.user))
        context = super(UrutkanRiwayatPenugasanView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Bekerja',
            'riwayat':'active',
            'selected':'bekerja'
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        with transaction.atomic():
            self.object = form.save()
            if urutkan_dokumen_form.is_valid():
                urutkan_dokumen_form.instance = self.object
                urutkan_dokumen_form.save()
        return super().form_valid(form)


class GetListRiwayatSDM(View):
    # BUAT TOKEN UNTUK DAPATKAN DATA DENGAN JWT, DAN LEWATKAN TOKEN MELALUI URL
    def get(self, request):
        request_data = request.GET.get('p')
        list_dok = None
        data = DokumenSDM.objects.filter(view=True, url=request_data).first()

        if data is not None and data.url == 'pendidikan':
            list_dok = RiwayatPendidikan.objects.all()
        elif data is not None and data.url == 'profesi':
            list_dok = RiwayatProfesi.objects.filter(pegawai__riwayatjabatan__nama_jabatan__kategori_sdm="Nakes")
        elif data is not None and data.url == 'inovasi':
            list_dok = RiwayatInovasi.objects.all()
        elif data is not None and data.url == 'kompetensi':
            list_dok = RiwayatPendidikan.objects.all()
        elif data is not None and data.url == 'organisasi':
            list_dok = RiwayatBekerja.objects.all()
        elif data is not None and data.url == 'diklat':
            list_dok = RiwayatBekerja.objects.all()
        elif data is not None and data.url == '':
            list_dok = RiwayatBekerja.objects.all()
        elif data is not None and data.url == 'bekerja':
            list_dok = RiwayatBekerja.objects.all()
        elif data is not None and data.url == 'bekerja':
            list_dok = RiwayatBekerja.objects.all()
        elif data is not None and data.url == 'bekerja':
            list_dok = RiwayatBekerja.objects.all()
        elif data is not None and data.url == 'bekerja':
            list_dok = RiwayatBekerja.objects.all()
        elif data is not None and data.url == 'profil':
            list_dok = RiwayatBekerja.objects.all()
       
        context = {
            'data':list_dok
        }
        return render(request, 'listdata.html', context)
