from django.db.models import Q, Count, F, Case, When, Sum, Prefetch, IntegerField
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.views.generic import ListView, DetailView, DeleteView, UpdateView, CreateView, TemplateView
# from rest_framework.views import 
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
# from django.utils.text import slugify
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from itertools import chain, zip_longest
from functools import lru_cache
import os
from django.shortcuts import get_object_or_404
from django.utils import timezone

from layanan.services import CheckCuti
from layanan.models import (
    JenisLayanan
)
from layanan.access.diklat import (
    filter_diklat_history_queryset,
    filter_users_for_diklat_role,
    is_diklat_admin,
    is_diklat_structural_officer,
)
from layanan.access.cuti import (
    can_manage_cuti_history,
    filter_cuti_history_queryset,
    filter_users_for_leave_role,
    is_leave_admin,
    is_leave_structural_officer,
)
from layanan.access.sip import (
    can_manage_profession_history,
    filter_profession_history_queryset,
    filter_profession_sip_queryset,
    filter_users_for_sip_role,
    is_sip_admin,
    is_sip_structural_officer,
)
from layanan.access.promotion import (
    filter_jabatan_queryset,
    filter_pangkat_queryset,
    filter_users_for_jabatan_role,
    filter_users_for_pangkat_role,
    is_jabatan_admin,
    is_pangkat_admin,
    is_promotion_structural_officer,
)
from layanan.access.berkala import (
    filter_berkala_queryset,
    filter_users_for_berkala_role,
    is_berkala_admin,
    is_berkala_structural_officer,
)
from layanan.access.inovasi import (
    filter_inovasi_queryset,
    filter_users_for_inovasi_role,
    is_inovasi_admin,
    is_inovasi_structural_officer,
)
from layanan.access.documents import (
    filter_document_queryset,
    filter_document_users,
    is_document_scope_manager,
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
    RiwayatInovasi,
    RiwayatPenugasan
    )
from myaccount.models import ProfilSDM, Users
from .access import (
    DocumentAdminRequiredMixin,
    DocumentObjectAccessMixin,
    get_accessible_document,
    get_safe_return_url,
    get_selected_nip,
    preserve_return_url,
    scope_document_queryset,
)
from .generic_views import (
    EmployeeDocumentModule,
)
from .document_registry import DOCUMENT_TYPES
from .requirements import get_required_documents

# Batas struktur baru: modul di bawah ini memakai EmployeeDocumentModule.
# Pendidikan, Panggol, Jabatan, Pengangkatan, Penempatan, Gaji Berkala,
# Kinerja, Penghargaan, Hukuman, Diklat, Kompetensi, Organisasi, Profesi,
# Keluarga, Inovasi (list/delete), dan Penugasan. View riwayat lainnya
# sengaja dipertahankan dalam struktur legacy.
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
    RiwayatPAKForm,
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

# def update_old_file(data):
#     if data_submitted.file: # Ini akan True jika file baru di-upload
#         # 3. Cek apakah file fisik lama benar-benar ada di disk
#         if os.path.exists(berkala_existing.file.path):
#             try:
#                 # 4. Hapus file lama
#                 os.remove(berkala_existing.file.path)
#                 print(f"File lama {berkala_existing.file.path} berhasil dihapus.")
#             except OSError as e:
#                 print(f"Gagal menghapus file lama {berkala_existing.file.path}: {e}")
#         return None
#     return None

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


FILE_KEPEGAWAIAN_SPECS = (
    ('Identitas', 'profil', 'file_ktp', 'KTP', 'fa-id-card'),
    ('Identitas', 'profil', 'file_npwp', 'NPWP', 'fa-receipt'),
    ('Identitas', 'profil', 'file_jkn', 'Kartu JKN', 'fa-heartbeat'),
    ('Identitas', 'profil', 'file_taspen', 'BPJS Ketenagakerjaan/Taspen', 'fa-shield-alt'),
    ('Pendidikan', 'pendidikan', 'file_ijazah', 'Ijazah Terakhir', 'fa-graduation-cap'),
    ('Pendidikan', 'pendidikan', 'file_transkrip', 'Transkrip Terakhir', 'fa-list-alt'),
    ('Kepegawaian', 'panggol', 'file', 'SK Kenaikan Pangkat Terakhir', 'fa-level-up-alt'),
    ('Kepegawaian', 'pengangkatan_cpns', 'file_sk', 'SK CPNS', 'fa-user-check'),
    ('Kepegawaian', 'pengangkatan', 'file_sk', 'SK Pengangkatan ASN/Non-ASN', 'fa-file-signature'),
    ('Kepegawaian', 'pengangkatan', 'file_spmt', 'SPMT', 'fa-clipboard-check'),
    ('Kepegawaian', 'pengangkatan', 'file_latsar', 'Sertifikat Latsar', 'fa-certificate'),
    ('Kepegawaian', 'pengangkatan', 'file_karpeg', 'Kartu Pegawai', 'fa-id-badge'),
    ('Kepegawaian', 'penempatan', 'file', 'SK Penempatan', 'fa-map-marker-alt'),
    ('Kepegawaian', 'berkala', 'file', 'SK Gaji Berkala', 'fa-money-check-alt'),
)


def get_file_kepegawaian_links(data):
    links = []
    seen_urls = set()
    for category, object_key, field_name, label, icon in FILE_KEPEGAWAIAN_SPECS:
        instance = data.get(object_key)
        file_field = getattr(instance, field_name, None) if instance else None
        if not file_field:
            continue
        try:
            url = file_field.url
        except (ValueError, NotImplementedError):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        links.append({
            'category': category,
            'label': label,
            'icon': icon,
            'url': url,
        })
    return links


def file_kepegawaian(request, nip):
    data = None
    if request.user.is_dokumen_admin:
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
        data['links'] = get_file_kepegawaian_links(data)
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
        data['links'] = get_file_kepegawaian_links(data)
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
        nip = get_selected_nip(request)
        if request.user.is_dokumen_admin and not nip:
            return redirect('riwayat_urls:document_admin_dashboard')

        selected_employee = get_user_bynip(nip) if nip else None
        if request.user.is_dokumen_admin and selected_employee is None:
            messages.error(request, 'Pegawai yang dipilih tidak ditemukan.')
            return redirect('riwayat_urls:document_admin_dashboard')
        if nip:
            user = nip
        document_owner = selected_employee or request.user
        required_documents, employment_record = get_required_documents(
            document_owner,
        )
        jenis_dok = list(required_documents)
        for document in jenis_dok:
            configuration = DOCUMENT_TYPES.get(document.url)
            document.is_required = getattr(document, 'is_required', False)
            document.is_empty = bool(
                document.is_required
                and configuration
                and not configuration[1].objects.filter(
                    pegawai=document_owner,
                ).exists()
            )
        jabatan = 'fungsional'
        file_kepeg = file_kepegawaian(request, user)
        data_peg = Users.objects.all().exclude(is_superuser=True)
        context={
            'nip':nip,
            'data_peg':data_peg,
            'file_kepeg':file_kepeg,
            'jabatan':jabatan,
            'jenis_dok':jenis_dok,
            'employment_status': (
                employment_record.status_pegawai
                if employment_record else None
            ),
            'employment_record_missing': employment_record is None,
            'riwayat':'active',
            'page':'Riwayat',
            'selected':'riwayat',
            'title_page':'Menu'
        }
        if request.user.is_dokumen_admin:
            context.update({
                'document_admin_employee': selected_employee,
                'document_admin_document_count': None,
            })
        return render(request, 'riwayat_home.html', context)


class DocumentAdminDashboardView(DocumentAdminRequiredMixin, ListView):
    model = Users
    template_name = 'admin_dokumen/dashboard.html'
    context_object_name = 'employee_list'
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            Users.objects
            .filter(is_active=True, is_superuser=False)
            .select_related('profil_user')
            .order_by('first_name', 'last_name', 'email')
        )
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
                | Q(profil_user__nip__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'q': self.request.GET.get('q', '').strip(),
            'document_admin': 'active',
            'riwayat': 'active',
            'title_page': 'Admin Dokumen SDM',
            'employee_count': Users.objects.filter(
                is_active=True,
                is_superuser=False,
            ).count(),
            'education_unverified_count': RiwayatPendidikan.objects.filter(
                is_verifikasi=False,
            ).count(),
            'education_verified_count': RiwayatPendidikan.objects.filter(
                is_verifikasi=True,
            ).count(),
        })
        return context

class RiwayatKelengkapan(LoginRequiredMixin, View):
    def get(self, request):
        data_peg = Users.objects.all().exclude(is_superuser=True)
        get_nip_user = get_selected_nip(request)
        user = request.user
        nip = get_nip(user)
        if get_nip_user is not None:
            nip = get_nip_user
        kelengkapan = None
        if not request.user.is_dokumen_admin or get_nip_user:
            nip = nip
            kelengkapan = cek_kelengkapan_user(nip)
        elif request.user.is_dokumen_admin:
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


def get_riwayat_menu_url(request, employee=None):
    return_to = get_safe_return_url(request)
    if return_to:
        return return_to
    url = reverse('riwayat_urls:riwayat_view')
    if is_document_scope_manager(request.user) and employee is not None:
        nip = get_nip(employee)
        if nip:
            return f'{url}?nip={nip}'
    return url
    
notfoundview = 'riwayat_urls:notfound_view'
save_success_message = "Data berhasi disimpan!"
form_not_valid_message = "Maaf pengisian form tidak valid"


class DocumentScopeContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_manage_document_scope'] = is_document_scope_manager(
            self.request.user
        )
        return context


