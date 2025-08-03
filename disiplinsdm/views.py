from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.db import transaction
from django.views import View, generic
from django.views.generic.edit import FormView
from django.db.models.query import QuerySet
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Sum, Case, When, F, Q, Min, Max, Value, CharField, Count
from django.db.models.functions import Extract, Cast, TruncDate
from django.core.paginator import Paginator
from django.contrib.staticfiles import finders
from django.db.models.fields import TimeField
# from django.db.models.functions import TruncMonth, ExtractMonth, TruncDate, TruncYear
from django.utils.functional import cached_property
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from datetime import date, datetime, time, timedelta
from django.utils.timezone import make_aware, localtime
from openpyxl.utils.datetime import from_excel
import pandas as pd
import os
from calendar import monthrange, month_name
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from django.http import HttpResponse
from collections import defaultdict
from decimal import Decimal
from django.utils import timezone
from openpyxl.drawing.image import Image as XLImage


from .utils import get_mingguan_lengkap, hitung_total_jam, is_user_authorized_to_approve
from openpyxl import load_workbook
import calendar
import qrcode
from io import BytesIO
import base64
from PIL import Image
from openpyxl.utils import get_column_letter


from strukturorg.models import SatuanKerjaInduk, UnitOrganisasi, Bidang, SubBidang

from .models import (
    JenisSDMPerinstalasi, 
    JadwalDinasSDM, 
    ApprovedJadwalDinasSDM,
    DaftarKegiatanPegawai, 
    AlasanTidakHadir, 
    KehadiranKegiatan, 
    JenisKegiatan,
    DetailKategoriJadwalDinas,
    HariLibur,
)
from dokumen.models import RiwayatPenempatan, RiwayatJabatan
from strukturorg.models import UnitInstalasi
from myaccount.models import Users, ProfilSDM
from .forms import (
    HariLiburForm,
    jadwal_formset, 
    update_jadwal_formset,
    jumlah_hari_dalam_bulan, 
    JenisSDMPerinstalasiBasicForm,
    JenisSDMPerinstalasiForm, 
    JenisSDMPerinstalasiCustomForm, 
    DaftarKegiatanPegawaiForm,
    kehadiran_formset,
    UploadFingerprintForm,
    FormCopyJadwalSDM,
    SalinJadwalForm,
    SalinJadwalInstalasiForm,
    SearchForm,
    PengajuanJadwalForm,
    PersetujuanForm,
    )

# Create your views here.
notfoundview = 'riwayat_urls:notfound_view'

def get_nip(user):
    try:
        nip = user.profil_user.nip
        return nip
    except Exception:
        return None

def get_date_from_string(tanggal):
    tanggal_sekarang = datetime.now()
    try:
        get_tanggal = datetime.strptime(tanggal, "%Y-%m-%d").date()
        return get_tanggal
    except Exception:
        return tanggal_sekarang
    
def get_day_in_a_month():
    sekarang = date.today().replace(day=1)
    tanggal = [sekarang + relativedelta(day=i) for i in range(jumlah_hari_dalam_bulan())]
    return tanggal


def get_evaluasi_tabel(inst_id, users, bulan=None, tahun=None):
    today = date.today()
    bulan = bulan or today.month
    tahun = tahun or today.year
    jumlah_hari = monthrange(tahun, bulan)[1]

    try:
        instalasi = UnitInstalasi.objects.get(pk=inst_id)
    except UnitInstalasi.DoesNotExist:
        return {
            'error': f'Instalasi dengan ID {inst_id} tidak ditemukan.'
        }

    # semua_pegawai = Users.objects.filter(instalasi=instalasi)

    # Ambil semua JenisSDMPerinstalasi bulan ini
    jenis_qs = JenisSDMPerinstalasi.objects.filter(
        bulan=bulan, tahun=tahun, instalasi=instalasi
    ).select_related('pegawai')

    jenis_map = {item.pegawai_id: item for item in jenis_qs}

    # Hitung jumlah jadwal per pegawai
    jadwal_count_qs = JadwalDinasSDM.objects.filter(
        tanggal__month=bulan,
        tanggal__year=tahun,
        pegawai__instalasi=instalasi
    ).values('pegawai__pegawai_id').annotate(jumlah=Count('id'))
    
    jadwal_map = {item['pegawai__pegawai_id']: item['jumlah'] for item in jadwal_count_qs}

    # Susun data per pegawai
    data_tabel = []
    for idx, peg in enumerate(users, start=1):
        terdaftar = peg.id in jenis_map
        jumlah_jadwal = jadwal_map.get(peg.id, 0)

        if not terdaftar:
            status = "❌ Belum terdaftar di JenisSDM"
        elif jumlah_jadwal == 0:
            status = "⚠️ Belum ada jadwal"
        elif jumlah_jadwal < jumlah_hari:
            status = "⚠️ Jadwal belum lengkap"
        else:
            status = "✅ Jadwal lengkap"

        data_tabel.append({
            'no': idx,
            'nama': peg.full_name,
            'terdaftar': "✅ Ya" if terdaftar else "❌ Tidak",
            'jumlah_jadwal': jumlah_jadwal,
            'status': status
        })

    return {
        'instalasi': instalasi.instalasi,
        'bulan': bulan,
        'tahun': tahun,
        'jumlah_hari': jumlah_hari,
        'data': data_tabel
    }


def get_pimpinan_id():
    pimpinan_ids = Users.objects.filter(
        Q(id__in=SatuanKerjaInduk.objects.values_list('nama_pimpinan_id', flat=True)) |
        Q(id__in=UnitOrganisasi.objects.values_list('nama_pimpinan_id', flat=True)) |
        Q(id__in=Bidang.objects.values_list('nama_pimpinan_id', flat=True)) |
        Q(id__in=SubBidang.objects.values_list('nama_pimpinan_id', flat=True))
    ).exclude(is_active=False).values_list('id', flat=True)
    
    return pimpinan_ids

