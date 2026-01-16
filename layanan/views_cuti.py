from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, 
    DeleteView, TemplateView, FormView
)
from django.views.generic.edit import FormMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, Http404
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User

from dokumen.models import RiwayatCuti
from .models import LayananCuti
from .forms_cuti import (
    LayananCutiForm, PersetujuanCutiForm, CutiFilterForm, CutiTundaForm
)
from .services import CheckCuti, CutiApprovalService


class DashboardCutiView(LoginRequiredMixin, TemplateView):
    """Dashboard untuk menampilkan overview cuti"""
    template_name = 'cuti/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        check_cuti = CheckCuti()
        user = self.request.user

        # Get user's leave info
        context['sisa_cuti'] = check_cuti.cek_sisa_cuti(user)
        context['total_cuti_proses'] = check_cuti.cek_total_cuti_termasuk_sedang_proses(user)
        
        # Get pending approvals for this user
        approval_service = CutiApprovalService()
        pending_approvals = []
        
        # Get all layanan cuti that need this user's approval
        all_cuti = LayananCuti.objects.filter(status__in=['Diajukan', 'Disetujui SubBidang', 'Disetujui Bidang'])
        
        for cuti in all_cuti:
            if approval_service.can_approve(user, cuti):
                pending_approvals.append(cuti)
        
        context['pending_approvals'] = pending_approvals[:5]  # Limit to 5
        context['pending_approvals_count'] = len(pending_approvals)
        
        # Get user's recent leave requests
        context['recent_cuti'] = LayananCuti.objects.filter(
            pegawai=user
        ).order_by('-created_at')[:5]
        
        return context


class LayananCutiListView(LoginRequiredMixin, ListView):
    """List view untuk daftar pengajuan cuti"""
    model = LayananCuti
    template_name = 'cuti/layanan_cuti_list.html'
    context_object_name = 'cuti_list'
    paginate_by = 10

    def get_queryset(self):
        queryset = LayananCuti.objects.all()
        
        # Filter based on user role
        if not self.request.user.is_superuser:
            # Regular users can only see their own requests
            queryset = queryset.filter(pegawai=self.request.user)
        
        # Apply filters
        form = CutiFilterForm(self.request.GET)
        if form.is_valid():
            status = form.cleaned_data.get('status')
            jenis_cuti = form.cleaned_data.get('jenis_cuti')
            tanggal_mulai = form.cleaned_data.get('tanggal_mulai')
            tanggal_akhir = form.cleaned_data.get('tanggal_akhir')
            pegawai = form.cleaned_data.get('pegawai')

            if status:
                queryset = queryset.filter(status=status)
            if jenis_cuti:
                queryset = queryset.filter(jenis_cuti=jenis_cuti)
            if tanggal_mulai:
                queryset = queryset.filter(tgl_mulai__gte=tanggal_mulai)
            if tanggal_akhir:
                queryset = queryset.filter(tgl_akhir__lte=tanggal_akhir)
            if pegawai:
                queryset = queryset.filter(pegawai=pegawai)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = CutiFilterForm(self.request.GET)
        context['check_cuti'] = CheckCuti()
        return context


class LayananCutiDetailView(LoginRequiredMixin, DetailView):
    """Detail view untuk pengajuan cuti"""
    model = LayananCuti
    template_name = 'cuti/layanan_cuti_detail.html'
    context_object_name = 'cuti'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['persetujuan_list'] = self.object.persetujuan.all().order_by('created_at')
        
        # Check if current user can approve
        approval_service = CutiApprovalService()
        context['can_approve'] = approval_service.can_approve(self.request.user, self.object)
        context['next_approval_level'] = approval_service.get_next_approval_level(self.object)
        
        return context