class UrutkanRiwayatPendidikanView(DocumentScopeContextMixin, DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
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
        

pendidikan_document = EmployeeDocumentModule(
    model=RiwayatPendidikan,
    form_class=RiwayatPendidikanForm,
    template_name='1_riwayat_pendidikan/riwayat_pendidikan_master.html',
    document_url='pendidikan',
    selected='pendidikan',
    title_page='Pendidikan',
    success_url_name='riwayat_urls:riwayat_pendidikan',
    file_fields=(
        'file_srt_penyetaraan',
        'file_ijazah',
        'file_transkrip',
        'file_verifikasi',
    ),
)

RiwayatPendidikanView = pendidikan_document.manage_view('RiwayatPendidikanView')
RiwayatPendidikanUpdateView = pendidikan_document.update_view(
    'RiwayatPendidikanUpdateView'
)
RiwayatPendidikanDeleteView = pendidikan_document.delete_view(
    'RiwayatPendidikanDeleteView'
)


class PromotionHistoryScopeMixin:
    scope_filter = None
    user_filter = None
    admin_check = None
    role_context_name = None

    def has_management_role(self):
        return is_document_scope_manager(self.request.user)

    def get_selected_employee(self):
        selected_nip = get_selected_nip(self.request)
        if selected_nip:
            return filter_document_users(
                Users.objects.filter(profil_user__nip=selected_nip),
                self.request.user,
            ).first()
        return None if self.has_management_role() else self.request.user

    def get_document_queryset(self):
        queryset = self.model.objects.all()
        if self.select_related:
            queryset = queryset.select_related(*self.select_related)
        queryset = filter_document_queryset(queryset, self.request.user)
        selected_nip = get_selected_nip(self.request)
        if selected_nip:
            queryset = queryset.filter(pegawai__profil_user__nip=selected_nip)
        return queryset.order_by(*self.order_by)

    def get_accessible_object(self, **lookup):
        return get_object_or_404(
            filter_document_queryset(
                self.model.objects.all(), self.request.user
            ),
            **lookup,
        )

    def get_queryset(self):
        return filter_document_queryset(
            self.model.objects.all(), self.request.user
        )

    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        context[self.role_context_name] = self.has_management_role()
        return context


class PanggolRulesMixin(PromotionHistoryScopeMixin):
    """Aturan bisnis khusus pangkat/golongan di atas reusable CRUD view."""

    scope_filter = staticmethod(filter_pangkat_queryset)
    user_filter = staticmethod(filter_users_for_pangkat_role)
    admin_check = staticmethod(is_pangkat_admin)
    role_context_name = 'can_manage_pangkat_role'

    def get_latest_tmt_gol(self, nip):
        if not nip:
            return None
        return (
            RiwayatPanggol.objects
            .filter(
                pegawai__profil_user__nip=nip,
                tmt_gol__isnull=False,
            )
            .order_by('-tmt_gol', '-id')
            .values_list('tmt_gol', flat=True)
            .first()
        )

    def check_status(self, nip):
        latest_tmt = self.get_latest_tmt_gol(nip)
        if latest_tmt is None:
            return True

        period = self.get_document_definition()
        elapsed = relativedelta(date.today(), latest_tmt)
        elapsed_months = (elapsed.years * 12) + elapsed.months
        return elapsed_months >= period.periode_min

    def next_panggol(self, nip):
        latest_tmt = self.get_latest_tmt_gol(nip)
        if latest_tmt is None:
            return None
        return latest_tmt + relativedelta(
            months=self.get_document_definition().periode_max,
        )

    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        nip = context.get('nip')
        context.update({
            'status_panggol': self.check_status(nip),
            'next_panggol': self.next_panggol(nip),
        })
        return context

    def can_create_document(self, form):
        employee = form.cleaned_data.get('pegawai')
        nip = self.get_employee_nip(employee) if employee else None
        return bool(employee and nip and self.check_status(nip))

    def get_creation_denied_message(self, form):
        return 'Anda belum saatnya naik pangkat!'


panggol_document = EmployeeDocumentModule(
    model=RiwayatPanggol,
    form_class=RiwayatPanggolForm,
    template_name='2_riwayat_panggol/riwayat_panggol_master.html',
    document_url='panggol',
    selected='panggol',
    title_page='Panggol',
    success_url_name='riwayat_urls:riwayat_panggol',
    file_fields=('file',),
)

RiwayatPanggolView = panggol_document.manage_view(
    'RiwayatPanggolView',
    mixins=(PanggolRulesMixin,),
)

RiwayatPanggolUpdateView = panggol_document.update_view(
    'RiwayatPanggolUpdateView',
    mixins=(PanggolRulesMixin,),
)
RiwayatPanggolDeleteView = panggol_document.delete_view(
    'RiwayatPanggolDeleteView',
    mixins=(PanggolRulesMixin,),
)


class UrutkanRiwayatPanggolView(DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '2_riwayat_panggol/riwayat_panggol_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_panggol')
    success_message = 'Urutan data berhasil diupdate!'

    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        user = self.request.user
        if nip:
            user = get_user_bynip(nip)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_panggol(
                self.request.POST,
                instance=self.object,
                queryset=scope_document_queryset(
                    self.object.riwayatpanggol_set.all(), self.request.user
                ),
            )
        else:
            queryset = scope_document_queryset(
                self.object.riwayatpanggol_set.all(), self.request.user
            )
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_panggol(
                instance=self.object,
                queryset=queryset,
            )
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

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_panggol')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
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
        selected_nip = get_selected_nip(request)
        data = UjiKompetensi.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='ujikomp')
        initial = {'dokumen':dok.first()}
        nip = None
        if not request.user.is_dokumen_admin:
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
        selected_nip = get_selected_nip(request)
        nip = None
        if not request.user.is_dokumen_admin:
            nip = get_nip(user)
                      
        if request.user.is_dokumen_admin and selected_nip:
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


class JabatanViewMixin(PromotionHistoryScopeMixin):
    """Filter dan state tampilan khusus Riwayat Jabatan."""

    scope_filter = staticmethod(filter_jabatan_queryset)
    user_filter = staticmethod(filter_users_for_jabatan_role)
    admin_check = staticmethod(is_jabatan_admin)
    role_context_name = 'can_manage_jabatan_role'

    def get_jabatan_filter(self):
        return (self.request.GET.get('jabatan') or '').strip()

    def get_document_queryset(self):
        queryset = super().get_document_queryset().exclude(
            pegawai__is_superuser=True,
        )
        if (
            self.has_management_role()
            and not get_selected_nip(self.request)
            and self.get_jabatan_filter()
        ):
            queryset = queryset.filter(
                jns_jabatan__icontains=self.get_jabatan_filter(),
            )
        return queryset

    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        context['jabatan'] = self.get_jabatan_filter()
        if not context.get('update_form') and self.request.GET.get('form'):
            context['form_view'] = 'block'
            context['data_view'] = 'none'
        return context

    def get_success_query_params(self, employee=None):
        params = super().get_success_query_params(employee)
        jabatan = self.get_jabatan_filter()
        if jabatan:
            params['jabatan'] = jabatan
        return params


jabatan_document = EmployeeDocumentModule(
    model=RiwayatJabatan,
    form_class=RiwayatJabatanForm,
    template_name='3_riwayat_jabatan/riwayat_jabatan_master.html',
    document_url='jabatan',
    selected='jabatan',
    title_page='Jabatan',
    success_url_name='riwayat_urls:riwayat_jabatan',
    file_fields=('file', 'file_pemberhentian'),
)

RiwayatJabatanView = jabatan_document.manage_view(
    'RiwayatJabatanView',
    mixins=(JabatanViewMixin,),
)
RiwayatJabatanUpdateView = jabatan_document.update_view(
    'RiwayatJabatanUpdateView',
    mixins=(JabatanViewMixin,),
)
RiwayatJabatanDeleteView = jabatan_document.delete_view(
    'RiwayatJabatanDeleteView',
    mixins=(JabatanViewMixin,),
)