class EvaluasiJadwal(LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView):
    template_name = 'jadwal_piket/evaluasijadwal_list.html'
    paginate_by = 20

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, 'Anda tidak memiliki izin untuk melihat menu ini.')
        return redirect(reverse('disiplinsdm_urls:jadwal_list'))

    def get_instalasi_queryset(self):
        user = self.request.user
        qs = UnitInstalasi.objects.all()
        if user.is_superuser:
            return qs
        profil = getattr(user, 'profil_admin', None)
        if profil:
            if profil.instalasi.exists():
                return qs.filter(pk__in=profil.instalasi.values_list('pk', flat=True))
            if profil.sub_bidang:
                return qs.filter(sub_bidang=profil.sub_bidang)
            if profil.bidang:
                return qs.filter(sub_bidang__bidang=profil.bidang)
        return qs.none()

    def get_inst_id(self, instalasi_qs):
        get = self.request.GET.get
        inst_id = get('inst')
        if not inst_id and instalasi_qs.exists():
            inst_id = str(instalasi_qs.first().pk)
        return inst_id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        get = self.request.GET.get
        tanggal = date.today()
        bulan = int(get('bulan') or tanggal.month)
        tahun = int(get('tahun') or tanggal.year)

        # Ambil daftar instalasi sesuai role
        instalasi_qs = self.get_instalasi_queryset()

        # Ambil inst_id dari GET atau fallback ke instalasi pertama
        inst_id = self.get_inst_id(instalasi_qs)

        # Saring user berdasarkan instalasi yang dipilih
        data_user = Users.objects.exclude(is_superuser=True, is_active=False).prefetch_related('riwayatpenempatan_set').order_by('-id')
        if inst_id:
            data_user = data_user.filter(
                riwayatpenempatan__penempatan_level4__id=inst_id,
                riwayatpenempatan__status=True
            )
        else:
            data_user = data_user.none()

        # Evaluasi berdasarkan user yang tersaring
        full_data_table = get_evaluasi_tabel(inst_id, data_user, bulan, tahun)
        data = full_data_table.get('data') if inst_id else []
        # Paginate hasil evaluasi
        paginator = Paginator(data, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context.update({
            'data': page_obj.object_list,
            'page_obj': page_obj,
            'paginator': paginator,
            'is_paginated': paginator.num_pages > 1,

            'instalasi_list': instalasi_qs,
            'bulan_list': [(i, month_name[i]) for i in range(1, 13)],
            'tahun_list': list(range(datetime.now().year - 5, datetime.now().year + 6)),

            'selected_inst': int(inst_id) if inst_id else None,
            'selected_bulan': bulan,
            'selected_tahun': tahun,
            'preserved_query': self._get_preserved_query(),

            'title': 'Evaluasi Pembuatan Jadwal',
            'url': reverse('disiplinsdm_urls:jadwal_list'),
            'riwayat': 'active',
            'selected': 'disiplin',
        })

        return context


    def _get_preserved_query(self):
        querydict = self.request.GET.copy()
        querydict.pop('page', None)
        return querydict.urlencode()


class HariLiburView(LoginRequiredMixin, generic.ListView):
    model = HariLibur
    template_name = 'jadwal_piket/harilibur_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        querydict = self.request.GET.copy()
        querydict.pop('page', None)
        context['preserved_query'] = querydict.urlencode()
        context['query'] = self.request.GET.get('q', '')
        context['bulan_list'] = [(i, month_name[i]) for i in range(1, 13)]
        current_year = datetime.now().year
        context['tahun_list'] = [year for year in range(current_year - 5, current_year + 6)]
        context['title'] = 'Daftar Hari Libur'
        context['url'] = reverse('disiplinsdm_urls:jadwal_list')
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        return context
    
    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get('per_page', 10)
        return per_page
    
    def get_queryset(self):
        tanggal = date.today()
        get = self.request.GET.get
        bulan = get('bulan')
        tahun = get('tahun')
        try:
            bulan = int(get('bulan')) if get('bulan') else tanggal.month
        except ValueError:
            bulan = tanggal.month

        try:
            tahun = int(get('tahun')) if get('tahun') else tanggal.year
        except ValueError:
            tahun = tanggal.year
        
        queryset = HariLibur.objects.filter(tanggal__month=bulan, tanggal__year=tahun).order_by('id')
        return queryset
    
    
class HariLiburCreateView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = HariLibur
    template_name='kehadirankegiatan/form.html'
    success_url=reverse_lazy('disiplinsdm_urls:harilibur_list')
    form_class=HariLiburForm
    
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        return False

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        messages.error(self.request, 'Anda tidak memiliki izin untuk menambah hari libur.')
        return redirect(reverse('disiplinsdm_urls:harilibur_list'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url'] = reverse('disiplinsdm_urls:harilibur_list')
        context['title'] = 'Tambah Hari Libur'
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        return context
    
    
class HariLiburUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = HariLibur
    template_name='kehadirankegiatan/form.html'
    success_url=reverse_lazy('disiplinsdm_urls:harilibur_list')
    form_class=HariLiburForm
    
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        return False

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        messages.error(self.request, 'Anda tidak memiliki izin untuk mengedit hari libur.')
        return redirect(reverse('disiplinsdm_urls:harilibur_list'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url'] = reverse('disiplinsdm_urls:harilibur_list')
        context['title'] = 'Edit Hari Libur'
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        return context
    

class HariLiburDeleteView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = HariLibur
    template_name='jadwal_piket/validasi_delete_jadwal.html'
    success_url=reverse_lazy('disiplinsdm_urls:harilibur_list')
    
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        return False

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        messages.error(self.request, 'Anda tidak memiliki izin untuk menghapus hari libur.')
        return redirect(reverse('disiplinsdm_urls:harilibur_list'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url'] = reverse('disiplinsdm_urls:harilibur_list')
        context['title'] = 'Hapus Hari Libur'
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        return context
    

def approve_instalasi_bulan(instalasi, bulan, tahun, user):
    with transaction.atomic():
        # Ambil ID pegawai yang statusnya 'diajukan'
        initial_jadwal_ids = list(JenisSDMPerinstalasi.objects.filter(
            instalasi=instalasi,
            bulan=bulan,
            tahun=tahun,
            status='diajukan'
        ).values_list('id', flat=True))
        
        # Ubah status jadi disetujui
        JenisSDMPerinstalasi.objects.filter(id__in=initial_jadwal_ids).update(status='disetujui')

        # Ambil jadwal yang akan di-approve
        draft_jadwal = JadwalDinasSDM.objects.filter(
            pegawai_id__in=initial_jadwal_ids,
            tanggal__year=tahun,
            tanggal__month=bulan
        )
        
        # Mapping baru: {(pegawai_id, tanggal): set(kategori_id)}
        new_shift_map = defaultdict(set)
        for jd in draft_jadwal:
            new_shift_map[(jd.pegawai_id, jd.tanggal)].add(jd.kategori_jadwal_id)
       
        # Ambil data ApprovedJadwalDinasSDM yang sudah ada
        old_approvals = ApprovedJadwalDinasSDM.objects.filter(
            pegawai_id__in=[j.pegawai_id for j in draft_jadwal],
            tanggal__year=tahun,
            tanggal__month=bulan
        ).select_related('kategori_jadwal', 'pegawai')

        # Mapping lama: {(pegawai_id, tanggal): set(kategori_id)}
        old_shift_map = defaultdict(set)
        for ap in old_approvals:
            old_shift_map[(ap.pegawai_id, ap.tanggal)].add(ap.kategori_jadwal_id)
        
        # Hapus shift yang tidak lagi dipakai (diganti)
        for (pegawai_id, tanggal), old_kategori_ids in old_shift_map.items():
            new_kategori_ids = new_shift_map.get((pegawai_id, tanggal), set())
            removed_shifts = old_kategori_ids - new_kategori_ids
            # added_ids = new_kategori_ids - old_kategori_ids
            # existing_ids = old_kategori_ids & new_kategori_ids
            # print(f"[{pegawai_id} - {tanggal}] Old: {old_kategori_ids} | New: {new_kategori_ids} | Removed: {removed_shifts} | Added: {added_ids}")
            
            if removed_shifts:
                ApprovedJadwalDinasSDM.objects.filter(
                    pegawai_id=pegawai_id,
                    tanggal=tanggal,
                    kategori_jadwal_id__in=removed_shifts
                ).delete()

        # Buat ulang existing_lookup setelah penghapusan
        existing_approvals = ApprovedJadwalDinasSDM.objects.filter(
            pegawai__in=[j.pegawai for j in draft_jadwal],
            tanggal__year=tahun,
            tanggal__month=bulan
        )
        existing_lookup = {
            (a.pegawai_id, a.tanggal, a.kategori_jadwal_id): a for a in existing_approvals
        }

        to_create = []
        to_update = []

        for jadwal in draft_jadwal:
            key = (jadwal.pegawai_id, jadwal.tanggal, jadwal.kategori_jadwal_id)

            if key in existing_lookup:
                obj = existing_lookup[key]
                obj.catatan = jadwal.catatan
                obj.is_approved = True
                obj.approved_by = user
                to_update.append(obj)
            else:
                to_create.append(ApprovedJadwalDinasSDM(
                    pegawai=jadwal.pegawai,
                    tanggal=jadwal.tanggal,
                    kategori_jadwal=jadwal.kategori_jadwal,
                    catatan=jadwal.catatan,
                    is_approved=True,
                    approved_by=user
                ))

        if to_create:
            ApprovedJadwalDinasSDM.objects.bulk_create(to_create)
        if to_update:
            ApprovedJadwalDinasSDM.objects.bulk_update(
                to_update,
                fields=['kategori_jadwal_id', 'catatan', 'is_approved', 'approved_by', 'updated_at']
            )
    

def generate_qr_with_logo(data: str, logo_path: str, size=300) -> BytesIO:
    # Buat QR Code
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H  # Tingkat koreksi tinggi agar QR masih bisa dibaca meski ditimpa logo
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # Resize QR
    qr_img = qr_img.resize((size, size), Image.LANCZOS)

    # Buka logo
    logo = Image.open(logo_path)
    logo_size = size // 4  # Logo 1/4 dari ukuran QR
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

    # Tempel logo ke tengah QR
    pos = ((qr_img.size[0] - logo.size[0]) // 2, (qr_img.size[1] - logo.size[1]) // 2)
    qr_img.paste(logo, pos, mask=logo if logo.mode == 'RGBA' else None)

    # Simpan ke BytesIO
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"


class JadwalBulananListView(LoginRequiredMixin, generic.ListView):
    model = JenisSDMPerinstalasi
    template_name = 'jadwal_piket/jadwal_pivot.html'
    context_object_name = 'metadata'

    def get_queryset(self):
        return JenisSDMPerinstalasi.objects.filter(
            bulan=self.bulan,
            tahun=self.tahun,
            instalasi=self.instalasi_id
        ).select_related('pegawai')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'bulan': self.bulan,
            'tahun': self.tahun,
            'tanggal_range': range(1, self.jumlah_hari + 1),
            'data': self.get_pivot_data().values(),
            'title': f'Jadwal instalasi {self.instalasi.instalasi}',
            'url': reverse('disiplinsdm_urls:jadwal_list'),
            'inst': self.instalasi_id,
            'tab': 'draft',
            'riwayat': 'active',
            'selected': 'disiplin',
        })

        # Tambahkan status dan QR
        context.update(self.get_status_and_qr())

        return context

    def get_pivot_data(self):
        pegawai_list = [md.pegawai for md in self.object_list]
        draft = JenisSDMPerinstalasi.objects.filter(bulan=self.bulan, tahun=self.tahun, status__in=['draft', 'ditolak', 'diajukan']).exists()
        
        jadwal_qs = ApprovedJadwalDinasSDM.objects.filter(
            tanggal__month=self.bulan,
            tanggal__year=self.tahun,
            pegawai__pegawai__in=pegawai_list
        ).select_related('kategori_jadwal', 'pegawai__pegawai')
        if draft:
            jadwal_qs = JadwalDinasSDM.objects.filter(
                tanggal__month=self.bulan,
                tanggal__year=self.tahun,
                pegawai__pegawai__in=pegawai_list
            ).select_related('kategori_jadwal', 'pegawai__pegawai')

        data = {
            md.pegawai.id: {
                'nama': md.pegawai.full_name,
                'jadwal': {}
            } for md in self.object_list
        }

        for j in jadwal_qs:
            pegawai_id = j.pegawai.pegawai.id
            hari = j.tanggal.day
            kategori = j.kategori_jadwal.akronim if j.kategori_jadwal else "-"

            # Pastikan key 'jadwal' sudah punya list untuk tanggal itu
            if hari not in data[pegawai_id]['jadwal']:
                data[pegawai_id]['jadwal'][hari] = []

            # Tambahkan kategori (hindari duplikat jika perlu)
            if kategori not in data[pegawai_id]['jadwal'][hari]:
                data[pegawai_id]['jadwal'][hari].append(kategori)

        return data

    def get_status_and_qr(self):
        data = {}
        object_data = self.object_list.first()
        objects_draft = self.object_list.filter(status__in=['draft', 'ditolak']).exists()
        objects_pengajuan = self.object_list.filter(status='diajukan').exists()

        status = 'Draft'
        tanggal_pengajuan = datetime.now()
        tanggal_persetujuan = datetime.now()
        qr_image_pengajuan = None
        qr_image_persetujuan = None
        approved_jadwal = None

        if object_data and not objects_draft:
            status = 'Diajukan'
            tanggal_pengajuan = object_data.updated_at
            qr_image_pengajuan = self.generate_qr(
                f'diajukan oleh: {self.pimpinan_instalasi}\n'
                f'tanggal: {tanggal_pengajuan}\n'
                f'url: {self.get_absolute_url()}'
            )

            approved_jadwal = object_data.approvedjadwaldinassdm_set.filter(
                pegawai__bulan=self.bulan,
                pegawai__tahun=self.tahun
            ).first()

            if approved_jadwal and not objects_pengajuan:
                status = 'Disetujui'
                tanggal_persetujuan = approved_jadwal.updated_at
                qr_image_persetujuan = self.generate_qr(
                    f'disetujui oleh: {self.pimpinan}\n'
                    f'tanggal: {tanggal_persetujuan}\n'
                    f'url: {self.get_absolute_url()}'
                )

        return {
            'tanggal_pengajuan': tanggal_pengajuan,
            'qr_image_pengajuan': qr_image_pengajuan,
            'tanggal': tanggal_persetujuan,
            'qr_image': qr_image_persetujuan,
            'status': status,
            'pimpinan_instalasi': self.pimpinan_instalasi,
            'pimpinan': self.pimpinan,
            'object_draft': objects_draft,
            'object_pengajuan': objects_pengajuan,
            'approved_jadwal': approved_jadwal
        }
        
    # def generate_qr(self, data_str):
    #     image_path = '/var/www/html/prod/static/dist/img/logo_rsmandalika.png'
    #     if not os.path.exists(image_path):
    #         raise FileNotFoundError("Logo tidak ditemukan.")
    #     return generate_qr_with_logo(data_str, image_path)

    def generate_qr(self, data_str):
        image_path = finders.find('dist/img/logo_rsmandalika.png')
        return generate_qr_with_logo(data_str, image_path)

    def get_absolute_url(self):
        return self.request.build_absolute_uri(
            reverse('disiplinsdm_urls:jadwal_pivot', kwargs={'inst': self.instalasi_id})
        )

    @cached_property
    def bulan(self):
        return int(self.request.GET.get('bulan', date.today().month))

    @cached_property
    def tahun(self):
        return int(self.request.GET.get('tahun', date.today().year))

    @cached_property
    def jumlah_hari(self):
        return monthrange(self.tahun, self.bulan)[1]

    @cached_property
    def instalasi_id(self):
        return self.kwargs.get('inst')

    @cached_property
    def instalasi(self):
        return UnitInstalasi.objects.filter(pk=self.instalasi_id).select_related('sub_bidang').first()

    @cached_property
    def pimpinan_instalasi(self):
        return self.instalasi.nama_pimpinan if self.instalasi else '-'

    @cached_property
    def pimpinan(self):
        return self.instalasi.sub_bidang.nama_pimpinan if self.instalasi and self.instalasi.sub_bidang else '-'


class ApprovedJadwalBulananListView(LoginRequiredMixin, generic.ListView):
    model = JenisSDMPerinstalasi
    template_name = 'jadwal_piket/jadwal_pivot_approved.html'
    context_object_name = 'metadata'

    def get_queryset(self):
        return JenisSDMPerinstalasi.objects.filter(
            bulan=self.bulan,
            tahun=self.tahun,
            instalasi=self.instalasi_id
        ).select_related('pegawai')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'bulan': self.bulan,
            'tahun': self.tahun,
            'tanggal_range': range(1, self.jumlah_hari + 1),
            'data': self.get_pivot_data().values(),
            'title': f'Jadwal instalasi {self.instalasi.instalasi}',
            'url': reverse('disiplinsdm_urls:jadwal_list'),
            'inst': self.instalasi_id,
            'tab': 'approved',
            'riwayat': 'active',
            'selected': 'disiplin',
        })

        # Tambahkan status dan QR
        context.update(self.get_status_and_qr())

        return context

    def get_pivot_data(self):
        pegawai_list = [md.pegawai for md in self.object_list]
        
        jadwal_qs = ApprovedJadwalDinasSDM.objects.filter(
            tanggal__month=self.bulan,
            tanggal__year=self.tahun,
            pegawai__pegawai__in=pegawai_list
        ).select_related('kategori_jadwal', 'pegawai__pegawai')

        data = {
            md.pegawai.id: {
                'nama': md.pegawai.full_name,
                'jadwal': {}
            } for md in self.object_list
        }

        for j in jadwal_qs:
            pegawai_id = j.pegawai.pegawai.id
            hari = j.tanggal.day
            kategori = j.kategori_jadwal.akronim if j.kategori_jadwal else "-"

            # Pastikan key 'jadwal' sudah punya list untuk tanggal itu
            if hari not in data[pegawai_id]['jadwal']:
                data[pegawai_id]['jadwal'][hari] = []

            # Tambahkan kategori (hindari duplikat jika perlu)
            if kategori not in data[pegawai_id]['jadwal'][hari]:
                data[pegawai_id]['jadwal'][hari].append(kategori)

        return data

    def get_status_and_qr(self):
        data = {}
        object_data = self.object_list.first()
        objects_draft = self.object_list.filter(status__in=['draft', 'ditolak', 'diajukan']).exists()

        status = 'Draft' if objects_draft else 'Disetujui'
        tanggal_pengajuan = datetime.now()
        tanggal_persetujuan = datetime.now()
        qr_image_pengajuan = None
        qr_image_persetujuan = None
        approved_jadwal = None

        if object_data:
            tanggal_pengajuan = object_data.updated_at
            qr_image_pengajuan = self.generate_qr(
                f'diajukan oleh: {self.pimpinan_instalasi}\n'
                f'tanggal: {tanggal_pengajuan}\n'
                f'url: {self.get_absolute_url()}'
            )

            approved_jadwal = object_data.approvedjadwaldinassdm_set.filter(
                pegawai__bulan=self.bulan,
                pegawai__tahun=self.tahun
            ).first()

            if approved_jadwal:
                tanggal_persetujuan = approved_jadwal.updated_at
                qr_image_persetujuan = self.generate_qr(
                    f'disetujui oleh: {self.pimpinan}\n'
                    f'tanggal: {tanggal_persetujuan}\n'
                    f'url: {self.get_absolute_url()}'
                )

        return {
            'tanggal_pengajuan': tanggal_pengajuan,
            'qr_image_pengajuan': qr_image_pengajuan,
            'tanggal': tanggal_persetujuan,
            'qr_image': qr_image_persetujuan,
            'status': status,
            'pimpinan_instalasi': self.pimpinan_instalasi,
            'pimpinan': self.pimpinan,
            'approved_jadwal': approved_jadwal
        }
        
    # def generate_qr(self, data_str):
    #     image_path = '/var/www/html/prod/static/dist/img/logo_rsmandalika.png'
    #     if not os.path.exists(image_path):
    #         raise FileNotFoundError("Logo tidak ditemukan.")
    #     return generate_qr_with_logo(data_str, image_path)

    def generate_qr(self, data_str):
        image_path = finders.find('dist/img/logo_rsmandalika.png')
        return generate_qr_with_logo(data_str, image_path)

    def get_absolute_url(self):
        return self.request.build_absolute_uri(
            reverse('disiplinsdm_urls:jadwal_pivot', kwargs={'inst': self.instalasi_id})
        )

    @cached_property
    def bulan(self):
        return int(self.request.GET.get('bulan', date.today().month))

    @cached_property
    def tahun(self):
        return int(self.request.GET.get('tahun', date.today().year))

    @cached_property
    def jumlah_hari(self):
        return monthrange(self.tahun, self.bulan)[1]

    @cached_property
    def instalasi_id(self):
        return self.kwargs.get('inst')

    @cached_property
    def instalasi(self):
        return UnitInstalasi.objects.filter(pk=self.instalasi_id).select_related('sub_bidang').first()

    @cached_property
    def pimpinan_instalasi(self):
        return self.instalasi.nama_pimpinan if self.instalasi else '-'

    @cached_property
    def pimpinan(self):
        return self.instalasi.sub_bidang.nama_pimpinan if self.instalasi and self.instalasi.sub_bidang else '-'


class PengajuanJadwalInstalasi(LoginRequiredMixin, UserPassesTestMixin, generic.View):
    def test_func(self):
        instalasi_id = self.kwargs['inst']
        user = self.request.user
        instalasi_pimpinan_list = UnitInstalasi.objects.filter(nama_pimpinan=user)
        if user.is_staff and instalasi_pimpinan_list.filter(pk=instalasi_id).exists():
            return True
        return False

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        inst = self.kwargs.get('inst')
        messages.error(self.request, 'Anda tidak memiliki izin untuk melakukan pengajuan jadwal.')
        return redirect(reverse('disiplinsdm_urls:jadwal_pivot', kwargs={'inst':inst}))
    
    def post(self, request, *args, **kwargs):
        instalasi_id = kwargs.get('inst')
        bulan = kwargs.get('bulan')
        tahun = kwargs.get('tahun')
        instalasi = None
        try:
            instalasi=UnitInstalasi.objects.get(pk=instalasi_id)
        except UnitInstalasi.DoesNotExist:
            instalasi = None
        initial_jadwal = JenisSDMPerinstalasi.objects.filter(
            instalasi=instalasi, 
            bulan=bulan,
            tahun=tahun,
            status='draft'
        ).update(status='diajukan')
        messages.success(request, f'Jadwal instalasi {instalasi.instalasi} diajukan!')
        return redirect(reverse('disiplinsdm_urls:jadwal_pivot', kwargs={'inst':instalasi_id}))
    
        
class ApprovalJadwalInstalasi(LoginRequiredMixin, UserPassesTestMixin, generic.View):
    def test_func(self):
        instalasi_id = self.kwargs['inst']
        user = self.request.user
        sub_bidang = user.profil_admin.sub_bidang if hasattr(user, 'profil_admin') and hasattr(user.profil_admin, 'sub_bidang') else None
        instalasi_pimpinan_list = UnitInstalasi.objects.filter(sub_bidang=sub_bidang)
        if user.is_staff and instalasi_pimpinan_list.filter(pk=instalasi_id).exists():
            return True
        return False

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        inst = self.kwargs.get('inst')
        messages.error(self.request, 'Anda tidak memiliki izin untuk melakukan approval jadwal ini.')
        return redirect(reverse('disiplinsdm_urls:jadwal_pivot', kwargs={'inst':inst}))
    
    def post(self, *args, **kwargs):
        instalasi_id = kwargs.get('inst')
        bulan = kwargs.get('bulan')
        tahun = kwargs.get('tahun')
        instalasi = None
        try:
            instalasi=UnitInstalasi.objects.get(pk=instalasi_id)
        except UnitInstalasi.DoesNotExist:
            instalasi = None
        with transaction.atomic():
            approve_instalasi_bulan(instalasi, bulan, tahun, self.request.user)
        return redirect(reverse('disiplinsdm_urls:jadwal_pivot', kwargs={'inst':instalasi_id}))


def generate_qr_with_logo_for_excel(data: str, logo_path: str, size=300) -> BytesIO:
    # Buat QR Code
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H  # Tingkat koreksi tinggi agar QR masih bisa dibaca meski ditimpa logo
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # Resize QR
    qr_img = qr_img.resize((size, size), Image.LANCZOS)

    # Buka logo
    logo = Image.open(logo_path)
    logo_size = size // 4  # Logo 1/4 dari ukuran QR
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

    # Tempel logo ke tengah QR
    pos = ((qr_img.size[0] - logo.size[0]) // 2, (qr_img.size[1] - logo.size[1]) // 2)
    qr_img.paste(logo, pos, mask=logo if logo.mode == 'RGBA' else None)

    # Simpan ke BytesIO
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def hitung_standar_jam_kerja(model, bulan, tahun):
    _, total_hari = calendar.monthrange(tahun, bulan)
    jam_kerja = Decimal("0")
    for hari in range(1, total_hari + 1):
        tanggal = date(tahun, bulan, hari)
        if model.objects.filter(tanggal=tanggal).exists():
            continue
        weekday = tanggal.weekday()
        if weekday in [0, 1, 2, 3]:  # Senin–Kamis
            jam_kerja += Decimal("7")
        elif weekday == 4:  # Jumat
            jam_kerja += Decimal("6.5")
        elif weekday == 5:  # Sabtu
            jam_kerja += Decimal("4.5")
    return jam_kerja


def hitung_standar_jam_kerja_maks(model, bulan, tahun):
    _, total_hari = calendar.monthrange(tahun, bulan)
    jam_kerja = Decimal("0")
    for hari in range(1, total_hari + 1):
        tanggal = date(tahun, bulan, hari)
        if model.objects.filter(tanggal=tanggal).exists():
            continue
        weekday = tanggal.weekday()
        if weekday in [0, 1, 2, 3]:  # Senin–Kamis
            jam_kerja += Decimal("7")
        elif weekday == 4:  # Jumat
            jam_kerja += Decimal("6.5")
        elif weekday == 5:  # Sabtu
            jam_kerja += Decimal("5.5")
    return jam_kerja


def evaluasi_beban(jumlah_jam, standar_min, standar_max):
    if jumlah_jam < standar_min:
        return "Ringan 🔵"
    elif jumlah_jam <= standar_max:
        return "Ideal 🟢"
    else:
        return "Overload 🔴"


def draft_export_jadwal_excel(request, inst, bulan, tahun):
    jumlah_hari = monthrange(tahun, bulan)[1]
    nama_bulan = date(tahun, bulan, 1).strftime('%B')

    try:
        instalasi = UnitInstalasi.objects.get(pk=inst)
    except UnitInstalasi.DoesNotExist:
        instalasi = None

    metadata = JenisSDMPerinstalasi.objects.filter(
        bulan=bulan, tahun=tahun, instalasi=instalasi
    ).select_related('pegawai').prefetch_related('jadwaldinassdm_set__kategori_jadwal')

    # Siapkan workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Jadwal {bulan}-{tahun}"

    judul = f"Jadwal Instalasi {instalasi.instalasi} Bulan {nama_bulan} {tahun}"
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=jumlah_hari + 4)
    judul_cell = ws.cell(row=1, column=1, value=judul)
    judul_cell.font = Font(size=14, bold=True)
    judul_cell.alignment = Alignment(horizontal='center')

    header = ["No", "Nama Pegawai"] + list(range(1, jumlah_hari + 1)) + ["Total Jam", "Evaluasi"]
    ws.append(header)
    for cell in ws[2]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="DDDDDD", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')

    # Loop data pegawai
    for idx, md in enumerate(metadata, start=1):
        baris = [idx, md.pegawai.full_name]
        jadwal_per_hari = {jadwal.tanggal.day: jadwal.kategori_jadwal.akronim if jadwal.kategori_jadwal else "-" for jadwal in md.jadwaldinassdm_set.all()}
        
        for tgl in range(1, jumlah_hari + 1):
            baris.append(jadwal_per_hari.get(tgl, "-"))

        total_jam = md.kurang_lebih_jam_kerja
        baris.append(total_jam)

        evaluasi = evaluasi_beban(
            Decimal(total_jam),
            Decimal(md.standar_min_efektif),
            Decimal(md.standar_max_efektif)
        )
        baris.append(evaluasi)

        ws.append(baris)

    # Styling border
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=jumlah_hari + 4):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')

    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 25

    # Tambahan info dan legend
    ws.append([])
    ws.append(["Keterangan Akronim:"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
    keterangan_akronim = {
        "P": "Pagi", "S": "Siang", "M": "Malam", "Md": "Middle",
        "LP": "Lepas Piket", "L": "Libur", "LX": "Libur Extra", "C": "Cuti"
    }
    for kode, ket in keterangan_akronim.items():
        ws.append([kode, ket])
        ws.cell(row=ws.max_row, column=1).alignment = Alignment(horizontal='center')

    # Response
    filename = f"jadwal_{bulan}_{tahun}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


# def draft_export_jadwal_excel(request, inst, bulan, tahun):
#     jumlah_hari = monthrange(tahun, bulan)[1]
#     nama_bulan = date(tahun, bulan, 1).strftime('%B')

#     try:
#         instalasi = UnitInstalasi.objects.get(pk=inst)
#     except UnitInstalasi.DoesNotExist:
#         instalasi = None

#     metadata = JenisSDMPerinstalasi.objects.filter(
#         bulan=bulan, tahun=tahun, instalasi=instalasi
#     ).select_related('pegawai')

#     pegawai_list = [md.pegawai for md in metadata]

#     jadwal_qs = JadwalDinasSDM.objects.filter(
#         tanggal__month=bulan,
#         tanggal__year=tahun,
#         pegawai__pegawai__in=pegawai_list
#     ).select_related('kategori_jadwal', 'pegawai__pegawai')

#     data = {}
#     for md in metadata:
#         data[md.pegawai.id] = {
#             'nama': md.pegawai.full_name,
#             'jadwal': defaultdict(str)
#         }

#     for j in jadwal_qs:
#         hari = j.tanggal.day
#         kategori = j.kategori_jadwal.akronim if j.kategori_jadwal else "-"
#         slot = data[j.pegawai.pegawai.id]['jadwal']
#         slot[hari] = f"{slot[hari]},{kategori}" if slot[hari] else kategori

#     jam_pegawai = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
#     for j in jadwal_qs:
#         if not j.kategori_jadwal or not j.kategori_jadwal.waktu_datang or not j.kategori_jadwal.waktu_pulang:
#             continue

#         dt = datetime.combine(date.min, j.kategori_jadwal.waktu_datang)
#         pt = datetime.combine(date.min, j.kategori_jadwal.waktu_pulang)
#         if pt <= dt:
#             pt += timedelta(days=1)
#         durasi = Decimal(str((pt - dt).total_seconds() / 3600))
#         jam_pegawai[j.pegawai.pegawai.id][j.tanggal.day] += durasi

#     standar_min = hitung_standar_jam_kerja(HariLibur, bulan, tahun)
#     standar_max = hitung_standar_jam_kerja_maks(HariLibur, bulan, tahun)

#     wb = openpyxl.Workbook()
#     ws = wb.active
#     ws.title = f"Jadwal {bulan}-{tahun}"

#     judul = f"Jadwal Instalasi {instalasi.instalasi} Bulan {nama_bulan} {tahun}"
#     ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=jumlah_hari + 4)
#     judul_cell = ws.cell(row=1, column=1, value=judul)
#     judul_cell.font = Font(size=14, bold=True)
#     judul_cell.alignment = Alignment(horizontal='center')

#     header = ["No", "Nama Pegawai"] + list(range(1, jumlah_hari + 1)) + ["Total Jam", "Evaluasi"]
#     ws.append(header)

#     for cell in ws[2]:
#         cell.font = Font(bold=True)
#         cell.fill = PatternFill(start_color="DDDDDD", fill_type="solid")
#         cell.alignment = Alignment(horizontal='center')

#     for idx, (pid, row) in enumerate(data.items(), start=1):
#         baris = [idx, row['nama']]
#         total_jam = Decimal("0")
#         for tgl in range(1, jumlah_hari + 1):
#             isi = row['jadwal'].get(tgl, "-")
#             jam = jam_pegawai[pid].get(tgl, Decimal("0"))
#             total_jam += jam
#             baris.append(isi)
#         baris.append(float(total_jam))
#         baris.append(evaluasi_beban(total_jam, standar_min, standar_max))
#         ws.append(baris)

#     border = Border(
#         left=Side(style='thin'), right=Side(style='thin'),
#         top=Side(style='thin'), bottom=Side(style='thin')
#     )

#     for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=jumlah_hari + 4):
#         for cell in row:
#             cell.border = border
#             cell.alignment = Alignment(horizontal='center', vertical='center')

#     ws.column_dimensions["A"].width = 5
#     ws.column_dimensions["B"].width = 25

#     ws.append([])
#     ws.append([f"Standar jam kerja bulan ini:", f"{float(standar_min)} – {float(standar_max)} jam"])
#     ws.cell(row=ws.max_row, column=1).font = Font(bold=True)

#     ws.append([])
#     ws.append(["Keterangan Akronim:"])
#     ws.cell(row=ws.max_row, column=1).font = Font(bold=True)

#     keterangan_akronim = {
#         "P": "Pagi", "S": "Siang", "M": "Malam", "Md": "Middle",
#         "LP": "Lepas Piket", "L": "Libur", "LX": "Libur Extra", "C": "Cuti"
#     }

#     for kode, ket in keterangan_akronim.items():
#         ws.append([kode, ket])
#         ws.cell(row=ws.max_row, column=1).alignment = Alignment(horizontal='center')
        
#     filename = f"jadwal_{bulan}_{tahun}.xlsx"
#     response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#     response['Content-Disposition'] = f'attachment; filename="{filename}"'
#     wb.save(response)
#     return response


def export_jadwal_excel(request, inst, bulan, tahun):
    jumlah_hari = monthrange(tahun, bulan)[1]
    nama_bulan = date(tahun, bulan, 1).strftime('%B')

    try:
        instalasi = UnitInstalasi.objects.get(pk=inst)
    except UnitInstalasi.DoesNotExist:
        instalasi = None

    metadata = JenisSDMPerinstalasi.objects.filter(
        bulan=bulan, tahun=tahun, instalasi=instalasi
    ).select_related('pegawai')

    pegawai_list = [md.pegawai for md in metadata]

    jadwal_qs = ApprovedJadwalDinasSDM.objects.filter(
        tanggal__month=bulan,
        tanggal__year=tahun,
        pegawai__pegawai__in=pegawai_list
    ).select_related('kategori_jadwal', 'pegawai__pegawai')

    data = {}
    for md in metadata:
        data[md.pegawai.id] = {
            'nama': md.pegawai.full_name,
            'jadwal': defaultdict(str)
        }

    for j in jadwal_qs:
        hari = j.tanggal.day
        kategori = j.kategori_jadwal.akronim if j.kategori_jadwal else "-"
        slot = data[j.pegawai.pegawai.id]['jadwal']
        slot[hari] = f"{slot[hari]},{kategori}" if slot[hari] else kategori

    jam_pegawai = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for j in jadwal_qs:
        if not j.kategori_jadwal or not j.kategori_jadwal.waktu_datang or not j.kategori_jadwal.waktu_pulang:
            continue

        dt = datetime.combine(date.min, j.kategori_jadwal.waktu_datang)
        pt = datetime.combine(date.min, j.kategori_jadwal.waktu_pulang)
        if pt <= dt:
            pt += timedelta(days=1)
        durasi = Decimal(str((pt - dt).total_seconds() / 3600))
        jam_pegawai[j.pegawai.pegawai.id][j.tanggal.day] += durasi

    standar_min = hitung_standar_jam_kerja(HariLibur, bulan, tahun)
    standar_max = hitung_standar_jam_kerja_maks(HariLibur, bulan, tahun)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Jadwal {bulan}-{tahun}"

    judul = f"Jadwal Instalasi {instalasi.instalasi} Bulan {nama_bulan} {tahun}"
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=jumlah_hari + 4)
    judul_cell = ws.cell(row=1, column=1, value=judul)
    judul_cell.font = Font(size=14, bold=True)
    judul_cell.alignment = Alignment(horizontal='center')

    header = ["No", "Nama Pegawai"] + list(range(1, jumlah_hari + 1)) + ["Total Jam", "Evaluasi"]
    ws.append(header)

    for cell in ws[2]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="DDDDDD", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')

    for idx, (pid, row) in enumerate(data.items(), start=1):
        baris = [idx, row['nama']]
        total_jam = Decimal("0")
        for tgl in range(1, jumlah_hari + 1):
            isi = row['jadwal'].get(tgl, "-")
            jam = jam_pegawai[pid].get(tgl, Decimal("0"))
            total_jam += jam
            baris.append(isi)
        baris.append(float(total_jam))
        baris.append(evaluasi_beban(total_jam, standar_min, standar_max))
        ws.append(baris)

    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=jumlah_hari + 4):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')

    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 25

    ws.append([])
    ws.append([f"Standar jam kerja bulan ini:", f"{float(standar_min)} – {float(standar_max)} jam"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True)

    ws.append([])
    ws.append(["Keterangan Akronim:"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True)

    keterangan_akronim = {
        "P": "Pagi", "S": "Siang", "M": "Malam", "Md": "Middle",
        "LP": "Lepas Piket", "L": "Libur", "LX": "Libur Extra", "C": "Cuti"
    }

    for kode, ket in keterangan_akronim.items():
        ws.append([kode, ket])
        ws.cell(row=ws.max_row, column=1).alignment = Alignment(horizontal='center')
        
    # === Pengesahan Digital di Pojok Kanan Bawah ===
    tanggal = jadwal_qs.first()
    pimpinan = None
    try:
        unit = UnitInstalasi.objects.get(pk=inst)
        pimpinan = unit.sub_bidang.nama_pimpinan
    except UnitInstalasi.DoesNotExist:
        unit = None
    # Lokasi pengesahan (custom jika perlu)
    lokasi_pengesahan = "Pujut"
    tanggal_pengesahan = tanggal.updated_at.strftime("%d %B %Y")
    nama_pimpinan = pimpinan.full_name_2 if hasattr(pimpinan, 'full_name_2') else None

    # QR Code data
    qr_data = f"Jadwal Bulan {nama_bulan} {tahun} - Disahkan oleh {nama_pimpinan} ({lokasi_pengesahan}, {tanggal_pengesahan})"
    logo_path = finders.find('dist/img/logo_rsmandalika.png')  # Ganti sesuai path logo kamu
    # logo_path = '/var/www/html/prod/static/dist/img/logo_rsmandalika.png'

    qr_buffer = generate_qr_with_logo_for_excel(qr_data, logo_path)
    qr_image = XLImage(qr_buffer)
    qr_image.width = 150
    qr_image.height = 150

    # Posisi baris & kolom
    baris_awal = ws.max_row + 3
    kolom_qr = jumlah_hari
    
    col_letter = get_column_letter(kolom_qr)
    start_row = ws.max_row + 4

    # Isi teks pengesahan
    ws.cell(row=baris_awal, column=kolom_qr, value="Mengetahui,")
    ws.cell(row=baris_awal + 1, column=kolom_qr, value=f"{lokasi_pengesahan}, {tanggal_pengesahan}")
    ws.cell(row=baris_awal + 12, column=kolom_qr, value=nama_pimpinan)
    ws.cell(row=baris_awal + 12, column=kolom_qr).font = Font(bold=True)
    ws.cell(row=baris_awal + 12, column=kolom_qr).alignment = Alignment(horizontal='center')

    # Sisipkan QR Code
    qr_position = f"{col_letter}{start_row + 2}"
    ws.add_image(qr_image, qr_position)


    filename = f"jadwal_{bulan}_{tahun}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response
    

class AjukanJadwalView(generic.UpdateView):
    model = JenisSDMPerinstalasi
    form_class = PengajuanJadwalForm
    template_name = 'jadwal_piket/jadwal_pengajuan_persetujuan.html'
    
    def get_success_url(self):
        query_params = self.request.GET.copy()
        if query_params:  # hanya jika ada query string
            return f'{reverse("disiplinsdm_urls:jadwal_list")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_list')

    def get_failure_url(self):
        pk = self.kwargs.get('pk')
        query_params = self.request.GET.copy()
        if query_params:
            return f'{reverse("disiplinsdm_urls:jadwal_auto_create", kwargs={"pk":pk})}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_auto_create', kwargs={'pk':pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        context['status'] = obj.status
        context['title'] = f'Detail Jadwal: { self.object.pegawai.full_name } ({ self.object.bulan }/{ self.object.tahun })'
        context['url'] = self.get_failure_url()

        queryset = obj.jadwaldinassdm_set.select_related('kategori_jadwal').order_by('tanggal')

        minggu_list = get_mingguan_lengkap(obj.bulan, obj.tahun)
        libur_set = set(HariLibur.objects.filter(
            tanggal__year=obj.tahun, tanggal__month=obj.bulan
        ).values_list('tanggal', flat=True))

        minggu_data = []
        total_bulanan = 0
        for minggu in minggu_list:
            hari_data = []
            total_mingguan = 0
            for jadwal in queryset:
                tgl = jadwal.tanggal
                if minggu[0] <= tgl <= minggu[-1]:
                    datang = jadwal.kategori_jadwal.waktu_datang if jadwal.kategori_jadwal else None
                    pulang = jadwal.kategori_jadwal.waktu_pulang if jadwal.kategori_jadwal else None
                    jam = 0
                    if datang and pulang:
                        mulai = datetime.combine(tgl, datang)
                        selesai = datetime.combine(tgl, pulang)
                        if selesai < mulai:
                            selesai += timedelta(days=1)
                        jam = round((selesai - mulai).total_seconds() / 3600, 1)
                    total_mingguan += jam
                    total_bulanan += jam

                    hari_data.append({
                        'tanggal': tgl,
                        'kategori': jadwal.kategori_jadwal,
                        'jam': jam,
                        'catatan': jadwal.catatan,
                        'libur': tgl.weekday() == 6 or tgl in libur_set
                    })
            minggu_data.append({
                'range': minggu,
                'data': hari_data,
                'total_jam': total_mingguan,
            })

        context.update({
            'minggu_data': minggu_data,
            'total_bulanan': total_bulanan,
            'standar_min': obj.standar_min_efektif,
            'standar_max': obj.standar_max_efektif,
            'selisih': obj.selisih_jam_kerja,
        })
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.status not in ['draft', 'ditolak']:
            messages.warning(request, "Jadwal ini tidak dalam status draft atau ditolak.")
            return redirect(self.get_failure_url())

        jadwal_sdm = self.object

        with transaction.atomic():
            # Update status
            jadwal_sdm.status = 'diajukan'
            jadwal_sdm.save()
            messages.success(request, 'Pengajuan behasil dilakukan, informasikan ke atasan anda agar segera disetujui!')
        return redirect(self.get_success_url())


class SetujuiJadwalView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = JenisSDMPerinstalasi
    template_name = 'jadwal_piket/jadwal_pengajuan_persetujuan.html'
    fields = []
    
    def get_success_url(self):
        query_params = self.request.GET.copy()
        if query_params:  # hanya jika ada query string
            return f'{reverse("disiplinsdm_urls:jadwal_list")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_list')
    
    def get_failure_url(self):
        pk = self.kwargs.get('pk')
        query_params = self.request.GET.copy()
        if query_params:  # hanya jika ada query string
            return f'{reverse("disiplinsdm_urls:jadwal_auto_create", kwargs={"pk":pk})}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_auto_create', kwargs={'pk':pk})

    def test_func(self):
        sub_bidang = SubBidang.objects.filter(nama_pimpinan=self.request.user).exists()
        if self.request.user.is_superuser:
            return True
        elif sub_bidang and self.request.user.is_staff:
            return True
        return False

    def handle_no_permission(self):
        messages.error(self.request, "Anda tidak memiliki izin untuk menyetujui jadwal.")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        context['status'] = obj.status if hasattr(obj, 'status') else 'draft'
        context['title'] = f'Detail Jadwal: { self.object.pegawai.full_name } ({ self.object.bulan }/{ self.object.tahun })'
        context['url'] = reverse_lazy('disiplinsdm_urls:jadwal_list')
        jadwal_list = obj.jadwaldinassdm_set.select_related('kategori_jadwal').order_by('tanggal')

        minggu_data = []
        minggu_list = get_mingguan_lengkap(obj.bulan, obj.tahun)
        libur_set = set(HariLibur.objects.filter(
            tanggal__year=obj.tahun,
            tanggal__month=obj.bulan
        ).values_list('tanggal', flat=True))

        total_bulanan = 0
        for minggu in minggu_list:
            hari_data = []
            total_mingguan = 0
            for jadwal in jadwal_list:
                if minggu[0] <= jadwal.tanggal <= minggu[-1]:
                    datang = jadwal.kategori_jadwal.waktu_datang if jadwal.kategori_jadwal else None
                    pulang = jadwal.kategori_jadwal.waktu_pulang if jadwal.kategori_jadwal else None
                    jam = 0
                    if datang and pulang:
                        mulai = datetime.combine(jadwal.tanggal, datang)
                        selesai = datetime.combine(jadwal.tanggal, pulang)
                        if selesai < mulai:
                            selesai += timedelta(days=1)
                        jam = round((selesai - mulai).total_seconds() / 3600, 1)
                    total_mingguan += jam
                    total_bulanan += jam
                    hari_data.append({
                        'tanggal': jadwal.tanggal,
                        'kategori': jadwal.kategori_jadwal,
                        'jam': jam,
                        'catatan': jadwal.catatan,
                        'libur': jadwal.tanggal.weekday() == 6 or jadwal.tanggal in libur_set
                    })
            minggu_data.append({
                'range': minggu,
                'data': hari_data,
                'total_jam': total_mingguan,
            })

        context.update({
            'minggu_data': minggu_data,
            'total_bulanan': total_bulanan,
            'standar_min': obj.standar_min_efektif,
            'standar_max': obj.standar_max_efektif,
            'selisih': obj.selisih_jam_kerja,
            'can_approve': self.request.user.is_staff,
        })
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.status != 'diajukan':
            messages.warning(request, "Jadwal ini tidak dalam status 'diajukan'.")
            return redirect(self.get_failure_url())

        aksi = request.POST.get("aksi")
        alasan = request.POST.get("alasan_penolakan", "").strip()

        if aksi == 'tolak':
            if not alasan:
                messages.error(request, "Mohon isi alasan penolakan jika ingin menolak jadwal.")
                return redirect(self.get_failure_url())

            self.object.status = 'ditolak'
            self.object.alasan_penolakan = alasan
            self.object.save()

            messages.success(request, f"Jadwal {self.object.pegawai.full_name} berhasil ditolak.")
            return redirect(self.get_success_url())

        elif aksi == 'setujui':
            jadwal_list = self.object.jadwaldinassdm_set.filter(
                tanggal__month=self.object.bulan,
                tanggal__year=self.object.tahun
            )

            with transaction.atomic():
                self.object.status = 'disetujui'
                self.object.save()

                # Ambil semua jadwal approved yang sudah ada
                approved_existing = ApprovedJadwalDinasSDM.objects.filter(
                    pegawai=self.object,
                    tanggal__month=self.object.bulan,
                    tanggal__year=self.object.tahun
                )

                # Buat mapping: {(tanggal, kategori_id): Approved}
                approved_map = {
                    (a.tanggal, a.kategori_jadwal_id): a for a in approved_existing
                }

                # Buat mapping baru dari draft jadwal
                draft_map = {
                    (j.tanggal, j.kategori_jadwal_id): j for j in jadwal_list
                }

                to_create = []
                to_update = []

                # Update jika ada perubahan
                for key, jadwal in draft_map.items():
                    if key in approved_map:
                        approved = approved_map[key]
                        if (
                            approved.catatan != jadwal.catatan or
                            not approved.is_approved or
                            approved.approved_by != request.user
                        ):
                            approved.catatan = jadwal.catatan
                            approved.is_approved = True
                            approved.approved_by = request.user
                            to_update.append(approved)
                    else:
                        to_create.append(ApprovedJadwalDinasSDM(
                            pegawai=self.object,
                            tanggal=jadwal.tanggal,
                            kategori_jadwal=jadwal.kategori_jadwal,
                            catatan=jadwal.catatan,
                            is_approved=True,
                            approved_by=request.user
                        ))

                # Hapus approved yang sudah tidak ada di draft
                existing_keys = set(approved_map.keys())
                current_keys = set(draft_map.keys())
                removed_keys = existing_keys - current_keys
                if removed_keys:
                    ApprovedJadwalDinasSDM.objects.filter(
                        pegawai=self.object,
                        tanggal__in=[k[0] for k in removed_keys],
                        kategori_jadwal_id__in=[k[1] for k in removed_keys]
                    ).delete()

                if to_create:
                    ApprovedJadwalDinasSDM.objects.bulk_create(to_create)

                if to_update:
                    ApprovedJadwalDinasSDM.objects.bulk_update(
                        to_update,
                        fields=['catatan', 'is_approved', 'approved_by', 'updated_at']
                    )

            messages.success(request, f"Jadwal {self.object.pegawai.full_name} berhasil disetujui.")
            return redirect(self.get_success_url())


def get_jenis_hari(tanggal):
    weekday = tanggal.weekday()
    if weekday in [0, 1, 2, 3]:
        return "Senin s/d kamis"
    elif weekday == 4:
        return "Jumat"
    elif weekday == 5:
        return "Sabtu"
    elif weekday == 6:
        return "Ahad"
    
def generate_bulk_jadwal(pegawai_obj, bulan, tahun):
    minggu_list = get_mingguan_lengkap(bulan, tahun)
    libur_qs = set(HariLibur.objects.filter(tanggal__month=bulan, tanggal__year=tahun).values_list('tanggal', flat=True))
    detail_map = {
        "Senin s/d kamis": DetailKategoriJadwalDinas.objects.filter(hari="Senin s/d kamis").first(),
        "Jumat": DetailKategoriJadwalDinas.objects.filter(hari="Jumat").first(),
        "Sabtu": DetailKategoriJadwalDinas.objects.filter(hari="Sabtu").first(),
        "Ahad": DetailKategoriJadwalDinas.objects.filter(hari="Ahad").first()  # libur
    }

    jadwal_list = []
    for minggu in minggu_list:
        for tanggal in minggu:
            is_libur = tanggal in libur_qs or tanggal.weekday() == 6
            kategori = detail_map.get("Ahad")
            if not is_libur:
                jenis_hari = get_jenis_hari(tanggal)
                kategori = detail_map.get(jenis_hari)

            jadwal = JadwalDinasSDM(
                pegawai=pegawai_obj,
                tanggal=tanggal,
                kategori_jadwal=kategori
            )
            jadwal_list.append(jadwal)
    
    # Simpan semua jadwal sekaligus
    JadwalDinasSDM.objects.bulk_create(jadwal_list)
    return jadwal_list


def safe_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
    
class JadwalListView(LoginRequiredMixin, generic.ListView):
    model = JenisSDMPerinstalasi
    template_name = 'jadwal_piket/jadwal_list.html'
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    paginate_by = 10

    # ====================
    # Helper Methods
    # ====================
    def get_penempatan_object(self, nip):
        if not nip:
            return None
        return RiwayatPenempatan.objects.filter(pegawai__profil_user__nip=nip, status=True).last()

    def get_jenis_sdm(self, nip):
        if not nip:
            return None
        return RiwayatJabatan.objects.filter(pegawai__profil_user__nip=nip).last()

    def get_user(self, nip):
        if not nip:
            return None
        return Users.objects.filter(profil_user__nip=nip, is_active=True).first()

    def get_filter_params(self):
        get = self.request.GET.get
        today = date.today()

        try:
            bulan = int(get('bulan')) if get('bulan') else today.month
            if not (1 <= bulan <= 12):
                bulan = today.month
        except ValueError:
            bulan = today.month

        try:
            tahun = int(get('tahun')) if get('tahun') else today.year
        except ValueError:
            tahun = today.year

        return {
            'query': get('q'),
            'bulan': bulan,
            'tahun': tahun,
            'nip': get('nip'),
            'tanggal': get_date_from_string(get('tanggal') or today.isoformat()),
        }


    def get_active_instalasi(self):
        inst_param = self.request.GET.get('inst')
        if inst_param:
            return UnitInstalasi.objects.filter(pk=inst_param).first()

        user = self.request.user
        profil = getattr(user, 'profil_admin', None)

        if user.is_superuser:
            return UnitInstalasi.objects.first()
        elif profil:
            if profil.instalasi.exists():
                return profil.instalasi.first()
            if profil.sub_bidang:
                return UnitInstalasi.objects.filter(sub_bidang=profil.sub_bidang).first()
            if profil.bidang:
                return UnitInstalasi.objects.filter(sub_bidang__bidang=profil.bidang).first()
            if profil.unor:
                return UnitInstalasi.objects.filter(sub_bidang__bidang__unor=profil.unor).first()
        else:
            instalasi = user.riwayatpenempatan_set.filter(status=True).first()
            if instalasi is not None:
                instalasi = instalasi.penempatan_level4
            else:
                instalasi = None
            return instalasi
        

    def get_user_queryset(self):
        user = self.request.user
        users = Users.objects.exclude(is_superuser=True, is_active=False).prefetch_related('riwayatpenempatan_set')
        profil = getattr(user, 'profil_admin', None)

        if user.is_superuser:
            return users
        if not profil:
            return users.none()

        if profil.instalasi.exists():
            return users.filter(riwayatpenempatan__penempatan_level4__in=profil.instalasi.values_list('pk', flat=True), riwayatpenempatan__status=True)
        if profil.sub_bidang:
            return users.filter(riwayatpenempatan__penempatan_level3=profil.sub_bidang, riwayatpenempatan__status=True)
        if profil.bidang:
            return users.filter(riwayatpenempatan__penempatan_level2=profil.bidang, riwayatpenempatan__status=True)
        if profil.unor:
            return users.filter(riwayatpenempatan__penempatan_level1=profil.unor, riwayatpenempatan__status=True)
        return users.none()
    
    def get_instalasi_queryset(self):
        user = self.request.user
        instalasi_list = UnitInstalasi.objects.all().prefetch_related('sub_bidang', 'sub_bidang__bidang', 'sub_bidang__bidang__unor')
        profil = getattr(user, 'profil_admin', None)

        if user.is_superuser:
            return instalasi_list
        if not profil:
            return instalasi_list.none()

        if profil.instalasi.exists():
            return instalasi_list.filter(pk__in=profil.instalasi.values_list('pk', flat=True))
        if profil.sub_bidang:
            return instalasi_list.filter(sub_bidang=profil.sub_bidang)
        if profil.bidang:
            return instalasi_list.filter(sub_bidang__bidang=profil.bidang, riwayatpenempatan__status=True)
        if profil.unor:
            return instalasi_list.filter(sub_bidang__bidang__unor=profil.unor, riwayatpenempatan__status=True)
        return instalasi_list.none()

    def get_queryset(self):
        params = self.get_filter_params()
        instalasi = self.get_active_instalasi()
        queryset = JenisSDMPerinstalasi.objects.all().order_by('-id').exclude(
                Q(pegawai__is_active=False) |
                Q(pegawai__is_superuser=True)
            )
        
        if self.request.user.is_superuser:
            queryset = queryset
        if instalasi:
            queryset = queryset.filter(instalasi=instalasi)
        else:
            queryset = queryset.none()
        
        queryset = queryset.filter(bulan=params['bulan'], tahun=params['tahun'])
        if params['query']:
            q = params['query']
            queryset = queryset.filter(
                Q(pegawai__first_name__icontains=q) |
                Q(pegawai__last_name__icontains=q) |
                Q(jenis_sdm__profesi__profesi__icontains=q) |
                Q(instalasi__instalasi__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.get_filter_params()
        instalasi = self.get_active_instalasi()
        selelcted_instalasi = instalasi.instalasi if instalasi is not None else ''
        
        instalasi_list = self.get_instalasi_queryset()

        context['instalasi_list'] = instalasi_list
        context['instalasi_param'] = instalasi.pk if instalasi else None
        context['users'] = self.get_user_queryset()

        selected_user = self.get_user(params['nip'])
        penempatan = self.get_penempatan_object(params['nip'])
        jenis_sdm = self.get_jenis_sdm(params['nip'])
        jenis_sdm_nama = jenis_sdm.nama_jabatan if jenis_sdm else None

        form_initial = {
            'jenis_sdm': jenis_sdm_nama,
            'pegawai': selected_user,
            'unor': getattr(penempatan, 'penempatan_level1', None),
            'bidang': getattr(penempatan, 'penempatan_level2', None),
            'sub_bidang': getattr(penempatan, 'penempatan_level3', None),
            'instalasi': getattr(penempatan, 'penempatan_level4', None),
            'bulan': params['tanggal'].month,
            'tahun': params['tanggal'].year,
        }

        current_year = datetime.now().year
        querydict = self.request.GET.copy()
        querydict.pop('page', None)

        context.update({
            'form': JenisSDMPerinstalasiForm(initial=form_initial),
            'bulan_list': [(i, month_name[i]) for i in range(1, 13)],
            'tahun_list': list(range(current_year - 5, current_year + 6)),
            'bulan': params['bulan'],
            'tahun': params['tahun'],
            'selected_user': selected_user,
            'preserved_query': querydict.urlencode(),
            'query': params['query'],
            'searchform': SearchForm(self.request.GET or None),
            'instalasi':instalasi,
            'title_page': 'disiplin',
            'riwayat': 'active',
            'selected': 'disiplin',
            'title': f"Jadwal Kerja Unit/Instalasi {selelcted_instalasi}",
        })
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.warning(request, 'Maaf anda tidak berhak menambahkan jadwal pegawai!')
            return redirect(reverse('disiplinsdm_urls:jadwal_list'))

        form = JenisSDMPerinstalasiForm(request.POST)
        pegawai = form.data.get('pegawai')
        bulan = form.data.get('bulan')
        tahun = form.data.get('tahun')

        if pegawai and bulan and tahun:
            existing = JenisSDMPerinstalasi.objects.filter(pegawai__id=pegawai, bulan=bulan, tahun=tahun).first()
            if existing:
                messages.info(request, 'Jadwal sudah ada untuk pegawai ini pada bulan dan tahun tersebut.')
                return redirect(reverse('disiplinsdm_urls:jadwal_auto_create', kwargs={'pk': existing.pk}))

        if form.is_valid():
            with transaction.atomic():
                obj = form.save()
                generate_bulk_jadwal(obj, int(bulan), int(tahun))
            return redirect(reverse('disiplinsdm_urls:jadwal_auto_create', kwargs={'pk': obj.pk}))

        return render(request, self.template_name, {
            'form': form,
            'error': 'Form tidak valid.'
        })
    

class JadwalDinasFormsetUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):#view pembuatan multipiket 1 hari
    model = JenisSDMPerinstalasi
    fields = []
    template_name = 'jadwal_piket/jadwal_dinas_form.html'

    def get_success_url(self):
        query_params = self.request.GET.copy()
        if query_params:  # hanya jika ada query string
            return f'{reverse("disiplinsdm_urls:jadwal_list")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_list')
    
    def get_failure_url(self):
        pk = self.kwargs.get('pk')
        query_params = self.request.GET.copy()
        if query_params:
            return f'{reverse("disiplinsdm_urls:jadwal_auto_create", kwargs={"pk":pk})}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_auto_create', kwargs={'pk':pk})
    
    def test_func(self):
        if self.request.user.is_staff:
            return True
        return False
    
    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        messages.error(self.request, 'Anda tidak memiliki izin untuk membuat atau mengedit jadwal.')
        return redirect(self.get_success_url())
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        shift_tanggal = request.GET.get('shift_tanggal')
        if shift_tanggal:
            try:
                tanggal_obj = datetime.strptime(shift_tanggal, "%Y-%m-%d").date()
                label_hari = {
                    0: 'Senin s/d kamis',
                    1: 'Senin s/d kamis',
                    2: 'Senin s/d kamis',
                    3: 'Senin s/d kamis',
                    4: 'Jumat',
                    5: 'Sabtu',
                    6: 'Minggu'
                }
                label = label_hari[tanggal_obj.weekday()]
                kategori_default = DetailKategoriJadwalDinas.objects.filter(
                    kategori_dinas__kategori_dinas='Reguler',
                    hari=label_hari[0]
                ).first()

                JadwalDinasSDM.objects.create(
                    pegawai=self.object,
                    tanggal=tanggal_obj,
                    kategori_jadwal=kategori_default
                )
                messages.info(request, f"Shift baru ditambahkan untuk {tanggal_obj.strftime('%d %b %Y')}")
            except Exception as e:
                messages.error(request, f"Gagal menambahkan shift: {e}")
            return redirect(self.get_failure_url())
        
        return super().get(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = JadwalDinasSDM.objects.filter(
            pegawai=self.object,
            tanggal__year=self.object.tahun,
            tanggal__month=self.object.bulan
        ).order_by('tanggal')

        if self.request.POST:
            formset = update_jadwal_formset(data=self.request.POST, instance=self.object, queryset=queryset)
        else:
            formset = update_jadwal_formset(instance=self.object, queryset=queryset)

        minggu_formsets, total = self.build_mingguan_context(formset)

        context['formset'] = formset
        context['minggu_formsets'] = minggu_formsets
        context['total_bulanan'] = total
        context['url'] = reverse('disiplinsdm_urls:jadwal_list')
        context['title'] = 'Atur jadwal pegawai'
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        query_params = self.request.GET.copy()

        if formset.is_valid():
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.status = 'draft'
                self.object.save()
                formset.instance = self.object
                for f in formset.forms:
                    if not f.cleaned_data.get('kategori_jadwal'):
                        initial_value = f.initial.get('kategori_jadwal')
                        if initial_value:
                            f.instance.kategori_jadwal_id = initial_value
                formset.save()
            if 'ajukan' in self.request.POST:
                messages.success(self.request, "Silahkan cek kembali detail data yang telah dibuat sebelum disimpan!")
                if query_params:
                    return redirect(f'{reverse("disiplinsdm_urls:ajukan_jadwal", kwargs={"pk": self.object.pk})}?{query_params.urlencode()}')
                return redirect(reverse('disiplinsdm_urls:ajukan_jadwal', kwargs={'pk': self.object.pk}))
            else:
                messages.success(self.request, "Data berhasil disimpan sebagai draft.")
                return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
        
    def form_invalid(self, form):
        messages.error(self.request, 'Maaf data gagal disimpan!')
        context = self.get_context_data(form=form)
        context['query_params'] = self.request.GET.copy()
        return self.render_to_response(context)

    def build_mingguan_context(self, formset):
        minggu_list = get_mingguan_lengkap(self.object.bulan, self.object.tahun)
        minggu_formsets = []
        total = 0

        libur_set = set(HariLibur.objects.filter(
            tanggal__year=self.object.tahun,
            tanggal__month=self.object.bulan
        ).values_list('tanggal', flat=True))

        label_hari = {
            0: 'Senin s/d kamis',
            1: 'Senin s/d kamis',
            2: 'Senin s/d kamis',
            3: 'Senin s/d kamis',
            4: 'Jumat',
            5: 'Sabtu',
        }

        kategori_libur = DetailKategoriJadwalDinas.objects.filter(
            kategori_jadwal='Libur'
        ).first()

        from collections import defaultdict
        for minggu in minggu_list:
            tanggal_forms = defaultdict(list)
            for f in formset.forms:
                tgl = f.instance.tanggal
                if tgl and minggu[0] <= tgl <= minggu[-1]:
                    is_libur = tgl.weekday() == 6 or tgl in libur_set
                    f.is_hari_libur = is_libur

                    # Auto-assign kategori_jadwal jika kosong
                    if not f.instance.kategori_jadwal:
                        if is_libur:
                            f.initial['kategori_jadwal'] = kategori_libur
                        else:
                            label = label_hari.get(tgl.weekday())
                            default_kat = DetailKategoriJadwalDinas.objects.filter(
                                kategori_dinas__kategori_dinas='Reguler',
                                hari=label
                            ).first()
                            if default_kat:
                                f.initial['kategori_jadwal'] = default_kat

                    tanggal_forms[tgl].append(f)

            minggu_data = []
            for tgl, forms in sorted(tanggal_forms.items()):
                jam = hitung_total_jam(forms, DetailKategoriJadwalDinas)
                total += jam
                minggu_data.append({
                    'tanggal': tgl,
                    'forms': forms,
                    'total_jam': jam
                })

            minggu_formsets.append({
                'range': minggu,
                'data_harian': minggu_data,
                'total_jam': sum(h['total_jam'] for h in minggu_data)
            })

        return minggu_formsets, total

           
class JadwalDinasFormsetUpdateView2(generic.UpdateView):#view pembuatan jadwal hanya 1 piket 1 hari
    model = JenisSDMPerinstalasi
    fields = []
    template_name = 'jadwal_piket/jadwal_dinas_form.html'
    success_url = reverse_lazy('disiplinsdm_urls:jadwal_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            formset = update_jadwal_formset(data=self.request.POST, instance=self.object)
        else:
            formset = update_jadwal_formset(instance=self.object)
        minggu_formsets, total = self.build_mingguan_context(formset)
        context['formset'] = formset
        context['minggu_formsets'] = minggu_formsets
        context['total_bulanan'] = total
        context['url'] = reverse('disiplinsdm_urls:jadwal_list')
        context['title'] = 'Atur jadwal pegawai'
        context['riwayat'] ='active'
        context['selected'] ='disiplin'
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            with transaction.atomic():
                # Terapkan nilai initial yang tidak terkirim dalam POST
                for f in formset.forms:
                    if not f.cleaned_data.get('kategori_jadwal'):
                        initial_value = f.initial.get('kategori_jadwal')
                        if initial_value:
                            f.instance.kategori_jadwal_id = initial_value
                formset.save()
                messages.success(self.request, 'Data berhasil disimpan!')
            return super().form_valid(form)
        else:
            messages.error(self.request, 'Maaf data gagal disimpan!')
            print('formset: ', formset.errors)
            print('form: ', form.errors)
            return self.form_invalid(form)
        
    def build_mingguan_context(self, formset):
        minggu_list = get_mingguan_lengkap(self.object.bulan, self.object.tahun)
        minggu_formsets = []
        total = 0

        libur_set = set(HariLibur.objects.filter(
            tanggal__year=self.object.tahun,
            tanggal__month=self.object.bulan
        ).values_list('tanggal', flat=True))

        label_hari = {
            0: 'Senin s/d kamis',
            1: 'Senin s/d kamis',
            2: 'Senin s/d kamis',
            3: 'Senin s/d kamis',
            4: 'Jumat',
            5: 'Sabtu',
        }

        kategori_libur = DetailKategoriJadwalDinas.objects.filter(
            kategori_jadwal='Libur'
        ).first()

        for minggu in minggu_list:
            forms = []
            for f in formset.forms:
                tgl = f.instance.tanggal
                if tgl and minggu[0] <= tgl <= minggu[-1]:
                    is_libur = tgl.weekday() == 6 or tgl in libur_set
                    f.is_hari_libur = is_libur
                    if not f.instance.kategori_jadwal:
                        if is_libur:
                            f.initial['kategori_jadwal'] = kategori_libur
                        else:
                            label = label_hari.get(tgl.weekday())
                            default_kat = DetailKategoriJadwalDinas.objects.filter(
                                kategori_dinas__kategori_dinas='Reguler',
                                hari=label
                            ).first()
                            if default_kat:
                                f.initial['kategori_jadwal'] = default_kat
                    forms.append(f)        
                    
            jam = hitung_total_jam(forms, DetailKategoriJadwalDinas)
            total += jam
            minggu_formsets.append({
                'range': minggu,
                'formset': forms,
                'total_jam': jam
            })

        return minggu_formsets, total

    
class JadwalDinasDetailView(LoginRequiredMixin, generic.DetailView):#view untuk multipiket perhari
    model = JenisSDMPerinstalasi
    template_name = 'jadwal_piket/jadwal_detail.html'
    context_object_name = 'object'
    
    def back_url(self):
        query_params = self.request.GET.copy()
        if query_params:
            return f'{reverse("disiplinsdm_urls:jadwal_list")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        jadwal_list = obj.jadwaldinassdm_set.select_related('kategori_jadwal').order_by('tanggal')

        minggu_data = []
        minggu_list = get_mingguan_lengkap(obj.bulan, obj.tahun)
        libur_set = set(HariLibur.objects.filter(
            tanggal__year=obj.tahun,
            tanggal__month=obj.bulan
        ).values_list('tanggal', flat=True))

        total_bulanan = 0
        for minggu in minggu_list:
            hari_data = []
            total_mingguan = 0
            for jadwal in jadwal_list:
                if minggu[0] <= jadwal.tanggal <= minggu[-1]:
                    datang = jadwal.kategori_jadwal.waktu_datang if jadwal.kategori_jadwal else None
                    pulang = jadwal.kategori_jadwal.waktu_pulang if jadwal.kategori_jadwal else None
                    jam = 0
                    if datang and pulang:
                        mulai = datetime.combine(jadwal.tanggal, datang)
                        selesai = datetime.combine(jadwal.tanggal, pulang)
                        if selesai < mulai:
                            selesai += timedelta(days=1)
                        jam = round((selesai - mulai).total_seconds() / 3600, 1)
                    total_mingguan += jam
                    total_bulanan += jam
                    hari_data.append({
                        'tanggal': jadwal.tanggal,
                        'kategori': jadwal.kategori_jadwal,
                        'jam': jam,
                        'catatan': jadwal.catatan,
                        'libur': jadwal.tanggal.weekday() == 6 or jadwal.tanggal in libur_set
                    })
            minggu_data.append({
                'range': minggu,
                'data': hari_data,
                'total_jam': total_mingguan,
            })

        context.update({
            'minggu_data': minggu_data,
            'total_bulanan': total_bulanan,
            'standar_min': obj.standar_min_efektif,
            'standar_max': obj.standar_max_efektif,
            'selisih': obj.selisih_jam_kerja,
            'can_approve': self.request.user.is_staff,
        })
        context['url'] = self.back_url()
        context['title'] = 'Lihat Jadwal Pegawai'
        context['title_page'] = 'Lihat Jadwal'
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        return context
    

class SalinJadwalView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'jadwal_piket/jadwal_salin_form.html'
    
    def get_success_url(self):
        query_params = self.request.GET.copy()
        if query_params:
            return f'{reverse("disiplinsdm_urls:jadwal_list")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_list')
    
    def get_failure_url(self):
        query_params = self.request.GET.copy()
        if query_params:
            return f'{reverse("disiplinsdm_urls:salin_jadwal")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:salin_jadwal')
    
    def test_func(self):
        if self.request.user.is_staff:
            return True
        return False

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        messages.error(self.request, 'Anda tidak memiliki izin untuk menyalin data.')
        return redirect(self.get_success_url())

    
    def get_instalasi(self, user):
        penempatan = None
        if user:
            penempatan = RiwayatPenempatan.objects.filter(pegawai=user, status=True).first()
        return penempatan
    
    def get_initial_jadwal(self, user, bulan, tahun):
        jadwal = None
        if user and bulan and tahun:
            jadwal = JenisSDMPerinstalasi.objects.filter(pegawai=user, bulan=bulan, tahun=tahun)
        return jadwal
    
    def get_pegawai(self, pk):
        try:
            if pk:
                data = Users.objects.get(pk=pk)
                return data
            else:
                return None
        except Users.DoesNotExist:
            return None

    def get(self, request):
        login_user = self.request.user
        sumber = request.GET.get('sumber')
        tujuan = request.GET.get('tujuan')
        tgl = request.GET.get('tanggal')
        tanggal = get_date_from_string(tgl)
        data_user = Users.objects.all().exclude(is_superuser=True, is_active=False).prefetch_related('riwayatpenempatan_set')
        if login_user.is_superuser:
            users = data_user
        elif login_user.is_staff and not login_user.is_superuser:
            if login_user.profil_admin.instalasi.exists():
                users = data_user.filter(riwayatpenempatan__penempatan_level4__in = login_user.profil_admin.instalasi.values_list('pk', flat=True), riwayatpenempatan__status=True)
            elif login_user.profil_admin.sub_bidang:
                users = data_user.filter(riwayatpenempatan__penempatan_level3 = login_user.profil_admin.sub_bidang, riwayatpenempatan__status=True)
            elif login_user.profil_admin.bidang:
                users = data_user.filter(riwayatpenempatan__penempatan_level2 = login_user.profil_admin.bidang, riwayatpenempatan__status=True)
            elif login_user.profil_admin.unor:
                users = data_user.filter(riwayatpenempatan__penempatan_level1 = login_user.profil_admin.unor, riwayatpenempatan__status=True)
        
        bulan = tanggal.month
        tahun = tanggal.year
        selected_instalasi = self.get_instalasi(sumber)
        selected_sumber = self.get_pegawai(sumber)
        selected_tujuan = self.get_pegawai(tujuan)
        selected_jadwal = self.get_initial_jadwal(tujuan, bulan, tahun)
        initial = {
            'instalasi': selected_instalasi,
            'sumber': selected_sumber,
            'tujuan': selected_tujuan,
            'bulan':bulan,
            'tahun':tahun
        }
        form = SalinJadwalForm(initial=initial, instance={
            'sumber':selected_sumber, 
            'tujuan':selected_tujuan, 
            'instalasi':selected_instalasi}
        )
        context = {
            'users':users,
            'form':form,
            'title':'Copy jadwal pegawai',
            'selected_instalasi': selected_instalasi,
            'selected_sumber':selected_sumber,
            'selected_tujuan':selected_tujuan,
            'selected_jadwal':selected_jadwal,
            'url': reverse('disiplinsdm_urls:jadwal_list'),
            'riwayat':'active',
            'selected': 'disiplin',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = SalinJadwalForm(request.POST)
        if form.is_valid():
            sumber = form.cleaned_data['sumber']
            tujuan = form.cleaned_data['tujuan']
            bulan = form.cleaned_data['bulan']
            tahun = form.cleaned_data['tahun']

            sumber_inst = JenisSDMPerinstalasi.objects.filter(
                pegawai=sumber, bulan=bulan, tahun=tahun
            ).first()

            if not sumber_inst:
                messages.warning(request, "Pegawai sumber belum memiliki metadata jadwal bulan ini.")
                return render(request, self.template_name, {'form': form})
            
            # Cek/siapkan metadata untuk pegawai tujuan
            tujuan_inst, _ = JenisSDMPerinstalasi.objects.get_or_create(
                pegawai=tujuan,
                bulan=bulan,
                tahun=tahun,
                defaults={
                    'unor': sumber_inst.unor,
                    'bidang': sumber_inst.bidang,
                    'sub_bidang': sumber_inst.sub_bidang,
                    'instalasi': sumber_inst.instalasi,
                    'jenis_sdm': sumber_inst.jenis_sdm
                }
            )

            # Hapus jadwal lama (jika ada)
            JadwalDinasSDM.objects.filter(pegawai=tujuan_inst).delete()

            # Ambil semua jadwal dari pegawai sumber
            jadwal_sumber = JadwalDinasSDM.objects.filter(
                pegawai=sumber_inst
            ).only('tanggal', 'kategori_jadwal')  # Optimasi: ambil field yang dibutuhkan saja

            # Siapkan list untuk bulk_create
            jadwal_baru = []

            for j in jadwal_sumber:
                try:
                    tanggal_baru = j.tanggal.replace(month=bulan, year=tahun)
                    jadwal_baru.append(JadwalDinasSDM(
                        pegawai=tujuan_inst,
                        tanggal=tanggal_baru,
                        kategori_jadwal=j.kategori_jadwal
                    ))
                except ValueError:
                    continue  # Lewati error tanggal (misalnya 31 ke Februari)

            # Simpan sekaligus ke database
            JadwalDinasSDM.objects.bulk_create(jadwal_baru)
            messages.success(request,f"Berhasil menyalin {len(jadwal_baru)} entri jadwal dari {sumber.full_name} ke {tujuan.full_name}.")
            return redirect(self.get_success_url())
        return redirect(self.get_failure_url())


class SalinJadwalInstalasiView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'jadwal_piket/jadwal_salin_instalasi_form.html'
    
    def get_success_url(self):
        query_params = self.request.GET.copy()
        if query_params:
            return f'{reverse("disiplinsdm_urls:jadwal_list")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_list')
    
    def get_failure_url(self):
        query_params = self.request.GET.copy()
        if query_params:
            return f'{reverse("disiplinsdm_urls:salin_jadwal_instalasi")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:salin_jadwal_instalasi')
    
    def test_func(self):
        if self.request.user.is_staff:
            return True
        return False

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        messages.error(self.request, 'Anda tidak memiliki izin untuk menyalin data.')
        return redirect(self.get_success_url())

    def get(self, request):
        form = SalinJadwalInstalasiForm(user=self.request.user)
        context = {
            'title':'Silahkan buat jadwal instalasi anda berdasarkan jadwal pada bulan sebelumnya',
            'url' : self.get_success_url(),
            'form': form
        }
        return render(request, self.template_name, context)

    def post(self, request):
        user = self.request.user
        form = SalinJadwalInstalasiForm(request.POST, user=user)
        if form.is_valid():
            instalasi = form.cleaned_data['instalasi']
            bulan_sumber = int(form.cleaned_data['bulan_sumber'])
            tahun_sumber = form.cleaned_data['tahun_sumber']
            bulan_tujuan = int(form.cleaned_data['bulan'])
            tahun_tujuan = form.cleaned_data['tahun']

            sumber_jadwal = JenisSDMPerinstalasi.objects.filter(
                instalasi=instalasi,
                bulan=bulan_sumber,
                tahun=tahun_sumber
            ).prefetch_related('jadwaldinassdm_set', 'pegawai')

            total_jadwal_dibuat = 0
            for item in sumber_jadwal:
                # Cari instalasi aktif pegawai saat ini (bisa saja sudah pindah)
                riwayat_aktif = RiwayatPenempatan.objects.filter(
                    pegawai=item.pegawai, status=True
                ).first()

                instalasi_aktif = riwayat_aktif.penempatan_level4 if riwayat_aktif else item.instalasi

                tujuan_obj, _ = JenisSDMPerinstalasi.objects.get_or_create(
                    pegawai=item.pegawai,
                    instalasi=instalasi_aktif,
                    bulan=bulan_tujuan,
                    tahun=tahun_tujuan,
                    defaults={
                        'unor': item.unor,
                        'bidang': item.bidang,
                        'sub_bidang': item.sub_bidang,
                        'jenis_sdm': item.jenis_sdm,
                    }
                )

                # Hapus jadwal lama tujuan
                JadwalDinasSDM.objects.filter(pegawai=tujuan_obj).delete()

                # Persiapkan bulk_create
                daftar_jadwal = []
                for jadwal in item.jadwaldinassdm_set.all():
                    try:
                        tanggal_baru = jadwal.tanggal.replace(month=bulan_tujuan, year=tahun_tujuan)
                        daftar_jadwal.append(JadwalDinasSDM(
                            pegawai=tujuan_obj,
                            tanggal=tanggal_baru,
                            kategori_jadwal=jadwal.kategori_jadwal
                        ))
                    except ValueError:
                        continue  # lewati misal 31 Feb

                JadwalDinasSDM.objects.bulk_create(daftar_jadwal)
                total_jadwal_dibuat += len(daftar_jadwal)

            messages.success(request, f"Berhasil menyalin {total_jadwal_dibuat} entri jadwal ke bulan {bulan_tujuan}/{tahun_tujuan}.")
            return redirect(self.get_success_url())
        messages.error(request, 'Form tidak valid. Silahkan periksa kembali.')
        return redirect(self.get_failure_url())
    

class JadwalUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = JenisSDMPerinstalasi
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name='next'
    form_class = JenisSDMPerinstalasiBasicForm
    template_name = 'kehadirankegiatan/form.html'
    
    def test_func(self):
        if self.request.user.is_staff:
            return True
        return False

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        messages.error(self.request, 'Anda tidak memiliki izin untuk edit data.')
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        query_params = self.request.GET.copy()
        if query_params:  # hanya jika ada query string
            return f'{reverse("disiplinsdm_urls:jadwal_list")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_list')

    def form_invalid(self, form):
        messages.error(self.request, 'Maaf data gagal disimpan!')
        # Simpan query params untuk mengembalikan ke halaman yang sama
        query_params = self.request.GET.copy()
        context = self.get_context_data(form=form)
        context['query_params'] = query_params
        return self.render_to_response(context)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit jadwal pegawai'
        context['url'] = self.get_success_url()
        return context
    
    