class LayananCutiCreateView(LoginRequiredMixin, CreateView):
    """Create view untuk pengajuan cuti baru"""
    model = LayananCuti
    form_class = LayananCutiForm
    template_name = 'cuti/layanan_cuti_form.html'
    success_url = reverse_lazy('cuti:layanan_cuti_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.pegawai = self.request.user
        messages.success(self.request, 'Pengajuan cuti berhasil dibuat!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        check_cuti = CheckCuti()
        context['sisa_cuti'] = check_cuti.cek_sisa_cuti(self.request.user)
        return context


class CutiTundaCreateView(LoginRequiredMixin, CreateView):
    """Create view khusus untuk cuti tertunda"""
    model = LayananCuti
    form_class = CutiTundaForm
    template_name = 'cuti/cuti_tunda_form.html'
    success_url = reverse_lazy('cuti:layanan_cuti_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        check_cuti = CheckCuti()
        if not check_cuti.can_manage_cuti_tunda(request.user):
            messages.error(request, 'Anda tidak memiliki wewenang untuk mengajukan cuti tertunda')
            return redirect('cuti:layanan_cuti_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.pegawai = self.request.user
        messages.success(self.request, 'Pengajuan cuti tertunda berhasil dibuat!')
        return super().form_valid(form)


class PersetujuanCutiView(LoginRequiredMixin, FormMixin, DetailView):
    """View untuk persetujuan cuti"""
    model = LayananCuti
    template_name = 'cuti/persetujuan_cuti.html'
    context_object_name = 'cuti'
    form_class = PersetujuanCutiForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['persetujuan_list'] = self.object.persetujuan.all().order_by('created_at')
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['layanan_cuti'] = self.object
        return kwargs

    def form_valid(self, form):
        approval_service = CutiApprovalService()
        
        try:
            status = form.cleaned_data['status']
            catatan = form.cleaned_data['catatan']
            
            approval = approval_service.approve_cuti(
                layanan_cuti=self.object,
                approver=self.request.user,
                status=status,
                catatan=catatan
            )
            
            if status == 'Approved':
                messages.success(self.request, f'Cuti berhasil disetujui pada level {approval.level_approval}')
            else:
                messages.warning(self.request, 'Cuti ditolak')
                
            return redirect('cuti:persetujuan_list')
            
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


class PersetujuanListView(LoginRequiredMixin, ListView):
    """List view untuk daftar persetujuan yang pending"""
    model = LayananCuti
    template_name = 'cuti/persetujuan_list.html'
    context_object_name = 'pending_cuti_list'
    paginate_by = 10

    def get_queryset(self):
        approval_service = CutiApprovalService()
        pending_cuti = []
        
        # Get all layanan cuti that need this user's approval
        all_cuti = LayananCuti.objects.filter(
            status__in=['Diajukan', 'Disetujui SubBidang', 'Disetujui Bidang']
        ).order_by('-created_at')
        
        for cuti in all_cuti:
            if approval_service.can_approve(self.request.user, cuti):
                pending_cuti.append(cuti)
        
        return pending_cuti

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        approval_service = CutiApprovalService()
        
        # Add approval level info
        for cuti in context['pending_cuti_list']:
            cuti.next_level = approval_service.get_next_approval_level(cuti)
        
        return context


class RiwayatCutiListView(LoginRequiredMixin, ListView):
    """List view untuk riwayat cuti"""
    model = RiwayatCuti
    template_name = 'cuti/riwayat_cuti_list.html'
    context_object_name = 'riwayat_list'
    paginate_by = 10

    def get_queryset(self):
        queryset = RiwayatCuti.objects.all()
        
        # Regular users can only see their own history
        if not self.request.user.is_superuser:
            queryset = queryset.filter(pegawai=self.request.user)
        
        return queryset.order_by('-created_at')


class LayananCutiUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update view untuk mengedit pengajuan cuti (hanya yang belum diproses)"""
    model = LayananCuti
    form_class = LayananCutiForm
    template_name = 'cuti/layanan_cuti_form.html'

    def test_func(self):
        cuti = self.get_object()
        return (cuti.pegawai == self.request.user and 
                cuti.status == 'Diajukan')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Pengajuan cuti berhasil diperbarui!')
        return super().form_valid(form)


class LayananCutiDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete view untuk membatalkan pengajuan cuti"""
    model = LayananCuti
    template_name = 'cuti/layanan_cuti_confirm_delete.html'
    success_url = reverse_lazy('cuti:layanan_cuti_list')

    def test_func(self):
        cuti = self.get_object()
        return (cuti.pegawai == self.request.user and 
                cuti.status in ['Diajukan', 'Ditolak'])

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Pengajuan cuti berhasil dibatalkan!')
        return super().delete(request, *args, **kwargs)


class CutiStatsView(LoginRequiredMixin, TemplateView):
    """View untuk statistik cuti"""
    template_name = 'cuti/cuti_stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        check_cuti = CheckCuti()
        
        # Get statistics
        total_cuti = LayananCuti.objects.count()
        pending_cuti = LayananCuti.objects.filter(status='Diajukan').count()
        approved_cuti = LayananCuti.objects.filter(
            status__in=['Disetujui SubBidang', 'Disetujui Bidang', 'Disetujui Unor']
        ).count()
        rejected_cuti = LayananCuti.objects.filter(status='Ditolak').count()
        
        context.update({
            'total_cuti': total_cuti,
            'pending_cuti': pending_cuti,
            'approved_cuti': approved_cuti,
            'rejected_cuti': rejected_cuti,
            'sisa_cuti': check_cuti.cek_sisa_cuti(self.request.user),
        })
        
        return context


# API Views for AJAX
class GetSisaCutiAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint untuk mendapatkan sisa cuti via AJAX"""
    
    def get(self, request, *args, **kwargs):
        check_cuti = CheckCuti()
        sisa_cuti = check_cuti.cek_sisa_cuti(request.user)
        
        return JsonResponse({
            'sisa_cuti': sisa_cuti
        })


class ValidateCutiDateAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint untuk validasi tanggal cuti via AJAX"""
    
    def get(self, request, *args, **kwargs):
        tgl_mulai = request.GET.get('tgl_mulai')
        tgl_akhir = request.GET.get('tgl_akhir')
        jenis_cuti = request.GET.get('jenis_cuti')
        
        if not tgl_mulai or not tgl_akhir:
            return JsonResponse({'valid': False, 'message': 'Tanggal harus diisi'})
        
        try:
            from datetime import datetime
            tgl_mulai = datetime.strptime(tgl_mulai, '%Y-%m-%d').date()
            tgl_akhir = datetime.strptime(tgl_akhir, '%Y-%m-%d').date()
            
            if tgl_mulai > tgl_akhir:
                return JsonResponse({'valid': False, 'message': 'Tanggal mulai tidak boleh lebih besar dari tanggal akhir'})
            
            if jenis_cuti == 'Cuti Tahunan':
                check_cuti = CheckCuti()
                sisa_cuti = check_cuti.cek_sisa_cuti(request.user)
                lama_cuti = (tgl_akhir - tgl_mulai).days + 1
                
                if lama_cuti > sisa_cuti:
                    return JsonResponse({
                        'valid': False, 
                        'message': f'Sisa cuti tidak mencukupi. Sisa: {sisa_cuti} hari, diajukan: {lama_cuti} hari'
                    })
            
            return JsonResponse({'valid': True, 'message': 'Tanggal valid'})
            
        except ValueError:
            return JsonResponse({'valid': False, 'message': 'Format tanggal tidak valid'})