class UrutkanRiwayatJabatanView(DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '3_riwayat_jabatan/riwayat_jabatan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_jabatan')
    success_message = 'Urutan data berhasil diupdate!'

    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        user = self.request.user
        if nip:
            user = get_user_bynip(nip)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_jabatan(
                self.request.POST,
                instance=self.object,
                queryset=scope_document_queryset(
                    self.object.riwayatjabatan_set.all(), self.request.user
                ),
            )
        else:
            queryset = scope_document_queryset(
                self.object.riwayatjabatan_set.all(), self.request.user
            )
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_jabatan(
                instance=self.object,
                queryset=queryset,
            )
        context = super(UrutkanRiwayatJabatanView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Jabatan',
            'riwayat':'active',
            'selected':'jabatan'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_jabatan')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)


pengangkatan_document = EmployeeDocumentModule(
    model=RiwayatPengangkatan,
    form_class=RiwayatPengangkatanForm,
    template_name='4_riwayat_pengangkatan/riwayat_pengangkatan_master.html',
    document_url='pengangkatan',
    selected='pengangkatan',
    title_page='Pengangkatan',
    success_url_name='riwayat_urls:riwayat_pengangkatan',
    file_fields=(
        'file_sk',
        'file_spmt',
        'file_latsar',
        'file_karpeg',
    ),
)

RiwayatPengangkatanView = pengangkatan_document.manage_view(
    'RiwayatPengangkatanView'
)
RiwayatPengangkatanUpdateView = pengangkatan_document.update_view(
    'RiwayatPengangkatanUpdateView'
)
RiwayatPengangkatanDeleteView = pengangkatan_document.delete_view(
    'RiwayatPengangkatanDeleteView'
)


class UrutkanRiwayatPengangkatanView(DocumentScopeContextMixin, DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '4_riwayat_pengangkatan/riwayat_pengangkatan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_pengangkatan')
    success_message = 'Urutan data berhasil diupdate!'

    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        user = self.request.user
        if nip:
            user = get_user_bynip(nip)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_pengangkatan(self.request.POST, instance=self.object)
        else:
            queryset = self.object.riwayatpengangkatan_set.all()
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_pengangkatan(
                instance=self.object,
                queryset=queryset,
            )
        context = super(UrutkanRiwayatPengangkatanView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Pengangkatan',
            'riwayat':'active',
            'selected':'pengangkatan'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_pengangkatan')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)


class PenempatanRulesMixin:
    """Aturan satu penempatan aktif per pegawai dan state tampilan."""

    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        if not context.get('update_form') and self.request.GET.get('f'):
            context['form_view'] = 'block'
            context['data_view'] = 'none'
        return context

    def save_document(self, form):
        document = form.save(commit=False)
        employee = form.cleaned_data.get('pegawai')
        document.pegawai = employee

        with transaction.atomic():
            employee_documents = RiwayatPenempatan.objects.filter(
                pegawai=employee,
            )
            list(employee_documents.select_for_update().values_list('pk', flat=True))
            if document.status:
                employee_documents.exclude(pk=document.pk).update(status=False)
            document.save()
            form.save_m2m()
        return document


class PenempatanLainnyaMixin(PenempatanRulesMixin):
    def get_form(self, **kwargs):
        if not getattr(self, 'object', None):
            initial = kwargs.setdefault('initial', {})
            initial.setdefault('status', False)
        return super().get_form(**kwargs)


penempatan_document = EmployeeDocumentModule(
    model=RiwayatPenempatan,
    form_class=RiwayatPenempatanForm,
    template_name='5_riwayat_penempatan/riwayat_penempatan_master.html',
    document_url='penempatan',
    selected='penempatan',
    title_page='Penempatan',
    success_url_name='riwayat_urls:riwayat_penempatan',
    file_fields=('file',),
    order_by=('-status', 'no_urut_dokumen'),
)

RiwayatPenempatanView = penempatan_document.manage_view(
    'RiwayatPenempatanView',
    mixins=(PenempatanRulesMixin,),
)
RiwayatPenempatanUpdateView = penempatan_document.update_view(
    'RiwayatPenempatanUpdateView',
    mixins=(PenempatanRulesMixin,),
)
RiwayatPenempatanDeleteView = penempatan_document.delete_view(
    'RiwayatPenempatanDeleteView'
)


penempatan_lainnya_document = EmployeeDocumentModule(
    model=RiwayatPenempatan,
    form_class=RiwayatPenempatanLainnyaForm,
    template_name='5_riwayat_penempatan/riwayat_penempatan_form_create_view.html',
    document_url='penempatan',
    selected='penempatan',
    title_page='Penempatan Instansi Luar RS',
    success_url_name='riwayat_urls:riwayat_penempatan',
    file_fields=('file',),
    order_by=('-status', 'no_urut_dokumen'),
    pk_url_kwarg='pk',
)

RiwayatPenempatanInstansiBeforeCreateView = (
    penempatan_lainnya_document.manage_view(
        'RiwayatPenempatanInstansiBeforeCreateView',
        mixins=(PenempatanLainnyaMixin,),
    )
)
RiwayatPenempatanInstansiBeforUpdateView = (
    penempatan_lainnya_document.update_view(
        'RiwayatPenempatanInstansiBeforUpdateView',
        mixins=(PenempatanLainnyaMixin,),
    )
)


class UrutkanRiwayatPenempatanView(DocumentScopeContextMixin, DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '5_riwayat_penempatan/riwayat_penempatan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penempatan')
    success_message = 'Urutan data berhasil diupdate!'

    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        user = self.request.user
        if nip:
            user = get_user_bynip(nip)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_penempatan(self.request.POST, instance=self.object)
        else:
            queryset = self.object.riwayatpenempatan_set.all()
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_penempatan(
                instance=self.object,
                queryset=queryset,
            )
        context = super(UrutkanRiwayatPenempatanView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penempatan',
            'riwayat':'active',
            'selected':'penempatan'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_penempatan')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class BerkalaRulesMixin:
    """Indikator jatuh tempo kenaikan gaji berkala."""

    def has_management_role(self):
        return is_document_scope_manager(self.request.user)

    def get_selected_employee(self):
        selected_nip = get_selected_nip(self.request)
        if selected_nip:
            return filter_document_users(
                Users.objects.filter(profil_user__nip=selected_nip),
                self.request.user,
            ).first()
        return None if self.has_management_role() else self.request.user

    def get_document_queryset(self):
        queryset = filter_document_queryset(
            self.model.objects.all(), self.request.user
        )
        selected_nip = get_selected_nip(self.request)
        if selected_nip:
            queryset = queryset.filter(pegawai__profil_user__nip=selected_nip)
        return queryset.order_by(*self.order_by)

    def get_accessible_object(self, **lookup):
        return get_object_or_404(
            filter_document_queryset(
                self.model.objects.all(), self.request.user
            ),
            **lookup,
        )

    def get_queryset(self):
        return filter_document_queryset(
            self.model.objects.all(), self.request.user
        )

    def get_latest_tmt_gaji(self, nip):
        if not nip:
            return None
        return (
            RiwayatGajiBerkala.objects
            .filter(
                pegawai__profil_user__nip=nip,
                tmt_gaji__isnull=False,
            )
            .order_by('-tmt_gaji', '-id')
            .values_list('tmt_gaji', flat=True)
            .first()
        )

    def check_status(self, nip):
        latest_tmt = self.get_latest_tmt_gaji(nip)
        if latest_tmt is None:
            return True
        elapsed = relativedelta(date.today(), latest_tmt)
        elapsed_months = (elapsed.years * 12) + elapsed.months
        return elapsed_months >= 21

    def next_berkala(self, nip):
        latest_tmt = self.get_latest_tmt_gaji(nip)
        if latest_tmt is None:
            return None
        return latest_tmt + relativedelta(months=24)

    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        nip = context.get('nip')
        context.update({
            'status_berkala': self.check_status(nip),
            'next_berkala': self.next_berkala(nip),
            'can_manage_berkala_role': self.has_management_role(),
        })
        return context


berkala_document = EmployeeDocumentModule(
    model=RiwayatGajiBerkala,
    form_class=RiwayatGajiBerkalaForm,
    template_name='6_riwayat_berkala/riwayat_berkala_master.html',
    document_url='berkala',
    selected='berkala',
    title_page='Gaji Berkala',
    success_url_name='riwayat_urls:riwayat_berkala',
    file_fields=('file',),
)

RiwayatGajiBerkalaView = berkala_document.manage_view(
    'RiwayatGajiBerkalaView',
    mixins=(BerkalaRulesMixin,),
)
RiwayatGajiBerkalaUpdateView = berkala_document.update_view(
    'RiwayatGajiBerkalaUpdateView',
    mixins=(BerkalaRulesMixin,),
)
RiwayatGajiBerkalaDeleteView = berkala_document.delete_view(
    'RiwayatGajiBerkalaDeleteView',
    mixins=(BerkalaRulesMixin,),
)


class UrutkanRiwayatGajiBerkalaView(DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '6_riwayat_berkala/riwayat_berkala_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_berkala')
    success_message = 'Urutan data berhasil diupdate!'

    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        user = self.request.user
        if nip:
            user = get_user_bynip(nip)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_berkala(
                self.request.POST,
                instance=self.object,
                queryset=scope_document_queryset(
                    self.object.gaji_berkala.all(), self.request.user
                ),
            )
        else:
            queryset = scope_document_queryset(
                self.object.gaji_berkala.all(), self.request.user
            )
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_berkala(
                instance=self.object,
                queryset=queryset,
            )
        context = super(UrutkanRiwayatGajiBerkalaView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Berkala',
            'riwayat':'active',
            'selected':'berkala'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_berkala')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)


class KinerjaContextMixin:
    card_title = 'Riwayat Kinerja'

    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        context['card_title'] = self.card_title
        context['title_page'] = 'Riwayat Kinerja'
        return context


class KinerjaSaveMixin:
    def save_document(self, form):
        form.instance.dokumen = self.get_document_definition()
        return super().save_document(form)


class KinerjaCreateMixin(KinerjaSaveMixin, KinerjaContextMixin):
    card_title = 'Tambah Riwayat Kinerja'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.GET.get('popup') == '1':
            return render(
                self.request,
                'riwayat_pendukung/popup_success.html',
                {
                    'object': self.object,
                    'field_id': self.request.GET.get(
                        'field',
                        'id_kinerja_dua_thn',
                    ),
                    'title_page': 'Tambah Riwayat Kinerja',
                    'success_message': (
                        'Kinerja sudah dimasukkan ke pilihan pada form usulan.'
                    ),
                },
            )
        return response


class KinerjaUpdateMixin(KinerjaSaveMixin, KinerjaContextMixin):
    card_title = 'Ubah Riwayat Kinerja'


kinerja_document = EmployeeDocumentModule(
    model=RiwayatKinerja,
    form_class=RiwayatKinerjaForm,
    template_name='riwayat_kinerja/form.html',
    document_url='kinerja',
    selected='kinerja',
    title_page='Riwayat Kinerja',
    success_url_name='riwayat_urls:riwayat_kinerja',
    file_fields=('file',),
    order_by=('-periode_kinerja_akhir', '-id'),
    select_related=('pegawai', 'kuadran_kinerja', 'nama_penilai'),
)


class UrutkanRiwayatKinerjaView(DocumentScopeContextMixin, DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '7_riwayat_kinerja/riwayat_kinerja_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_kinerja')
    success_message = 'Urutan data berhasil diupdate!'

    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        context = super(UrutkanRiwayatKinerjaView, self).get_context_data(**kwargs)
        nip = get_selected_nip(self.request)
        user = self.request.user
        if nip:
            user = get_user_bynip(nip)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_kinerja(self.request.POST, instance=self.object)
        else:
            queryset = self.object.riwayatkinerja_set.all()
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_kinerja(
                instance=self.object,
                queryset=queryset,
            )
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Kinerja',
            'riwayat':'active',
            'selected':'kinerja'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_kinerja')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)


penghargaan_document = EmployeeDocumentModule(
    model=RiwayatPenghargaan,
    form_class=RiwayatPenghargaanForm,
    template_name='8_riwayat_penghargaan/riwayat_penghargaan_master.html',
    document_url='penghargaan',
    selected='penghargaan',
    title_page='Penghargaan',
    success_url_name='riwayat_urls:riwayat_penghargaan',
    file_fields=('file',),
)

RiwayatPenghargaanView = penghargaan_document.manage_view(
    'RiwayatPenghargaanView'
)
RiwayatPenghargaanUpdateView = penghargaan_document.update_view(
    'RiwayatPenghargaanUpdateView'
)
RiwayatPenghargaanDeleteView = penghargaan_document.delete_view(
    'RiwayatPenghargaanDeleteView'
)


class UrutkanRiwayatPenghargaanView(DocumentScopeContextMixin, DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '8_riwayat_penghargaan/riwayat_penghargaan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penghargaan')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_penghargaan(self.request.POST, instance=self.object)
        else:
            queryset = self.object.riwayatpenghargaan_set.all()
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_penghargaan(
                instance=self.object,
                queryset=queryset,
            )
        context = super(UrutkanRiwayatPenghargaanView, self).get_context_data(**kwargs)
        user = get_user_bynip(nip) if nip else None
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penghargaan',
            'riwayat':'active',
            'selected':'penghargaan'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_penghargaan')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)
hukuman_document = EmployeeDocumentModule(
    model=RiwayatHukuman,
    form_class=RiwayatHukumanForm,
    template_name='9_riwayat_hukuman/riwayat_hukuman_master.html',
    document_url='hukuman',
    selected='hukuman',
    title_page='Hukuman',
    success_url_name='riwayat_urls:riwayat_hukuman',
    file_fields=('file',),
)

RiwayatHukumanView = hukuman_document.manage_view('RiwayatHukumanView')
RiwayatHukumanUpdateView = hukuman_document.update_view(
    'RiwayatHukumanUpdateView'
)
RiwayatHukumanDeleteView = hukuman_document.delete_view(
    'RiwayatHukumanDeleteView'
)


class UrutkanRiwayatHukumanView(DocumentScopeContextMixin, DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '9_riwayat_hukuman/riwayat_hukuman_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_hukuman')
    success_message = 'Urutan data berhasil diupdate!'

    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_hukuman(self.request.POST, instance=self.object)
        else:
            queryset = self.object.riwayathukuman_set.all()
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_hukuman(
                instance=self.object,
                queryset=queryset,
            )
        context = super(UrutkanRiwayatHukumanView, self).get_context_data(**kwargs)
        user = get_user_bynip(nip) if nip else None
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Hukuman',
            'riwayat':'active',
            'selected':'hukuman'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_hukuman')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatCutiView(LoginRequiredMixin, CheckCuti, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        can_manage = bool(
            is_leave_admin(user)
            or is_leave_structural_officer(user)
        )
        requested_nip = (request.GET.get('nip') or '').strip() or None
        target = None
        if requested_nip and can_manage:
            target = filter_users_for_leave_role(
                Users.objects.filter(profil_user__nip=requested_nip),
                user,
                include_self=False,
            ).first()
            if target is None:
                raise Http404('Pegawai tidak ditemukan atau di luar cakupan.')
        elif not can_manage:
            target = user

        data = filter_cuti_history_queryset(
            RiwayatCuti.objects.all(),
            user,
        ).order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='cuti').first()
        initial = {'dokumen':dok}
        if target:
            initial['pegawai'] = target
            data = data.filter(pegawai=target)
        nip = getattr(getattr(target, 'profil_user', None), 'nip', None)
        pegawai_saldo = target
        snapshot_saldo = (
            self.buat_snapshot_saldo_cuti(pegawai_saldo)
            if pegawai_saldo
            else None
        )
        form = RiwayatCutiForm(initial=initial, request=request)
        context={
            'user':pegawai_saldo,
            'data':data,
            'form':form,
            'nip':nip,
            'dok':dok,
            'snapshot_saldo_cuti': snapshot_saldo,
            'cek_sisa_cuti': (
                snapshot_saldo['total_tersedia']
                if snapshot_saldo else None
            ),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Cuti',
            'form_view':'none',
            'data_view':'block',
            'riwayat':'active',
            'selected':'cuti'
        }
        context['can_manage_cuti_role'] = can_manage
        context['document_menu_url'] = reverse('riwayat_urls:riwayat_view')
        return render(request, '10_riwayat_cuti/riwayat_cuti_master.html', context)
    
    def post(self, request, **kwargs):
        form = RiwayatCutiForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.dokumen = DokumenSDM.objects.filter(url='cuti').first()
            instance.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_cuti'))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_cuti'))


class RiwayatCutiUpdateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            return filter_cuti_history_queryset(
                RiwayatCuti.objects.all(),
                self.request.user,
            ).get(id=id)
        except RiwayatCuti.DoesNotExist as exc:
            raise Http404(
                'Riwayat Cuti tidak ditemukan atau tidak dapat diakses.'
            ) from exc
        
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
        if (
            action == 'delete'
            and can_manage_cuti_history(request.user, data_detail)
        ):
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


class RiwayatPenggunaanCutiView(LoginRequiredMixin, CheckCuti, TemplateView):
    template_name = '10_riwayat_cuti/riwayat_cuti_penggunaan.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profil = getattr(self.request.user, 'profil_user', None)
        requested_nip = self.request.GET.get('nip')
        can_manage = bool(
            is_leave_admin(self.request.user)
            or is_leave_structural_officer(self.request.user)
        )
        if requested_nip and can_manage:
            pegawai = filter_users_for_leave_role(
                Users.objects.filter(profil_user__nip=requested_nip),
                self.request.user,
                include_self=False,
            ).first()
        else:
            pegawai = self.request.user
        if pegawai is None:
            raise Http404('Pegawai tidak ditemukan.')

        tahun_sekarang = date.today().year
        snapshot = self.buat_snapshot_saldo_cuti(
            pegawai,
            tahun_sekarang,
        )
        label_keterangan = {
            'N-2': '2 Tahun Lalu',
            'N-1': '1 Tahun Lalu',
            'N': 'Tahun Berjalan',
        }
        ringkasan = []
        for row in snapshot['rows']:
            if row['hak_tunda'] or row['terpakai_tunda']:
                catatan = (
                    f"Hak tunda {row['hak_tunda']} hari; "
                    f"dipakai {row['terpakai_tunda']} hari; "
                    f"sisa {row['sisa_tunda']} hari."
                )
            elif row['label'] in ('N-2', 'N-1'):
                catatan = (
                    f"Kompensasi yang dapat digunakan "
                    f"{row['dapat_digunakan']} hari."
                )
            else:
                catatan = 'Hak cuti tahunan tahun berjalan.'
            ringkasan.append({
                'tahun': row['tahun'],
                'keterangan': label_keterangan[row['label']],
                'hak_awal': row['hak_awal'],
                'terpakai': row['terpakai'],
                'sisa_dapat_diambil': row['dapat_digunakan'],
                'catatan': catatan,
            })

        context['pegawai'] = pegawai
        context['ringkasan_cuti'] = ringkasan
        context['total_hak_tersedia'] = snapshot['total_tersedia']
        context['riwayat_all'] = (
            RiwayatCuti.objects
            .filter(pegawai=pegawai)
            .select_related('usulan')
            .order_by('-tahun_cuti', '-created_at')
        )
        return context

class UrutkanRiwayatCutiView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = DokumenSDM
    template_name = '10_riwayat_cuti/riwayat_cuti_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_cuti')
    success_message = 'Urutan data berhasil diupdate!'

    def get_target_employee(self):
        nip = (self.request.GET.get('nip') or '').strip()
        if not nip:
            return None
        return filter_users_for_leave_role(
            Users.objects.filter(profil_user__nip=nip),
            self.request.user,
            include_self=False,
        ).first()

    def test_func(self):
        return bool(
            (
                is_leave_admin(self.request.user)
                or is_leave_structural_officer(self.request.user)
            )
            and self.get_target_employee() is not None
        )
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        employee = self.get_target_employee()
        queryset = filter_cuti_history_queryset(
            self.object.riwayatcuti_set.filter(pegawai=employee),
            self.request.user,
        )
        urutkan_dokumen_form = urutkan_dokumen_cuti(
            self.request.POST or None,
            instance=self.object,
            queryset=queryset,
        )
        context = super(UrutkanRiwayatCutiView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': employee,
            'nip': getattr(
                getattr(employee, 'profil_user', None),
                'nip',
                None,
            ),
            'document_menu_url': reverse('riwayat_urls:riwayat_cuti'),
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Cuti',
            'riwayat':'active',
            'selected':'cuti'
        })
        return context

    def get_success_url(self):
        employee = self.get_target_employee()
        nip = getattr(getattr(employee, 'profil_user', None), 'nip', None)
        url = reverse('riwayat_urls:riwayat_cuti')
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatCutiMonitoringListView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    CheckCuti,
    ListView,
):
    """Monitoring saldo cuti tahunan seluruh pegawai untuk admin cuti."""
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    model = Users
    template_name = '10_riwayat_cuti/riwayat_cuti_monitoring.html'
    context_object_name = 'pegawai_list'
    paginate_by = 25

    def test_func(self):
        return bool(
            is_leave_admin(self.request.user)
            or is_leave_structural_officer(self.request.user)
        )

    def get_queryset(self):
        queryset = (
            Users.objects.filter(is_active=True)
            .exclude(is_superuser=True)
            .select_related('profil_user')
            .prefetch_related(
                Prefetch(
                    'riwayat_penempatan',
                    queryset=RiwayatPenempatan.objects.filter(status=True)
                    .select_related(
                        'penempatan_level1',
                        'penempatan_level2',
                        'penempatan_level3',
                        'penempatan_level4',
                        'penempatan_level4__sub_bidang',
                        'penempatan_level3__bidang',
                        'penempatan_level2__unor',
                    )
                    .order_by('-updated_at'),
                    to_attr='active_penempatan',
                )
            )
            .order_by('first_name', 'last_name', 'id')
        )
        queryset = filter_users_for_leave_role(
            queryset,
            self.request.user,
            include_self=False,
        )

        keyword = self.request.GET.get('q', '').strip()
        if keyword:
            for term in keyword.split():
                queryset = queryset.filter(
                    Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                    | Q(email__icontains=term)
                    | Q(profil_user__nip__icontains=term)
                )
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tahun = date.today().year
        monitoring_rows = []
        for pegawai in context['pegawai_list']:
            snapshot = self.buat_snapshot_saldo_cuti(pegawai, tahun)
            saldo = {row['label']: row for row in snapshot['rows']}
            monitoring_rows.append({
                'pegawai': pegawai,
                'penempatan': (
                    pegawai.active_penempatan[0].penempatan
                    if pegawai.active_penempatan else '-'
                ),
                'n2': saldo['N-2'],
                'n1': saldo['N-1'],
                'n': saldo['N'],
                'total_tersedia': snapshot['total_tersedia'],
            })

        context.update(
            {
                'monitoring_rows': monitoring_rows,
                'tahun': tahun,
                'q': self.request.GET.get('q', '').strip(),
                'page': 'Home',
                'sub_page': 'Riwayat',
                'title_page': 'Monitoring Sisa Cuti Pegawai',
                'form_view': 'none',
                'data_view': 'block',
                'riwayat': 'active',
                'selected': 'cuti',
            }
        )
        return context
    
        
def get_diklat_employee_queryset(user):
    """Pegawai yang boleh dipantau pada modul Diklat."""
    return filter_users_for_diklat_role(
        Users.objects.all(),
        user,
    )


class DiklatSaveMixin:
    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        context['can_manage_diklat_role'] = bool(
            is_diklat_admin(self.request.user)
            or is_diklat_structural_officer(self.request.user)
        )
        return context

    def get_document_queryset(self):
        queryset = self.model.objects.all()
        if self.order_by:
            queryset = queryset.order_by(*self.order_by)
        return filter_diklat_history_queryset(
            queryset,
            self.request.user,
        )

    def get_accessible_object(self, **lookup):
        try:
            return filter_diklat_history_queryset(
                self.model.objects.all(),
                self.request.user,
            ).get(**lookup)
        except self.model.DoesNotExist as exc:
            raise Http404(
                'Riwayat Diklat tidak ditemukan atau tidak dapat diakses.'
            ) from exc

    def get_queryset(self):
        return filter_diklat_history_queryset(
            self.model.objects.all(),
            self.request.user,
        )

    def get_context(self, form):
        employee = self.object.pegawai.first()
        return self.get_common_context(
            user=employee,
            nip=self.get_employee_nip(employee),
            form=form,
            update_form=True,
            form_view='block',
            data_view='none',
        )

    def get_success_url(self, employee=None):
        if employee is not None and not isinstance(employee, Users):
            employee = employee.first()
        return super().get_success_url(employee)

    def save_document(self, form):
        form.instance.dokumen = self.get_document_definition()
        return super().save_document(form)