class DeleteJadwalView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        if self.request.user.is_staff:
            return True
        return False
    
    def get_success_url(self):
        query_params = self.request.GET.copy()
        if query_params:  # hanya jika ada query string
            return f'{reverse("disiplinsdm_urls:jadwal_list")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_list')

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        messages.error(self.request, 'Anda tidak memiliki izin untuk menghapus data.')
        return redirect(self.get_success_url())
    
    def get_object(self, id):
        try:
            data = JenisSDMPerinstalasi.objects.get(id=id)
            return data
        except JenisSDMPerinstalasi.DoesNotExist:
            return None
        
    def get(self, request, *args, **kwargs):
        id_jadwal = kwargs.get('id')
        instance = self.get_object(id_jadwal)
        context={
            'delete_jadwal':True,
            'data':instance,
            'url':reverse_lazy('disiplinsdm_urls:jadwal_list'),
            'title': 'Delete jadwal pegawai',
            'sub_page':'Riwayat',
            'title_page':'disiplin',
            'riwayat':'active',
            'selected':'disiplin'
        }
        return render(request, 'jadwal_piket/validasi_delete_jadwal.html', context)
    
    def post(self, request, **kwargs):
        id_jadwal = kwargs.get('id')
        instance = self.get_object(id_jadwal)
        instance.delete()
        return redirect(self.get_success_url())
    
    
