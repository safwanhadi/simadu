import os
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import LaporanMasalah, Saran
from .forms import LaporanForm, SaranForm

# Create your views here.

class LaporanView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        data = LaporanMasalah.objects.all()
        form = LaporanForm(request=request)
        form_view = 'none'
        data_view = 'block'
        if not request.user.is_superuser:
            initial = {'pegawai':request.user, 'status':'Laporan'}
            data = LaporanMasalah.objects.filter(pegawai=request.user)
            form = LaporanForm(request=request, initial=initial)
        context={
            'form':form,
            'data': data,
            'lapor':'active',
            'selected':'error',
            'title_page':'Laporan error',
            'form_view':form_view,
            'data_view':data_view
        }
        return render(request, '1_laporan/lapor_master.html', context)
    
    def post(self, request):
        form = LaporanForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data berhasil disimpan!')
            return redirect(reverse('laporan_urls:laporan_view'))
        messages.error(request, 'Maaf data gagal disimpan!')
        return redirect(reverse('laporan_urls:laporan_view'))
    
    
class UpdateLaporanView(LoginRequiredMixin, View):
    def get_object(self, id):
        try:
            data = LaporanMasalah.objects.get(id=id)
            return data
        except LaporanMasalah.DoesNotExist:
            return None
        
    def get(self, request, *args, **kwargs):
        data_id = kwargs.get('id')
        instance = self.get_object(data_id)
        form = LaporanForm(instance=instance, request=request)
        if instance.status == 'Laporan' or instance.status == 'Tindaklanjut':
            form_view = 'block'
            data_view = 'none'
        else:
            form_view = 'none'
            data_view = 'block'
        context = {
            'update_form':True,
            'detail':instance,
            'form':form,
            'lapor':'active',
            'selected':'error',
            'title_page':'Laporan error',
            'form_view':form_view,
            'data_view':data_view
        }
        return render(request, '1_laporan/lapor_master.html', context)
    
    def post(self, request, *args, **kwargs):
        data_id = kwargs.get('id')
        existing_obj = self.get_object(data_id)
        instance = self.get_object(data_id)
        form = LaporanForm(request=request, data=request.POST, files=request.FILES, instance=instance)
        if form.is_valid():
            data_lapor = form.save(commit=False)
            if existing_obj.gambar and existing_obj.gambar != data_lapor.gambar and os.path.exists(existing_obj.gambar.path):
                os.remove(existing_obj.gambar.path)
            data_lapor.save()
            messages.success(request, 'Data berhasil diupdate!')
            return redirect(reverse('laporan_urls:laporan_view'))
        messages.error(request, 'Maaf data gagal diupdate!')
        return redirect(reverse('laporan_urls:laporan_update_view', kwargs={'id':data_id}))
    

class SaranView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        data = Saran.objects.all()
        form = SaranForm(request=request)
        form_view = 'none'
        data_view = 'block'
        if not request.user.is_superuser:
            initial = {'pegawai':request.user}
            data = Saran.objects.filter(pegawai=request.user)
            form = SaranForm(initial=initial, request=request)
        context={
            'form':form,
            'data': data,
            'lapor':'active',
            'selected':'saran',
            'form_view':form_view,
            'data_view':data_view
        }
        return render(request, '2_saran/saran_master.html', context)
    
    def post(self, request, *args, **kwargs):
        form = SaranForm(data=request.POST, files=request.FILES, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data berhasil disimpan!')
            return redirect(reverse('laporan_urls:saran_view'))
        messages.error(request, 'Maaf data gagal disimpan!')
        return redirect(reverse('laporan_urls:saran_view'))
    
    
class UpdateSaranView(LoginRequiredMixin, View):
    def get_object(self, id):
        try:
            data = Saran.objects.get(id=id)
            return data
        except Saran.DoesNotExist:
            return None
        
    def get(self, request, *args, **kwargs):
        data_id = kwargs.get('id')
        instance = self.get_object(data_id)
        form = SaranForm(instance=instance, request=request)
        context = {
            'update_form':True,
            'form':form,
            'lapor':'active',
            'selected':'saran',
            'form_view':'block',
            'data_view':'none'
        }
        return render(request, '2_saran/saran_master.html', context)
    
    def post(self, request, *args, **kwargs):
        data_id = kwargs.get('id')
        instance = self.get_object(data_id)
        form = SaranForm(data=request.POST, files=request.FILES, instance=instance, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data berhasil diupdate!')
            return redirect(reverse('saran_urls:saran_view'))
        messages.error(request, 'Maaf data gagal diupdate!')
        return redirect(reverse('saran_urls:saran_update_view', kwargs={'id':data_id}))