diklat_document = EmployeeDocumentModule(
    model=RiwayatDiklat,
    form_class=RiwayatDiklatForm,
    template_name='11_riwayat_diklat/riwayat_diklat_form.html',
    document_url='diklat',
    selected='diklat',
    title_page='Diklat',
    success_url_name='riwayat_urls:riwayat_diklat',
    file_fields=('file', 'file_laporan'),
)


class RiwayatDiklatListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    model = Users
    template_name = '11_riwayat_diklat/riwayat_diklat_list_pegawai.html'
    context_object_name = 'data'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = get_diklat_employee_queryset(self.request.user)
        selected_nip = get_selected_nip(self.request)
        if selected_nip:
            queryset = queryset.filter(profil_user__nip=selected_nip)
        return queryset.filter(
            riwayatdiklat__isnull=False,
        ).values(
            'id',
            'riwayatdiklat__tgl_mulai__year',
            'first_name',
            'last_name',
            'profil_user__nip',
        ).annotate(
            frekuensi_diklat=Count('riwayatdiklat', distinct=True),
            jam_diklat=Sum('riwayatdiklat__jam_pelajaran', distinct=True),
        ).distinct()

    def get_paginate_by(self, queryset):
        if (
            is_diklat_admin(self.request.user)
            or is_diklat_structural_officer(self.request.user)
        ):
            return self.paginate_by
        return None
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page']='Home'
        context['sub_page']='Riwayat'
        context['title_page']='Diklat'
        context['form_view']='none'
        context['data_view']='block'
        context['riwayat']='active'
        context['selected']='diklat'
        context['can_manage_diklat_role'] = bool(
            is_diklat_admin(self.request.user)
            or is_diklat_structural_officer(self.request.user)
        )
        context['server_side_document_pagination'] = bool(
            context['can_manage_diklat_role']
        )
        return context
    

class RiwayatDiklatDetailView(LoginRequiredMixin, DetailView):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    model = Users
    template_name = '11_riwayat_diklat/riwayat_diklat_list_perorang.html'
    context_object_name = 'data'

    def get_queryset(self):
        return get_diklat_employee_queryset(self.request.user).select_related(
            'profil_user',
        ).prefetch_related('riwayatdiklat_set')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page']='Home'
        context['sub_page']='Riwayat'
        context['title_page']='Diklat'
        context['form_view']='none'
        context['data_view']='block'
        context['riwayat']='active'
        context['selected']='diklat'
        context['can_manage_diklat_role'] = bool(
            is_diklat_admin(self.request.user)
            or is_diklat_structural_officer(self.request.user)
        )
        return context


RiwayatDiklatCreateView = diklat_document.create_view(
    'RiwayatDiklatCreateView',
    mixins=(DiklatSaveMixin,),
)


class RiwayatDiklatPegawaiView(LoginRequiredMixin, ListView):
    model = RiwayatDiklat
    template_name = '11_riwayat_diklat/riwayat_diklat_pegawai.html'
    context_object_name = 'data'

    def get_queryset(self):
        return get_diklat_employee_queryset(self.request.user).annotate(
            frekuensi_diklat=Count('riwayatdiklat', distinct=True),
            jam_diklat=Sum('riwayatdiklat__jam_pelajaran', distinct=True),
        )

    def get_context_data(self, **kwargs):
        context = super(RiwayatDiklatPegawaiView, self).get_context_data(**kwargs)
        context.update({
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Diklat',
            'riwayat':'active',
            'selected':'diklat'
        })
        context['can_manage_diklat_role'] = bool(
            is_diklat_admin(self.request.user)
            or is_diklat_structural_officer(self.request.user)
        )
        return context


RiwayatDiklatUpdateView = diklat_document.update_view(
    'RiwayatDiklatUpdateView',
    mixins=(DiklatSaveMixin,),
)


class UrutkanRiwayatDiklatView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = DokumenSDM
    template_name = '11_riwayat_diklat/riwayat_diklat_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_diklat')
    success_message = 'Urutan data berhasil diupdate!'

    def get_target_employee(self):
        nip = (self.request.GET.get('nip') or '').strip()
        if not nip:
            return None
        return filter_users_for_diklat_role(
            Users.objects.filter(profil_user__nip=nip),
            self.request.user,
            include_self=False,
        ).first()

    def test_func(self):
        return bool(
            (
                is_diklat_admin(self.request.user)
                or is_diklat_structural_officer(self.request.user)
            )
            and self.get_target_employee() is not None
        )

    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        user = self.get_target_employee()
        nip = getattr(getattr(user, 'profil_user', None), 'nip', None)
        queryset = filter_diklat_history_queryset(
            self.object.riwayatdiklat_set.filter(pegawai=user),
            self.request.user,
        )
        urutkan_dokumen_form = urutkan_dokumen_diklat(
            self.request.POST or None,
            instance=self.object,
            queryset=queryset.distinct(),
        )
        context = super(UrutkanRiwayatDiklatView, self).get_context_data(**kwargs)
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Diklat',
            'riwayat':'active',
            'selected':'diklat'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_diklat')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)


RiwayatDiklatDeleteView = diklat_document.delete_view(
    'RiwayatDiklatDeleteView',
    template_name='11_riwayat_diklat/riwayat_diklat_master.html',
)
    

kompetensi_document = EmployeeDocumentModule(
    model=Kompetensi,
    form_class=KompetensiForm,
    template_name='18_riwayat_kompetensi/riwayat_kompetensi_master.html',
    document_url='kompetensi',
    selected='kompetensi',
    title_page='Kompetensi',
    success_url_name='riwayat_urls:riwayat_kompetensi',
    file_fields=('file_sert',),
)

RiwayatKompetensiView = kompetensi_document.manage_view(
    'RiwayatKompetensiView'
)
RiwayatKomptensiUpdateView = kompetensi_document.update_view(
    'RiwayatKomptensiUpdateView'
)
RiwayatKompetensiDeleteView = kompetensi_document.delete_view(
    'RiwayatKompetensiDeleteView'
)


class UrutkanRiwayatKompetensiView(DocumentScopeContextMixin, DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '18_riwayat_kompetensi/riwayat_kompetensi_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_kompetensi')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_kompetensi(self.request.POST, instance=self.object)
        else:
            queryset = self.object.kompetensi_set.all()
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_kompetensi(
                instance=self.object,
                queryset=queryset,
            )
        context = super(UrutkanRiwayatKompetensiView, self).get_context_data(**kwargs)
        user = get_user_bynip(nip) if nip else None
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Kompetensi',
            'riwayat':'active',
            'selected':'kompetensi'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_kompetensi')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)


organisasi_document = EmployeeDocumentModule(
    model=RiwayatOrganisasi,
    form_class=RiwayatOrganisasiForm,
    template_name='12_riwayat_organisasi/riwayat_organisasi_master.html',
    document_url='organisasi',
    selected='organisasi',
    title_page='Organisasi',
    success_url_name='riwayat_urls:riwayat_organisasi',
    file_fields=('file',),
)

RiwayatOrganisasiView = organisasi_document.manage_view(
    'RiwayatOrganisasiView'
)
RiwayatOrganisasiUpdateView = organisasi_document.update_view(
    'RiwayatOrganisasiUpdateView'
)
RiwayatOrganisasiDeleteView = organisasi_document.delete_view(
    'RiwayatOrganisasiDeleteView'
)
    

class UrutkanRiwayatOrganisasiView(DocumentScopeContextMixin, DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '12_riwayat_organisasi/riwayat_organisasi_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_organisasi')
    success_message = 'Urutan data berhasil diupdate!'

    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_organisasi(self.request.POST, instance=self.object)
        else:
            queryset = self.object.riwayatorganisasi_set.all()
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_organisasi(
                instance=self.object,
                queryset=queryset,
            )
        context = super(UrutkanRiwayatOrganisasiView, self).get_context_data(**kwargs)
        user = get_user_bynip(nip) if nip else None
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Organisasi',
            'riwayat':'active',
            'selected':'organisasi'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_organisasi')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)


class ProfesiContextMixin:
    def get_selected_employee(self):
        selected_nip = get_selected_nip(self.request)
        if selected_nip:
            return filter_users_for_sip_role(
                Users.objects.filter(profil_user__nip=selected_nip),
                self.request.user,
            ).first()
        if not (
            is_sip_admin(self.request.user)
            or is_sip_structural_officer(self.request.user)
        ):
            return self.request.user
        return None

    def get_document_queryset(self):
        queryset = self.model.objects.select_related(*self.select_related)
        queryset = filter_profession_history_queryset(queryset, self.request.user)
        selected_nip = get_selected_nip(self.request)
        if selected_nip:
            queryset = queryset.filter(pegawai__profil_user__nip=selected_nip)
        return queryset.order_by(*self.order_by)

    def get_accessible_object(self, **lookup):
        return get_object_or_404(
            filter_profession_history_queryset(
                self.model.objects.all(), self.request.user
            ),
            **lookup,
        )

    def get_queryset(self):
        return filter_profession_history_queryset(
            self.model.objects.all(), self.request.user
        )

    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        context['data_str'] = context['data']
        context['str'] = True
        context['can_manage_sip_role'] = bool(
            is_sip_admin(self.request.user)
            or is_sip_structural_officer(self.request.user)
        )
        return context


class ProfesiDeleteMixin(ProfesiContextMixin):
    def form_valid(self, form):
        child_files = [
            (sip.file_sip.storage, sip.file_sip.name)
            for sip in self.object.riwayatsipprofesi_set.all()
            if sip.file_sip and sip.file_sip.name
        ]
        response = super().form_valid(form)
        for storage, name in child_files:
            transaction.on_commit(
                lambda storage=storage, name=name: storage.delete(name),
                robust=True,
            )
        return response


profesi_document = EmployeeDocumentModule(
    model=RiwayatProfesi,
    form_class=RiwayatProfesiForm,
    template_name='13_riwayat_profesi/riwayat_profesi_master.html',
    document_url='profesi',
    selected='profesi',
    title_page='Profesi',
    success_url_name='riwayat_urls:riwayat_profesi',
    file_fields=('file_str',),
    select_related=('pegawai', 'profesi'),
)