class VerifikasiJadwalView(FormView):
    template_name = 'jadwal_piket/verifikasi_jadwal.html'
    form_class = PersetujuanForm

    def dispatch(self, request, *args, **kwargs):
        self.pengajuan = get_object_or_404(JenisSDMPerinstalasi, pk=self.kwargs['pk'], status='diajukan')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {
            'alasan': self.pengajuan.alasan_penolakan if self.pengajuan.alasan_penolakan else ''
        }
        return kwargs
    
    def get_success_url(self):
        query_params = self.request.GET.copy()
        if query_params:  # hanya jika ada query string
            return f'{reverse("disiplinsdm_urls:jadwal_list")}?{query_params.urlencode()}'
        return reverse('disiplinsdm_urls:jadwal_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pengajuan = self.pengajuan

        draft_set = JadwalDinasSDM.objects.filter(pegawai=pengajuan)
        approved_set = ApprovedJadwalDinasSDM.objects.filter(pegawai=pengajuan)
        approved_set = ApprovedJadwalDinasSDM.objects.filter(pegawai=pengajuan)
        total_jam_disetujui = 0

        for jadwal in approved_set:
            kategori = jadwal.kategori_jadwal
            if kategori and kategori.waktu_datang and kategori.waktu_pulang:
                datang = datetime.combine(datetime.today(), kategori.waktu_datang)
                pulang = datetime.combine(datetime.today(), kategori.waktu_pulang)
                if pulang < datang:
                    # Shift malam, tambahkan 1 hari ke pulang
                    pulang += timedelta(days=1)
                durasi = pulang - datang
                total_jam_disetujui += durasi.total_seconds() / 3600  # konversi ke jam

        tanggal_list = sorted(set(draft_set.values_list('tanggal', flat=True)) | set(approved_set.values_list('tanggal', flat=True)))
        perbandingan = []

        for tanggal in tanggal_list:
            draft = draft_set.filter(tanggal=tanggal).first()
            approved = approved_set.filter(tanggal=tanggal).first()
            perbandingan.append({
                'tanggal': tanggal,
                'jadwal_draft': draft.kategori_jadwal.kategori_jadwal if draft and draft.kategori_jadwal else '-',
                'jadwal_approved': approved.kategori_jadwal.kategori_jadwal if approved and approved.kategori_jadwal else '-',
                'status': '✅ Sama' if draft and approved and draft.kategori_jadwal == approved.kategori_jadwal else '❌ Berbeda',
                'catatan': draft.catatan or approved.catatan or '-'
            })

        context.update({
            'title': f'Verifikasi Jadwal: { pengajuan.pegawai.full_name } ({ pengajuan.bulan }/{ pengajuan.tahun })',
            'riwayat': 'active',
            'selected': 'disiplin',
            'url': reverse('disiplinsdm_urls:jadwal_list'),
            'pengajuan': pengajuan,
            'perbandingan_jadwal': perbandingan,
            'jam_aktual': pengajuan.kurang_lebih_jam_kerja,
            'jam_min': pengajuan.standar_min_efektif,
            'jam_max': pengajuan.standar_max_efektif,
            'selisih': pengajuan.selisih_jam_kerja,
            'jam_disetujui': round(total_jam_disetujui, 1),
        })
        return context

    def form_valid(self, form):
        alasan = form.cleaned_data['alasan']
        
        aksi = self.request.POST.get("aksi")
        if aksi == 'tolak':
            if not alasan:
                messages.error(self.request, "Mohon isi alasan penolakan jika ingin menolak jadwal.")
                return super().form_invalid(form)

            self.pengajuan.status = 'ditolak'
            self.pengajuan.alasan_penolakan = alasan
            self.pengajuan.save()

            messages.success(self.request, f"Jadwal berhasil ditolak.")
            return super().form_valid(form)

        elif aksi == 'setujui':
            with transaction.atomic():
                self.pengajuan.status = 'disetujui'
                self.pengajuan.alasan_penolakan = alasan
                self.pengajuan.save()
                for jadwal in JadwalDinasSDM.objects.filter(pegawai=self.pengajuan):
                    ApprovedJadwalDinasSDM.objects.update_or_create(
                        pegawai=self.pengajuan,
                        tanggal=jadwal.tanggal,
                        defaults={
                            'kategori_jadwal':jadwal.kategori_jadwal, 
                            'catatan':jadwal.catatan,
                            'is_approved':True,
                            'approved_by':self.request.user,
                        }
                    )
            return super().form_valid(form)
        
    def form_invalid(self, form):
        print("Form invalid")
        print(form.errors)
        return super().form_invalid(form)
    

class KehadiranListView(LoginRequiredMixin, generic.ListView):
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    model = DaftarKegiatanPegawai
    template_name = 'kehadirankegiatan/kehadiran_list.html'

    def get_date_params(self):
        """Parse tanggal dari query string dan kembalikan bulan dan tahun."""
        tgl = self.request.GET.get('tanggal')
        get_tanggal = get_date_from_string(tgl)
        return get_tanggal, get_tanggal.month, get_tanggal.year

    def get_instalasi(self):
        """Ambil dan validasi parameter instalasi dari query string."""
        inst_id = self.request.GET.get('inst')
        if inst_id and inst_id.strip():
            try:
                return UnitInstalasi.objects.get(id=inst_id)
            except UnitInstalasi.DoesNotExist:
                return None
        return None

    def get_queryset_for_user(self, bulan, tahun, instalasi):
        """Kembalikan queryset berdasarkan role user."""
        base_filter = {
            'bulan': bulan,
            'tahun': tahun,
            'kegiatan__slug': 'absen-datang',
        }
        # Jika user adalah superuser, filter berdasarkan instalasi jika ada
        if self.request.user.is_superuser:
            if instalasi:
                base_filter['instalasi'] = instalasi
            return DaftarKegiatanPegawai.objects.filter(**base_filter)

        elif self.request.user.is_staff:
            profil = self.request.user.profil_admin
            if instalasi:
                if isinstance(instalasi, QuerySet):
                    instalasi = instalasi.pk
                    base_filter['instalasi'] = instalasi
                else:
                    base_filter['instalasi'] = instalasi
            elif profil.instalasi.exists():
                base_filter['instalasi__in'] = profil.instalasi.values_list('pk', flat=True)
            elif profil.sub_bidang:
                base_filter['sub_bidang'] = profil.sub_bidang
            elif profil.bidang:
                base_filter['bidang'] = profil.bidang
            return DaftarKegiatanPegawai.objects.filter(**base_filter)

        # Default untuk user biasa (pegawai)
        base_filter['pegawai'] = self.request.user
        return DaftarKegiatanPegawai.objects.filter(**base_filter)

    def get_queryset(self):
        tanggal, bulan, tahun = self.get_date_params()
        instalasi = self.get_instalasi()
        queryset = self.get_queryset_for_user(bulan, tahun, instalasi)
        return queryset.order_by('pegawai__first_name', 'pegawai__last_name')
    
    def get_instalasi_list(self):
        instalasi = None
        if self.request.user.is_superuser:
            instalasi = UnitInstalasi.objects.filter(jenissdmperinstalasi__isnull=False).order_by('instalasi').distinct()

        elif self.request.user.is_staff:
            profil = self.request.user.profil_admin
            if profil.instalasi.exists():
                instalasis = profil.instalasi.values_list('pk', flat=True)
                instalasi = UnitInstalasi.objects.filter(pk__in=instalasis)
            elif profil.sub_bidang:
                instalasi = UnitInstalasi.objects.filter(sub_bidang=profil.sub_bidang)
            elif profil.bidang:
                instalasi = UnitInstalasi.objects.filter(sub_bidang__bidang=profil.bidang)
        return instalasi

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tanggal, bulan, tahun = self.get_date_params()
        context.update({
            'instalasi_list': self.get_instalasi_list(),
            'bulan': bulan,
            'tahun': tahun,
            'title': 'Daftar Kehadiran Pegawai',
            'page': 'Home',
            'sub_page': 'Riwayat',
            'title_page': 'Disiplin',
            'riwayat': 'active',
            'selected': 'disiplin',
            'url': reverse('disiplinsdm_urls:jadwal_list'),
        })
        return context


class DetailKehadiranListView(LoginRequiredMixin, generic.ListView):
    login_url = reverse_lazy('myaccount_urls:login_view')
    model = KehadiranKegiatan
    template_name = 'kehadirankegiatan/kehadiran_detail_list.html'
    
    def get_queryset(self):
        id_presensi = self.kwargs['id']
        try:
            presensi = DaftarKegiatanPegawai.objects.get(id=id_presensi)
            pegawai = presensi.pegawai
        except DaftarKegiatanPegawai.DoesNotExist:
            pegawai = None
        bulan = int(self.request.GET.get('bulan', datetime.today().month))
        tahun = int(self.request.GET.get('tahun', datetime.today().year))
        
        queryset = (
            KehadiranKegiatan.objects
            .filter(
                pegawai__pegawai=pegawai,
                tanggal__month=bulan,
                tanggal__year=tahun
            )
            .annotate(tgl=TruncDate('tanggal'))
            .values('tgl')
            .annotate(
                jam_datang=Min(
                    Case(
                        When(pegawai__kegiatan__jenis_kegiatan='Absen Datang',
                             then=Cast('tanggal', output_field=TimeField()))
                    )
                ),
                jam_pulang=Max(
                    Case(
                        When(pegawai__kegiatan__jenis_kegiatan='Absen Pulang',
                             then=Cast('tanggal', output_field=TimeField()))
                    )
                ),
                status=Max(
                    Case(
                        When(hadir=True, then=Value('Hadir')),
                        When(hadir=False, then=Value('Tidak Hadir')),
                        default=Value('-'),
                        output_field=CharField()
                    )
                ),
                ketepatan=Max('status_ketepatan'),
                alasan=Max('alasan__alasan'),
                keterangan=Max('ket'),
            )
            .order_by('tgl')
        )
        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        id_presensi = self.kwargs['id']
        presensi = DaftarKegiatanPegawai.objects.filter(id=id_presensi).first() if DaftarKegiatanPegawai.objects.filter(id=id_presensi) is not None else None
        context['presensi'] = presensi
        context['bulan'] = self.request.GET.get('bulan')
        context['tahun'] = self.request.GET.get('tahun')
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        context['title'] = 'Detail Kehadiran Pegawai'
        context['url'] = reverse_lazy('disiplinsdm_urls:kehadiran_list')
        return context

    
class KehadiranCreateView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = DaftarKegiatanPegawai
    form_class = DaftarKegiatanPegawaiForm
    template_name = 'kehadirankegiatan/kehadiran_form.html'
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    # success_url = reverse_lazy('disiplinsdm_urls:kehadiran_list')
    
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        return False

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        messages.error(self.request, 'Anda tidak memiliki izin untuk menambah kehadiran data.')
        return redirect(reverse('disiplinsdm_urls:kehadiran_list'))
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        tanggal = date.today()
        tgl = self.request.GET.get('tanggal')
        if tgl is not None:
            tanggal = get_date_from_string(tgl)
        if self.request.user.is_superuser:
            kwargs['request'] = self.request
            kwargs['tanggal'] = tanggal
        else:
            kwargs['initial'] = {
                'pegawai': self.request.user,
            }
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formset = kehadiran_formset(data=self.request.POST or None)
        context['formset']=formset
        context['url'] = reverse_lazy('disiplinsdm_urls:kehadiran_list')
        context['title'] = 'Daftar Kehadiran Pegawai'
        context['page'] = 'Home'
        context['sub_page'] = 'Riwayat'
        context['title_page'] = 'Disiplin'
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
                messages.success(self.request, 'Data berhasil disimpan!')
            return super().form_valid(form)
        else:
            messages.error(self.request, 'Maaf data gagal disimpan!')
            return self.form_invalid(form)
        
    def get_success_url(self):
        url = reverse('disiplinsdm_urls:kehadiran_update', kwargs={'pk':self.object.pk})
        return url
        
        
class KehadiranUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = DaftarKegiatanPegawai
    form_class = DaftarKegiatanPegawaiForm
    template_name = 'kehadirankegiatan/kehadiran_update_form.html'
    login_url = reverse_lazy('myaccount_urls:login_view')
    redirect_field_name = 'next'
    
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        return False

    def handle_no_permission(self):
        # Bisa redirect atau tampilkan pesan khusus
        messages.error(self.request, 'Anda tidak memiliki izin untuk mengedit kehadiran data.')
        return redirect(reverse('disiplinsdm_urls:kehadiran_list'))
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        tanggal = date.today()
        tgl = self.request.GET.get('tanggal')
        if tgl is not None:
            tanggal = get_date_from_string(tgl)
        if self.request.user.is_superuser:
            kwargs['request'] = self.request
            kwargs['tanggal'] = tanggal
        else:
            kwargs['initial'] = {
                'pegawai': self.request.user,
            }
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formset = kehadiran_formset(data=self.request.POST or None, instance=self.object)
        context['formset']=formset
        context['url'] = reverse_lazy('disiplinsdm_urls:kehadiran_list')
        context['title'] = 'Daftar Kehadiran Pegawai'
        context['page'] = 'Home'
        context['sub_page'] = 'Riwayat'
        context['title_page'] = 'Disiplin'
        context['riwayat'] = 'active'
        context['selected'] = 'disiplin'
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
                messages.success(self.request, 'Data berhasil disimpan!')
            return super().form_valid(form)
        else:
            messages.error(self.request, 'Maaf data gagal disimpan!')
            return self.form_invalid(form)
        
    def form_invalid(self, form):
        print('error form: ', form.errors)
        messages.error(self.request, 'Maaf data gagal tersimpan!')
        return super().form_invalid(form)
        
    def get_success_url(self):
        url = reverse('disiplinsdm_urls:kehadiran_update', kwargs={'pk':self.object.pk})
        return url


# finger setelah ditambahkan dokter spesialis
class FingerprintProcessor:
    def __init__(self, file):
        self.file = file
        self.scan_record = set()
        self.tanggal_diproses = set()

    def run(self):
        wb = load_workbook(self.file)
        ws = wb.active
        self._proses_scan(ws)
        self._tandai_tidak_hadir()

    def _cek_status_ketepatan(self, tipe, jam_scan, jam_referensi):
        if not jam_referensi:
            return None
        if tipe == 'Absen Datang' and jam_scan > jam_referensi:
            return 'Terlambat'
        elif tipe == 'Absen Pulang' and jam_scan < jam_referensi:
            return 'Cepat Pulang'
        return 'Tepat Waktu'

    def _proses_scan(self, worksheet):
        for row in worksheet.iter_rows(min_row=3):
            waktu_scan = row[0].value
            try:
                if isinstance(waktu_scan, str):
                    waktu_scan = parse(waktu_scan.replace('.', ':'), dayfirst=True)
                elif isinstance(waktu_scan, float):
                    waktu_scan = from_excel(waktu_scan)
                elif not isinstance(waktu_scan, datetime):
                    continue
            except Exception:
                continue

            nip = str(row[4].value).strip() if row[4].value else None
            io_flag = row[10].value  # 1 = Masuk, 2 = Pulang

            if not waktu_scan or not nip or io_flag not in [1, 2]:
                continue

            tanggal_asli = waktu_scan.date()
            tipe_kegiatan = 'Absen Datang' if io_flag == 1 else 'Absen Pulang'
            nip_bersih = nip.replace(' ', '')
            self.scan_record.add((nip_bersih, tipe_kegiatan, tanggal_asli))
            self.tanggal_diproses.add(tanggal_asli)

            try:
                profil = ProfilSDM.objects.get(nip=nip_bersih)
                pengguna = profil.user
                kegiatan, _ = JenisKegiatan.objects.get_or_create(jenis_kegiatan=tipe_kegiatan)
                relasi_sdm = pengguna.jenissdmperinstalasi_set.filter(
                    bulan=tanggal_asli.month, tahun=tanggal_asli.year
                ).last()

                daftar, _ = DaftarKegiatanPegawai.objects.get_or_create(
                    pegawai=pengguna,
                    kegiatan=kegiatan,
                    bulan=tanggal_asli.month,
                    tahun=tanggal_asli.year,
                    defaults={
                        'jenis_sdm': relasi_sdm.jenis_sdm if relasi_sdm else None,
                        'unor': relasi_sdm.unor if relasi_sdm else None,
                        'bidang': relasi_sdm.bidang if relasi_sdm else None,
                        'sub_bidang': relasi_sdm.sub_bidang if relasi_sdm else None,
                        'instalasi': relasi_sdm.instalasi if relasi_sdm else None,
                    }
                )
                
                # Coba ambil jadwal hari ini
                tanggal_scan = tanggal_asli
                jadwal_dinas = ApprovedJadwalDinasSDM.objects.filter(
                    pegawai__pegawai=pengguna,
                    tanggal=tanggal_scan
                ).first()

                # Kalau absen pulang, cek shift malam sebelumnya
                if not jadwal_dinas and tipe_kegiatan == 'Absen Pulang':
                    malam_sebelumnya = tanggal_scan - timedelta(days=1)
                    jadwal_dinas = ApprovedJadwalDinasSDM.objects.filter(
                        pegawai__pegawai=pengguna,
                        tanggal=malam_sebelumnya,
                        kategori_jadwal__kategori_jadwal='Malam'
                    ).first()

                # === Jika dokter spesialis tanpa jadwal tetap ===
                if profil.is_dokter_spesialis and not jadwal_dinas and tipe_kegiatan in ['Absen Datang', 'Absen Pulang']:
                    KehadiranKegiatan.objects.get_or_create(
                        pegawai=daftar,
                        tanggal=make_aware(waktu_scan),
                        defaults={
                            'hadir': True,
                            'status_ketepatan': None,
                            'catatan': 'Visite atau cyto spesialis'
                        }
                    )
                    continue  # Lewati proses ketepatan waktu

                # Jika tidak ada jadwal sama sekali, lewati
                if not jadwal_dinas:
                    continue

                jam_referensi = getattr(
                    jadwal_dinas.kategori_jadwal,
                    'waktu_datang' if tipe_kegiatan == 'Absen Datang' else 'waktu_pulang',
                    None
                )
                status = self._cek_status_ketepatan(tipe_kegiatan, waktu_scan.time(), jam_referensi)

                KehadiranKegiatan.objects.get_or_create(
                    pegawai=daftar,
                    tanggal=make_aware(waktu_scan),
                    defaults={
                        'hadir': True,
                        'status_ketepatan': status
                    }
                )
            except ProfilSDM.DoesNotExist:
                continue

    def _tandai_tidak_hadir(self):
        alasan_tk, _ = AlasanTidakHadir.objects.get_or_create(alasan='Tanpa Keterangan')

        for tanggal in self.tanggal_diproses:
            jadwal_masuk = ApprovedJadwalDinasSDM.objects.filter(
                tanggal=tanggal,
                kategori_jadwal__kategori_dinas__kategori_dinas__in=['Reguler', 'Piket']
            )
            for jadwal in jadwal_masuk:
                pengguna = jadwal.pegawai.pegawai
                profil = getattr(pengguna, 'profil_user', None)
                if not profil:
                    continue
                #if profil.is_dokter_spesialis:
                #    continue  # Jangan tandai tidak hadir untuk dokter spesialis

                nip = profil.nip
                nip_bersih = nip.replace(' ', '')
                key_datang = (nip_bersih, 'Absen Datang', tanggal)
                key_pulang = (nip_bersih, 'Absen Pulang', tanggal)

                if key_datang not in self.scan_record and key_pulang not in self.scan_record:
                    try:
                        kegiatan, _ = JenisKegiatan.objects.get_or_create(jenis_kegiatan='Absen Datang')
                        relasi_sdm = pengguna.jenissdmperinstalasi_set.filter(
                            bulan=tanggal.month, tahun=tanggal.year
                        ).first()

                        daftar, _ = DaftarKegiatanPegawai.objects.get_or_create(
                            pegawai=pengguna,
                            kegiatan=kegiatan,
                            bulan=tanggal.month,
                            tahun=tanggal.year,
                            defaults={
                                'jenis_sdm': relasi_sdm.jenis_sdm if relasi_sdm else None,
                                'unor': relasi_sdm.unor if relasi_sdm else None,
                                'bidang': relasi_sdm.bidang if relasi_sdm else None,
                                'sub_bidang': relasi_sdm.sub_bidang if relasi_sdm else None,
                                'instalasi': relasi_sdm.instalasi if relasi_sdm else None,
                            }
                        )

                        KehadiranKegiatan.objects.get_or_create(
                            pegawai=daftar,
                            tanggal=make_aware(datetime.combine(tanggal, time.min)),
                            defaults={
                                'hadir': False,
                                'alasan': alasan_tk
                            }
                        )
                    except ProfilSDM.DoesNotExist:
                        continue
                    

class FingerprintAutoUploadView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'kehadirankegiatan/form.html'
    form_class = UploadFingerprintForm
    success_url = reverse_lazy('disiplinsdm_urls:kehadiran_list')

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, 'Anda tidak memiliki izin untuk upload data presensi.')
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Upload Fingerprint',
            'url': self.success_url,
            'selected': 'disiplin',
            'riwayat': 'active'
        })
        return context

    def form_valid(self, form):
        file = form.cleaned_data['file']
        try:
            processor = FingerprintProcessor(file)
            processor.run()
            messages.success(self.request, "Fingerprint berhasil diproses. Data ketepatan hadir sudah ditentukan.")
        except Exception as e:
            messages.error(self.request, f"Terjadi kesalahan saat memproses fingerprint: {str(e)}")
            return self.form_invalid(form)
        return super().form_valid(form)
    
    
