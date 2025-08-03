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

from .models import ProfilSDM, Users
from .forms import ProfilForm, UserAdminChangeForm


class SimaduLoginView(LoginView):
    template_name = 'login.html'

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name)
        dashboard_url = reverse('dashboard_urls:dashboard_view')
        dashboard_absensi_url = reverse('dashboard_urls:dashboard_absensi_view')
        # riwayat_url = reverse('riwayat_urls:riwayat_view')
        if self.request.user.is_superuser:
            return redirect_to if redirect_to else dashboard_url
        else:
            return redirect_to if redirect_to else dashboard_absensi_url
    

def logout_view(request):
    logout(request)
    return redirect(reverse('myaccount_urls:login_view'))


class ChangePassword(PasswordChangeView):
    template_name = 'change_password.html'       
    
    def get_success_url(self) -> str:
        return reverse('myaccount_urls:ganti_password_done_view')

class ChangePasswordDone(PasswordChangeDoneView):
    template_name = 'change_password_done.html'
    title = "Password berhasil diganti!"


class ProfilView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
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
    