RiwayatProfesiView = profesi_document.manage_view(
    'RiwayatProfesiView',
    mixins=(ProfesiContextMixin,),
)
RiwayatProfesiUpdateView = profesi_document.update_view(
    'RiwayatProfesiUpdateView',
    mixins=(ProfesiContextMixin,),
)
RiwayatProfesiDeleteView = profesi_document.delete_view(
    'RiwayatProfesiDeleteView',
    mixins=(ProfesiDeleteMixin,),
)


class RiwayatSIPProfesiView(LoginRequiredMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def get_str_object(self, id):
        return get_object_or_404(
            filter_profession_history_queryset(
                RiwayatProfesi.objects.all(), self.request.user
            ),
            pk=id,
        )
        
    def get(self, request, **kwargs):
        id_str = kwargs.get('id')
        str_obj = self.get_str_object(id_str)
        data = str_obj.riwayatsipprofesi_set.all().order_by('no_urut_dokumen')
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
        context['can_manage_sip_role'] = bool(
            is_sip_admin(request.user)
            or is_sip_structural_officer(request.user)
        )
        return render(request, '13_riwayat_profesi/riwayat_profesi_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        str_obj = self.get_str_object(id)
        form = RiwayatSIPProfesiForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            sip = form.save(commit=False)
            sip.riwayat_profesi = str_obj
            sip.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_sipprofesi', kwargs={'id':id}))
        else:
            messages.error(request, form_not_valid_message)
            return redirect(reverse('riwayat_urls:riwayat_sipprofesi', kwargs={'id':id}))


class RiwayatSIPProfesiUpdateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def get_str_object(self, id):
        return get_object_or_404(
            filter_profession_history_queryset(
                RiwayatProfesi.objects.all(), self.request.user
            ),
            pk=id,
        )

    def get_object(self, id, id_str):
        return get_object_or_404(
            filter_profession_sip_queryset(
                RiwayatSIPProfesi.objects.all(), self.request.user
            ),
            pk=id,
            riwayat_profesi_id=id_str,
        )
    
    def get(self, request, **kwargs):
        id = kwargs.get('id')
        id_str = kwargs.get('id_str')
        self.get_str_object(id_str)
        instance = self.get_object(id, id_str)
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
        context['can_manage_sip_role'] = bool(
            is_sip_admin(request.user)
            or is_sip_structural_officer(request.user)
        )
        return render(request, '13_riwayat_profesi/riwayat_profesi_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        id_str = kwargs.get('id_str')
        str_obj = self.get_str_object(id_str)
        instance = self.get_object(id, id_str)
        old_file = None
        if instance.file_sip and instance.file_sip.name:
            old_file = (instance.file_sip.storage, instance.file_sip.name)
        form = RiwayatSIPProfesiForm(data=request.POST, files=request.FILES, instance=instance)
        if form.is_valid():
            riwayat_sipprofesi = form.save(commit=False)
            riwayat_sipprofesi.riwayat_profesi = str_obj
            with transaction.atomic():
                riwayat_sipprofesi.save()
                if (
                    old_file
                    and old_file[1] != riwayat_sipprofesi.file_sip.name
                ):
                    transaction.on_commit(
                        lambda storage=old_file[0], name=old_file[1]: storage.delete(name),
                        robust=True,
                    )
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_sipprofesi', kwargs={'id':str_obj.id}))
        else:
            messages.error(request, form_not_valid_message)
            return render(
                request,
                '13_riwayat_profesi/riwayat_profesi_master.html',
                {
                    'update_form': True,
                    'form': form,
                    'id_str': id_str,
                    'page': 'Home',
                    'sub_page': 'Riwayat',
                    'title_page': 'Profesi',
                    'form_view': 'block',
                    'data_view': 'none',
                    'riwayat': 'active',
                    'sip': True,
                    'selected': 'profesi',
                },
                status=400,
            )


class UrutkanRiwayatSIPProfesiView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = RiwayatProfesi
    template_name = '13_riwayat_profesi/riwayat_sip_urutkan_dokumen.html'
    success_message = 'Urutan data berhasil diupdate!'

    def get_queryset(self):
        return filter_profession_history_queryset(
            RiwayatProfesi.objects.all(), self.request.user
        )

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
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class RiwayatSIPDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = RiwayatSIPProfesi
    template_name = '13_riwayat_profesi/riwayat_profesi_master.html'
    success_message = "Data berhasil dihapus!"

    def get_queryset(self):
        return filter_profession_sip_queryset(
            RiwayatSIPProfesi.objects.all(), self.request.user
        ).filter(
            riwayat_profesi_id=self.kwargs['id_str'],
        )

    def get_success_url(self, **kwargs) -> str:
        success_url = reverse_lazy('riwayat_urls:riwayat_sipprofesi', kwargs={'id':self.kwargs.get('id_str')})
        return success_url
    
    def get_context_data(self, **kwargs):
        id_str = self.kwargs.get('id_str')
        data = self.object.riwayat_profesi.riwayatsipprofesi_set.all().order_by(
            'no_urut_dokumen',
        )
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
        file_data = None
        if self.object.file_sip and self.object.file_sip.name:
            file_data = (self.object.file_sip.storage, self.object.file_sip.name)
        with transaction.atomic():
            response = super().form_valid(form)
            if file_data:
                transaction.on_commit(
                    lambda storage=file_data[0], name=file_data[1]: storage.delete(name),
                    robust=True,
                )
        return response


class RiwayatBekerjaView(LoginRequiredMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def get(self, request, **kwargs):
        user = request.user
        selected_nip = get_selected_nip(request)
        data = RiwayatBekerja.objects.all().order_by('no_urut_dokumen')
        dok = DokumenSDM.objects.filter(url='bekerja').first()
        initial = {'dokumen':dok}
        nip=None
        if not request.user.is_dokumen_admin:
            nip = get_nip(user)
            initial = {'pegawai':user, 'dokumen':dok}
            if nip:
                data = RiwayatBekerja.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
            else:
                return redirect(reverse(notfoundview, kwargs={'bagian':'riwayat', 'selected':'bekerja'}))
        if selected_nip:
            nip = selected_nip
            data = RiwayatBekerja.objects.filter(pegawai__profil_user__nip=nip).order_by('no_urut_dokumen')
        page_obj = None
        if request.user.is_dokumen_admin and not selected_nip:
            paginator = Paginator(data, 25)
            page_obj = paginator.get_page(request.GET.get('page'))
            data = page_obj.object_list
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
        if page_obj is not None:
            context.update({
                'paginator': page_obj.paginator,
                'page_obj': page_obj,
                'is_paginated': page_obj.has_other_pages(),
                'server_side_document_pagination': True,
            })
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
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    def get_object(self, id, request=None):
        try:
            data = get_accessible_document(RiwayatBekerja, self.request.user, id=id)
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


class UrutkanRiwayatBekerjaView(DocumentScopeContextMixin, DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '14_riwayat_bekerja/riwayat_bekerja_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_bekerja')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
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


class RiwayatBekerjaDeleteView(DocumentObjectAccessMixin, SuccessMessageMixin, DeleteView):
    model = RiwayatBekerja
    template_name = '14_riwayat_bekerja/riwayat_bekerja_master.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_bekerja')
    success_message = "Data berhasil dihapus!"

    def get_context_data(self, **kwargs):
        user = self.request.user
        dok = DokumenSDM.objects.filter(url='bekerja').first()
        nip = None
        if self.request.user.is_dokumen_admin:
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


class KeluargaContextMixin:
    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        if self.request.GET.get('form') == 'block' and not extra.get('update_form'):
            context['form_view'] = 'block'
            context['data_view'] = 'none'
        if extra.get('update_form') and getattr(self, 'object', None) is not None:
            context['detail'] = self.object
        return context


class KeluargaDeleteMixin(KeluargaContextMixin):
    def form_valid(self, form):
        pasangan_files = [
            (pasangan.file_akte_nikah.storage, pasangan.file_akte_nikah.name)
            for pasangan in self.object.pasangan_set.all()
            if pasangan.file_akte_nikah and pasangan.file_akte_nikah.name
        ]
        with transaction.atomic():
            self.object.orangtua_set.all().delete()
            self.object.pasangan_set.all().delete()
            self.object.anak_set.all().delete()
            response = super().form_valid(form)
            for storage, name in pasangan_files:
                transaction.on_commit(
                    lambda storage=storage, name=name: storage.delete(name),
                    robust=True,
                )
        return response


keluarga_document = EmployeeDocumentModule(
    model=RiwayatKeluarga,
    form_class=RiwayatKeluargaForm,
    template_name='15_riwayat_keluarga/riwayat_keluarga_master.html',
    document_url='keluarga',
    selected='keluarga',
    title_page='Keluarga',
    success_url_name='riwayat_urls:riwayat_keluarga',
    file_fields=('file',),
    select_related=('pegawai',),
)

RiwayatKeluargaView = keluarga_document.manage_view(
    'RiwayatKeluargaView',
    mixins=(KeluargaContextMixin,),
)
RiwayatKeluargaUpdateView = keluarga_document.update_view(
    'RiwayatKeluargaUpdateView',
    mixins=(KeluargaContextMixin,),
)
RiwayatKeluargaDeleteView = keluarga_document.delete_view(
    'RiwayatKeluargaDeleteView',
    mixins=(KeluargaDeleteMixin,),
)


class RiwayatAnggotaKeluargaView(LoginRequiredMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    @staticmethod
    def normalize_status(status):
        status = (status or '').lower()
        if status not in {'orang-tua', 'pasangan', 'anak'}:
            raise Http404('Jenis anggota keluarga tidak valid.')
        return status

    def get_object(self, id, request=None):
        try:
            data = get_accessible_document(RiwayatKeluarga, self.request.user, id=id)
            return data
        except RiwayatKeluarga.DoesNotExist:
            messages.error(request, 'Mohon maaf detail riwayat keluarga tidak ditemukan!')
            return None
        
    def get(self, request, **kwargs):
        keluarga_id = kwargs.get('keluarga_id')
        get_status: str = kwargs.get('status')
        get_form = request.GET.get('form')
        form_view = 'none'
        data_view = 'block'
        if get_form == 'block':
            form_view = 'block'
            data_view = 'none'
        status = self.normalize_status(get_status)
        keluarga = self.get_object(keluarga_id, request)
        initial = {'keluarga': keluarga}
        if status == 'pasangan':
            data = Pasangan.objects.filter(keluarga=keluarga)
            form = RiwayatKeluargaPasanganForm(initial=initial)
        elif status == 'anak':
            data = Anak.objects.filter(keluarga=keluarga)
            form = RiwayatKeluargaAnakForm(initial=initial)
        else:
            data = OrangTua.objects.filter(keluarga=keluarga)
            form = RiwayatKeluargaOrangTuaForm(initial=initial)

        context={
            'pegawai': keluarga,
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
            'selected':'keluarga',
            'document_menu_url': get_riwayat_menu_url(request, keluarga.pegawai),
        }
        return render(request, '16_riwayat_anggota_keluarga/riwayat_anggota_keluarga_master.html', context)
    
    def post(self, request, **kwargs):
        keluarga_id = kwargs.get('keluarga_id')
        status = self.normalize_status(kwargs.get('status'))
        keluarga = self.get_object(keluarga_id, request)
        if status == 'orang-tua':
            form = RiwayatKeluargaOrangTuaForm(data=request.POST, files=request.FILES)
        elif status == 'pasangan':
            form = RiwayatKeluargaPasanganForm(data=request.POST, files=request.FILES)
        else:
            form = RiwayatKeluargaAnakForm(data=request.POST, files=request.FILES)

        if form.is_valid():
            anggota = form.save(commit=False)
            anggota.keluarga = keluarga
            anggota.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_anggota_keluarga', kwargs={'status':status, 'keluarga_id':keluarga_id}))
        messages.error(request, form_not_valid_message)
        return redirect(reverse('riwayat_urls:riwayat_anggota_keluarga', kwargs={'status':status, 'keluarga_id':keluarga_id}))


class RiwayatAnggotaKeluargaUpdateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'

    normalize_status = staticmethod(RiwayatAnggotaKeluargaView.normalize_status)

    def get_object(self, id, request=None):
        try:
            data = get_accessible_document(RiwayatKeluarga, self.request.user, id=id)
            return data
        except RiwayatKeluarga.DoesNotExist:
            messages.error(request, 'Mohon maaf detail riwayat keluarga tidak ditemukan!')
            return None
        
    def get_instance(self, id, status, keluarga_id):
        lookup = {'pk': id, 'keluarga_id': keluarga_id}
        if status == 'pasangan':
            return get_accessible_document(Pasangan, self.request.user, **lookup)
        if status == 'anak':
            return get_accessible_document(Anak, self.request.user, **lookup)
        return get_accessible_document(OrangTua, self.request.user, **lookup)
        
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
        status = self.normalize_status(get_status)
        keluarga = self.get_object(keluarga_id, request)
        instance = self.get_instance(id, status, keluarga_id)
        if status == 'pasangan':
            form = RiwayatKeluargaPasanganForm(instance=instance)
        elif status == 'anak':
            form = RiwayatKeluargaAnakForm(instance=instance)
        else:
            form = RiwayatKeluargaOrangTuaForm(instance=instance)

        context={
            'update_form':True,
            'pegawai': keluarga,
            'keluarga_id':keluarga_id,
            'form':form,
            'status':status,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Keluarga',
            'form_view':form_view,
            'data_view':data_view,
            'riwayat':'active',
            'selected':'keluarga',
            'document_menu_url': get_riwayat_menu_url(request, keluarga.pegawai),
        }
        return render(request, '16_riwayat_anggota_keluarga/riwayat_anggota_keluarga_master.html', context)
    
    def post(self, request, **kwargs):
        id = kwargs.get('id')
        keluarga_id = kwargs.get('keluarga_id')
        status = self.normalize_status(kwargs.get('status'))
        keluarga = self.get_object(keluarga_id, request)
        data_detail = self.get_instance(id, status, keluarga_id)
        instance = self.get_instance(id, status, keluarga_id)
        if status == 'orang-tua':
            form = RiwayatKeluargaOrangTuaForm(data=request.POST, files=request.FILES, instance=instance)
        elif status == 'pasangan':
            form = RiwayatKeluargaPasanganForm(data=request.POST, files=request.FILES, instance=instance)
        else:
            form = RiwayatKeluargaAnakForm(data=request.POST, files=request.FILES, instance=instance)

        if form.is_valid():
            if status == 'pasangan':
                riwayat_pasangan = form.save(commit=False)
                riwayat_pasangan.keluarga = keluarga
                if riwayat_pasangan.file_akte_nikah and data_detail.file_akte_nikah and data_detail.file_akte_nikah != riwayat_pasangan.file_akte_nikah and os.path.isfile(data_detail.file_akte_nikah.path):
                    os.remove(data_detail.file_akte_nikah.path)
                riwayat_pasangan.save()
            else:
                anggota = form.save(commit=False)
                anggota.keluarga = keluarga
                anggota.save()
            messages.success(request, save_success_message)
            return redirect(reverse('riwayat_urls:riwayat_anggota_keluarga', kwargs={'status':status, 'keluarga_id':keluarga_id}))
        messages.error(request, form_not_valid_message)
        return redirect(reverse('riwayat_urls:riwayat_anggota_keluarga', kwargs={'status':status, 'keluarga_id':keluarga_id}))


class RiwayatOrangTuaDeleteView(DocumentObjectAccessMixin, SuccessMessageMixin, DeleteView):
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


class InovasiContextMixin:
    def has_management_role(self):
        return bool(
            is_inovasi_admin(self.request.user)
            or is_inovasi_structural_officer(self.request.user)
        )

    def get_selected_employee(self):
        nip = get_selected_nip(self.request)
        if nip:
            return filter_users_for_inovasi_role(
                Users.objects.filter(profil_user__nip=nip),
                self.request.user,
            ).first()
        return None if self.has_management_role() else self.request.user

    def get_document_queryset(self):
        queryset = filter_inovasi_queryset(
            self.model.objects.select_related(*self.select_related),
            self.request.user,
        )
        nip = get_selected_nip(self.request)
        if nip:
            queryset = queryset.filter(pegawai__profil_user__nip=nip)
        return queryset.order_by(*self.order_by)

    def get_queryset(self):
        return filter_inovasi_queryset(
            self.model.objects.all(), self.request.user
        )

    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        context.update({
            'form': None,
            'form_view': 'none',
            'data_view': 'block',
            'can_manage_inovasi_role': self.has_management_role(),
        })
        return context


inovasi_document = EmployeeDocumentModule(
    model=RiwayatInovasi,
    form_class=None,
    template_name='17_riwayat_inovasi/riwayat_inovasi_master.html',
    document_url='inovasi',
    selected='inovasi',
    title_page='Inovasi',
    success_url_name='riwayat_urls:riwayat_inovasi',
    file_fields=('makalah', 'file_sk'),
    select_related=('pegawai', 'bidang'),
)

RiwayatInovasiView = inovasi_document.list_view(
    'RiwayatInovasiView',
    mixins=(InovasiContextMixin,),
)
RiwayatInovasiDeleteView = inovasi_document.delete_view(
    'RiwayatInovasiDeleteView',
    mixins=(InovasiContextMixin,),
)


class UrutkanRiwayatInovasiView(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '17_riwayat_inovasi/riwayat_inovasi_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_inovasi')
    success_message = 'Urutan data berhasil diupdate!'

    def test_func(self):
        nip = get_selected_nip(self.request)
        if not nip:
            return True
        return filter_users_for_inovasi_role(
            Users.objects.filter(profil_user__nip=nip), self.request.user
        ).exists()
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_inovasi(
                self.request.POST,
                instance=self.object,
                queryset=filter_inovasi_queryset(
                    self.object.riwayatinovasi_set.all(), self.request.user
                ),
            )
        else:
            queryset = filter_inovasi_queryset(
                self.object.riwayatinovasi_set.all(), self.request.user
            )
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_inovasi(
                instance=self.object,
                queryset=queryset,
            )
        context = super(UrutkanRiwayatInovasiView, self).get_context_data(**kwargs)
        user = get_user_bynip(nip) if nip else None
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Inovasi',
            'riwayat':'active',
            'selected':'inovasi'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_inovasi')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            urutkan_dokumen_form.instance = self.object
            urutkan_dokumen_form.save()
        return super().form_valid(form)
    

class PenugasanContextMixin:
    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        context['object_list'] = context['data']
        return context


class PenugasanFormMixin(PenugasanContextMixin):
    def get_form(self, **kwargs):
        employee = self.get_selected_employee()
        initial_values = {'dokumen': self.get_document_definition()}
        if employee is not None:
            initial_values['pegawai'] = employee
        if getattr(self, 'object', None) is not None:
            kwargs.setdefault('instance', self.object)
        kwargs['user'] = self.request.user
        kwargs['initial_values'] = initial_values
        return self.form_class(**kwargs)

    def get_common_context(self, **extra):
        context = super().get_common_context(**extra)
        context['add_form'] = True
        return context

    def save_document(self, form):
        form.instance.dokumen = self.get_document_definition()
        return super().save_document(form)


penugasan_document = EmployeeDocumentModule(
    model=RiwayatPenugasan,
    form_class=RiwayatPenugasanForm,
    template_name='19_riwayat_penugasan/riwayat_penugasan_master.html',
    document_url='penugasan',
    selected='penugasan',
    title_page='Penugasan',
    success_url_name='riwayat_urls:riwayat_penugasan',
    file_fields=('file_spt',),
    pk_url_kwarg='pk',
    select_related=('pegawai', 'jabatan', 'panggol'),
)

RiwayatPenugasanListView = penugasan_document.list_view(
    'RiwayatPenugasanListView'
)
RiwayatPenugasanCreateView = penugasan_document.create_view(
    'RiwayatPenugasanCreateView',
    mixins=(PenugasanFormMixin,),
)
RiwayatPenugasanUpdateView = penugasan_document.update_view(
    'RiwayatPenugasanUpdateView',
    mixins=(PenugasanFormMixin,),
)
RiwayatPenugasanDeleteView = penugasan_document.delete_view(
    'RiwayatPenugasanDeleteView',
    mixins=(PenugasanContextMixin,),
)


class UrutkanRiwayatPenugasanView(DocumentScopeContextMixin, DocumentAdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DokumenSDM
    template_name = '19_riwayat_penugasan/riwayat_penugasan_urutkan_dokumen.html'
    success_url = reverse_lazy('riwayat_urls:riwayat_penugasan')
    success_message = 'Urutan data berhasil diupdate!'
    
    def get_form_class(self):
        form = UrutkanDokumenSDMForm
        return form

    def get_context_data(self, **kwargs):
        nip = get_selected_nip(self.request)
        if self.request.POST:
            urutkan_dokumen_form = urutkan_dokumen_penugasan(self.request.POST, instance=self.object)
        else:
            queryset = self.object.riwayatpenugasan_set.all()
            if nip:
                queryset = queryset.filter(pegawai__profil_user__nip=nip)
            urutkan_dokumen_form = urutkan_dokumen_penugasan(
                instance=self.object,
                queryset=queryset,
            )
        context = super(UrutkanRiwayatPenugasanView, self).get_context_data(**kwargs)
        user = get_user_bynip(nip) if nip else None
        context.update({
            'urutkan_dokumen_form':urutkan_dokumen_form,
            'user': user,
            'nip': nip,
            'page':'Home',
            'sub_page':'Riwayat',
            'title_page':'Penugasan',
            'riwayat':'active',
            'selected':'penugasan'
        })
        return context

    def get_success_url(self):
        url = reverse('riwayat_urls:riwayat_penugasan')
        nip = get_selected_nip(self.request)
        return f'{url}?nip={nip}' if nip else url

    def form_valid(self, form):
        context = self.get_context_data()
        urutkan_dokumen_form = context['urutkan_dokumen_form']
        if not urutkan_dokumen_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
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


class RiwayatUjiKompetensiListView(LoginRequiredMixin, ListView):
    model = UjiKompetensi
    template_name = 'riwayat_ujikom/list.html'
    context_object_name = 'data'
    paginate_by = 20

    def get_queryset(self):
        queryset = UjiKompetensi.objects.select_related(
            'pegawai', 'kompetensi', 'kompetensi__jenis_sdm'
        ).order_by('-tgl_sert_ujikomp', '-id')
        return filter_document_queryset(queryset, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Riwayat Uji Kompetensi',
            'title_page': 'Riwayat Uji Kompetensi',
            'riwayat': 'active',
            'selected': 'ujikomp',
            'server_side_document_pagination': True,
            'can_manage_document_scope': is_document_scope_manager(self.request.user),
        })
        return context


class RiwayatUjiKompetensiCreateView(LoginRequiredMixin, CreateView):
    model = UjiKompetensi
    form_class = UjiKompetensiForm
    template_name = 'riwayat_ujikom/form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if not is_document_scope_manager(self.request.user):
            initial['pegawai'] = self.request.user
        return initial

    def form_valid(self, form):
        if not is_document_scope_manager(self.request.user):
            form.instance.pegawai = self.request.user
        response = super().form_valid(form)
        if self.request.GET.get('popup') == '1':
            return render(self.request, 'riwayat_pendukung/popup_success.html', {
                'object': self.object,
                'field_id': self.request.GET.get('field', 'id_kompetensi'),
                'title_page': 'Tambah Riwayat Uji Kompetensi',
                'success_message': 'Uji kompetensi sudah dimasukkan ke pilihan pada form usulan.',
            })
        messages.success(self.request, 'Riwayat uji kompetensi berhasil ditambahkan.')
        return response

    def get_success_url(self):
        return preserve_return_url(
            self.request,
            reverse('riwayat_urls:riwayat_ujikom'),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Tambah Riwayat Uji Kompetensi',
            'title_page': 'Riwayat Uji Kompetensi',
            'riwayat': 'active',
            'selected': 'ujikomp',
            'document_menu_url': get_riwayat_menu_url(self.request),
            'can_manage_document_scope': is_document_scope_manager(self.request.user),
        })
        return context


class RiwayatUjiKompetensiUpdateView(LoginRequiredMixin, UpdateView):
    model = UjiKompetensi
    form_class = UjiKompetensiForm
    template_name = 'riwayat_ujikom/form.html'

    def get_queryset(self):
        return filter_document_queryset(
            UjiKompetensi.objects.all(), self.request.user
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        if not is_document_scope_manager(self.request.user):
            form.instance.pegawai = self.request.user

        old_file = None
        if self.object.file_sert and 'file_sert' in self.request.FILES:
            old_file = (self.object.file_sert.storage, self.object.file_sert.name)

        with transaction.atomic():
            response = super().form_valid(form)
            if old_file and old_file[1] != self.object.file_sert.name:
                transaction.on_commit(
                    lambda storage=old_file[0], name=old_file[1]: storage.delete(name),
                    robust=True,
                )

        messages.success(self.request, 'Riwayat uji kompetensi berhasil diperbarui.')
        return response

    def get_success_url(self):
        return preserve_return_url(
            self.request,
            reverse('riwayat_urls:riwayat_ujikom'),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Ubah Riwayat Uji Kompetensi',
            'title_page': 'Riwayat Uji Kompetensi',
            'riwayat': 'active',
            'selected': 'ujikomp',
            'document_menu_url': get_riwayat_menu_url(
                self.request,
                self.object.pegawai,
            ),
            'can_manage_document_scope': is_document_scope_manager(self.request.user),
        })
        return context


class RiwayatUjiKompetensiDeleteView(LoginRequiredMixin, DeleteView):
    model = UjiKompetensi
    template_name = 'riwayat_ujikom/confirm_delete.html'

    def get_queryset(self):
        return filter_document_queryset(
            UjiKompetensi.objects.all(), self.request.user
        )

    def form_valid(self, form):
        file_data = None
        if self.object.file_sert:
            file_data = (self.object.file_sert.storage, self.object.file_sert.name)

        with transaction.atomic():
            response = super().form_valid(form)
            if file_data:
                transaction.on_commit(
                    lambda storage=file_data[0], name=file_data[1]: storage.delete(name),
                    robust=True,
                )

        messages.success(self.request, 'Riwayat uji kompetensi berhasil dihapus.')
        return response

    def get_success_url(self):
        return reverse('riwayat_urls:riwayat_ujikom')


class RiwayatPAKListView(LoginRequiredMixin, ListView):
    model = RiwayatPAK
    template_name = 'riwayat_pak/list.html'
    context_object_name = 'data'
    paginate_by = 20

    def get_queryset(self):
        queryset = RiwayatPAK.objects.select_related('pegawai').order_by('-tgl_srt', '-id')
        return filter_document_queryset(queryset, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Riwayat Penetapan Angka Kredit (PAK)',
            'title_page': 'Riwayat PAK',
            'riwayat': 'active',
            'selected': 'pak',
            'server_side_document_pagination': True,
            'can_manage_document_scope': is_document_scope_manager(self.request.user),
        })
        return context


class RiwayatPAKCreateView(LoginRequiredMixin, CreateView):
    model = RiwayatPAK
    form_class = RiwayatPAKForm
    template_name = 'riwayat_pak/form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if not is_document_scope_manager(self.request.user):
            initial['pegawai'] = self.request.user
        return initial

    def form_valid(self, form):
        if not is_document_scope_manager(self.request.user):
            form.instance.pegawai = self.request.user
        form.instance.dokumen = DokumenSDM.objects.filter(url='pak').first()
        response = super().form_valid(form)
        if self.request.GET.get('popup') == '1':
            return render(self.request, 'riwayat_pendukung/popup_success.html', {
                'object': self.object,
                'field_id': self.request.GET.get('field', 'id_pak'),
                'title_page': 'Tambah Riwayat PAK',
                'success_message': 'PAK sudah dimasukkan ke pilihan pada form usulan.',
            })
        messages.success(self.request, 'Riwayat PAK berhasil ditambahkan.')
        return response

    def get_success_url(self):
        return preserve_return_url(
            self.request,
            reverse('riwayat_urls:riwayat_pak'),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Tambah Riwayat PAK',
            'title_page': 'Riwayat PAK',
            'riwayat': 'active',
            'selected': 'pak',
            'document_menu_url': get_riwayat_menu_url(self.request),
            'can_manage_document_scope': is_document_scope_manager(self.request.user),
        })
        return context


class RiwayatPAKUpdateView(LoginRequiredMixin, UpdateView):
    model = RiwayatPAK
    form_class = RiwayatPAKForm
    template_name = 'riwayat_pak/form.html'

    def get_queryset(self):
        return filter_document_queryset(
            RiwayatPAK.objects.all(), self.request.user
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        if not is_document_scope_manager(self.request.user):
            form.instance.pegawai = self.request.user
        old_file = None
        if self.object.file and 'file' in self.request.FILES:
            old_file = (self.object.file.storage, self.object.file.name)
        with transaction.atomic():
            response = super().form_valid(form)
            if old_file and old_file[1] != self.object.file.name:
                transaction.on_commit(
                    lambda storage=old_file[0], name=old_file[1]: storage.delete(name),
                    robust=True,
                )
        messages.success(self.request, 'Riwayat PAK berhasil diperbarui.')
        return response

    def get_success_url(self):
        return preserve_return_url(
            self.request,
            reverse('riwayat_urls:riwayat_pak'),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'card_title': 'Ubah Riwayat PAK',
            'title_page': 'Riwayat PAK',
            'riwayat': 'active',
            'selected': 'pak',
            'document_menu_url': get_riwayat_menu_url(
                self.request,
                self.object.pegawai,
            ),
            'can_manage_document_scope': is_document_scope_manager(self.request.user),
        })
        return context


class RiwayatPAKDeleteView(LoginRequiredMixin, DeleteView):
    model = RiwayatPAK
    template_name = 'riwayat_pak/confirm_delete.html'

    def get_queryset(self):
        return filter_document_queryset(
            RiwayatPAK.objects.all(), self.request.user
        )

    def form_valid(self, form):
        file_data = None
        if self.object.file:
            file_data = (self.object.file.storage, self.object.file.name)
        with transaction.atomic():
            response = super().form_valid(form)
            if file_data:
                transaction.on_commit(
                    lambda storage=file_data[0], name=file_data[1]: storage.delete(name),
                    robust=True,
                )
        messages.success(self.request, 'Riwayat PAK berhasil dihapus.')
        return response

    def get_success_url(self):
        return reverse('riwayat_urls:riwayat_pak')


RiwayatKinerjaListView = kinerja_document.list_view(
    'RiwayatKinerjaListView',
    mixins=(KinerjaContextMixin,),
    template_name='riwayat_kinerja/list.html',
)
RiwayatKinerjaCreateView = kinerja_document.create_view(
    'RiwayatKinerjaCreateView',
    mixins=(KinerjaCreateMixin,),
)
RiwayatKinerjaBaruUpdateView = kinerja_document.update_view(
    'RiwayatKinerjaBaruUpdateView',
    mixins=(KinerjaUpdateMixin,),
)
RiwayatKinerjaBaruDeleteView = kinerja_document.delete_view(
    'RiwayatKinerjaBaruDeleteView',
    mixins=(KinerjaContextMixin,),
    template_name='riwayat_kinerja/confirm_delete.html',
)