# finger tanpa dokter spesialis
# class FingerprintAutoUploadView(LoginRequiredMixin, UserPassesTestMixin, FormView):
#     template_name = 'kehadirankegiatan/form.html'
#     form_class = UploadFingerprintForm
#     success_url = reverse_lazy('disiplinsdm_urls:kehadiran_list')
    
#     def test_func(self):
#         if self.request.user.is_superuser:
#             return True
#         return False

#     def handle_no_permission(self):
#         # Bisa redirect atau tampilkan pesan khusus
#         messages.error(self.request, 'Anda tidak memiliki izin untuk upload data presensi.')
#         return redirect(reverse('disiplinsdm_urls:kehadiran_list'))
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['title'] = 'Upload Fingerprint'
#         context['url'] = reverse_lazy('disiplinsdm_urls:kehadiran_list')
#         context['selected'] = 'disiplin'
#         context['riwayat'] = 'active'
#         return context

#     def form_valid(self, form):
#         file = form.cleaned_data['file']
#         wb = load_workbook(file)
#         ws = wb.active
#         scan_record = set()
#         tanggal_diproses = set()
#         def cek_status_ketepatan(tipe, jam_scan, jam_referensi):
#             if not jam_referensi:
#                 return None
#             if tipe == 'Absen Datang' and jam_scan > jam_referensi:
#                 return 'Terlambat'
#             elif tipe == 'Absen Pulang' and jam_scan < jam_referensi:
#                 return 'Cepat Pulang'
#             return 'Tepat Waktu'

