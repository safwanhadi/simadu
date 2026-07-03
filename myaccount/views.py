from django.db.models.query import QuerySet
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView, DetailView, CreateView
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView
from django.contrib.messages.views import SuccessMessageMixin
import os
from django.http import JsonResponse
from django.db.models import Q

from urllib.parse import urlencode
from django.conf import settings
from django.http import Http404


from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models.functions import ExtractMonth, ExtractDay

# SIMADU views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ProfilSDM

from .models import ProfilSDM, Users
from .forms import ProfilForm, UserAdminChangeForm
import logging

logger = logging.getLogger(__name__)


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