#         # === 1. Proses semua data fingerprint ===
#         for row in ws.iter_rows(min_row=3):
#             waktu_scan = row[0].value
#             try:
#                 if isinstance(waktu_scan, str):
#                     waktu_scan = waktu_scan.replace('.', ':')
#                     waktu_scan = parse(waktu_scan, dayfirst=True)
#                 elif isinstance(waktu_scan, float):
#                     waktu_scan = from_excel(waktu_scan)
#                 elif not isinstance(waktu_scan, datetime):
#                     continue
#             except Exception:
#                 continue

#             nip = str(row[4].value).strip() if row[4].value else None
#             io_flag = row[10].value  # 1 = Masuk, 2 = Pulang

#             if not waktu_scan or not nip or io_flag not in [1, 2]:
#                 continue

#             tanggal_asli = waktu_scan.date()
#             tipe_kegiatan = 'Absen Datang' if io_flag == 1 else 'Absen Pulang'
#             nip_bersih = nip.replace(' ', '')
#             scan_record.add((nip_bersih, tipe_kegiatan, tanggal_asli))
#             tanggal_diproses.add(tanggal_asli)

#             try:
#                 profil = ProfilSDM.objects.get(nip=nip_bersih)
#                 pengguna = profil.user
#                 kegiatan, _ = JenisKegiatan.objects.get_or_create(jenis_kegiatan=tipe_kegiatan)

#                 # print(f'detected_record: {pengguna.full_name} ({profil.nip})' )
#                 # Ambil relasi SDM
#                 relasi_sdm = pengguna.jenissdmperinstalasi_set.filter(
#                     bulan=tanggal_asli.month, tahun=tanggal_asli.year
#                 ).last()

#                 # Buat daftar kegiatan (bulanan)
#                 daftar, _ = DaftarKegiatanPegawai.objects.get_or_create(
#                     pegawai=pengguna,
#                     kegiatan=kegiatan,
#                     bulan=tanggal_asli.month,
#                     tahun=tanggal_asli.year,
#                     defaults={
#                         'jenis_sdm': relasi_sdm.jenis_sdm if relasi_sdm else None,
#                         'unor': relasi_sdm.unor if relasi_sdm else None,
#                         'bidang': relasi_sdm.bidang if relasi_sdm else None,
#                         'sub_bidang': relasi_sdm.sub_bidang if relasi_sdm else None,
#                         'instalasi': relasi_sdm.instalasi if relasi_sdm else None,
#                     }
#                 )
                
#                 # Tangani shift malam (Absen Pulang di hari berikutnya)
#                 tanggal_scan = tanggal_asli
#                 jadwal_dinas = ApprovedJadwalDinasSDM.objects.filter(
#                     pegawai__pegawai=pengguna, tanggal=tanggal_scan
#                 ).first()

#                 if not jadwal_dinas and tipe_kegiatan == 'Absen Pulang':
#                     malam_sebelumnya = tanggal_scan - timedelta(days=1)
#                     jadwal_dinas = ApprovedJadwalDinasSDM.objects.filter(
#                         pegawai__pegawai=pengguna,
#                         tanggal=malam_sebelumnya,
#                         kategori_jadwal__kategori_jadwal='Malam'
#                     ).first()
#                     if jadwal_dinas:
#                         tanggal_scan = malam_sebelumnya

#                 if not jadwal_dinas:
#                     continue

#                 if tipe_kegiatan == 'Absen Datang':
#                     jam_referensi = getattr(jadwal_dinas.kategori_jadwal, 'waktu_datang', None)
#                 else:
#                     jam_referensi = getattr(jadwal_dinas.kategori_jadwal, 'waktu_pulang', None)

#                 status = cek_status_ketepatan(tipe_kegiatan, waktu_scan.time(), jam_referensi)

#                 kehadiran = KehadiranKegiatan.objects.get_or_create(
#                     pegawai=daftar,
#                     tanggal=make_aware(waktu_scan),
#                     defaults={
#                         'hadir': True,
#                         'status_ketepatan': status
#                     }
#                 )
                
#             except ProfilSDM.DoesNotExist:
#                 continue

#         # === 2. Tandai pegawai yang tidak fingerprint ===
#         alasan_tk, _ = AlasanTidakHadir.objects.get_or_create(alasan='Tanpa Keterangan')

#         for tanggal in tanggal_diproses:
#             jadwal_masuk = ApprovedJadwalDinasSDM.objects.filter(
#                 tanggal=tanggal,
#                 kategori_jadwal__kategori_dinas__kategori_dinas__in=['Reguler', 'Piket']
#             )
#             for jadwal in jadwal_masuk:
#                 pengguna = jadwal.pegawai.pegawai
#                 nip = pengguna.profil_user.nip if hasattr(pengguna, 'profil_user') else None
#                 if not nip:
#                     continue

#                 nip_bersih = nip.replace(' ', '')
#                 key_datang = (nip_bersih, 'Absen Datang', tanggal)
#                 key_pulang = (nip_bersih, 'Absen Pulang', tanggal)

#                 if key_datang not in scan_record and key_pulang not in scan_record:
#                     try:
#                         kegiatan, _ = JenisKegiatan.objects.get_or_create(jenis_kegiatan='Absen Datang')
#                         relasi_sdm = pengguna.jenissdmperinstalasi_set.filter(
#                             bulan=tanggal.month, tahun=tanggal.year
#                         ).first()

#                         daftar, _ = DaftarKegiatanPegawai.objects.get_or_create(
#                             pegawai=pengguna,
#                             kegiatan=kegiatan,
#                             bulan=tanggal.month,
#                             tahun=tanggal.year,
#                             defaults={
#                                 'jenis_sdm': relasi_sdm.jenis_sdm if relasi_sdm else None,
#                                 'unor': relasi_sdm.unor if relasi_sdm else None,
#                                 'bidang': relasi_sdm.bidang if relasi_sdm else None,
#                                 'sub_bidang': relasi_sdm.sub_bidang if relasi_sdm else None,
#                                 'instalasi': relasi_sdm.instalasi if relasi_sdm else None,
#                             }
#                         )
                        
#                         print(f'not_detected: {daftar.pegawai.full_name}')

#                         KehadiranKegiatan.objects.get_or_create(
#                             pegawai=daftar,
#                             tanggal=make_aware(datetime.combine(tanggal, time.min)),
#                             defaults={
#                                 'hadir': False,
#                                 'alasan': alasan_tk
#                             }
#                         )

#                     except ProfilSDM.DoesNotExist:
#                         continue

#         messages.success(self.request, "Fingerprint berhasil diproses. Data ketepatan hadir sudah ditentukan.")
#         return super().form_valid(form)

