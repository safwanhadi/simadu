import os
from django.db.models.query import QuerySet
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, DeleteView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from hitcount.views import HitCountDetailView

from .models import InformasiSDM, VideoYoutube, KategoriVideo, KategoriInformasi
from .forms import VideoCommentForm, ReVideoCommentForm, VideoYoutubeForm, InformasiSDMForm

# Create your views here.

from datetime import datetime
import os
from django.http import FileResponse, Http404
from django.conf import settings

# pdf generator
# views.py
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render
from reportlab.pdfgen import canvas
import io

def pdf_viewer(request):
    try:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="my_pdf.pdf"'

        # Create the PDF content using ReportLab
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 100, "Hello, this is your PDF content!")
        p.showPage()
        p.save()

        # Return the PDF as a FileResponse
        buffer.seek(0)
        response.write(buffer.read())
        return response
    except FileNotFoundError:
        raise Http404("PDF not found")

def main(request):
    return render(request, 'template.html')


def pdf_view(request, id):
    # file_path = os.path.join(settings.MEDIA_ROOT, filename)
    try:
        data = InformasiSDM.objects.get(id=id)
        file_path = data.pdf_file.path
        if os.path.exists(file_path):
            # return FileResponse(open(file_path, 'rb'), content_type='application/pdf')
            with open(file_path, 'rb') as pdf:
                response = HttpResponse(pdf.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'inline; filename={data.pdf_file}'
                return response
        else:
            raise Http404("File not found")
    except InformasiSDM.DoesNotExist:
        return None

def pdf_list(request):
    data = InformasiSDM.objects.all()
    context={
        'data':data
    }
    return render(request, 'pdf_list.html', context)


class InformasiListView(LoginRequiredMixin, ListView):
    model = InformasiSDM
    template_name = 'infotemplate/userinfotemplate/user_informasi_master.html'
    context_object_name = 'object_list'
    paginate_by = 6

    def get_queryset(self):
        get_kategori = self.request.GET.get('kat')
        if get_kategori:
            queryset = self.model.objects.filter(kategori__slug=get_kategori, active=True, status='publish').order_by('-id')
        else:
            queryset = self.model.objects.filter(active=True, status='publish').order_by('-id')
        return queryset

    def get_context_data(self, **kwargs):
        context = super(InformasiListView, self).get_context_data(**kwargs)
        get_kategori = self.request.GET.get('kat')
        info_populer = self.model.objects.filter(active=True, status='publish').order_by('-hit_count_generic__hits')[:2]
        context.update({
            'headline': self.model.objects.filter(headline=True).first(),
            'info_populer': info_populer,
            'kategori':KategoriInformasi.objects.all(),
            'slug':get_kategori,
            'informasi':'active',
            'infotutorial':'active'
        })
        return context
    
    
class InformasiDetailView(LoginRequiredMixin, HitCountDetailView):
    model = InformasiSDM
    template_name = 'infotemplate/userinfotemplate/user_informasi_master.html'
    context_object_name = 'detail'
    count_hit = True

    def get_context_data(self, **kwargs):
        context = super(InformasiDetailView, self).get_context_data(**kwargs)
        get_case = self.request.GET.get('case')
        context.update({
            'kategori':KategoriInformasi.objects.all(),
            'case': get_case,
            'informasi':'active',
            'infotutorial':'active'
        })
        return context
    

class InformasiSDMView(LoginRequiredMixin, View):
    def get_object(self, id):
        try:
            data = InformasiSDM.objects.get(id=id)
            return data
        except InformasiSDM.DoesNotExist:
            return None
        
    def get(self, request, *args, **kwargs):
        data_id = kwargs.get('id')
        detail  = self.get_object(data_id)
        get_form_view = request.GET.get('f')
        form_view = 'none'
        data_view = 'block'
        data = InformasiSDM.objects.all()
        headline = data.filter(headline=True).first()
        newest = data.order_by('-id')[:2]
        form = None
        if request.user.is_superuser:
            if bool(get_form_view):
                form_view='block'
                data_view='none'
            form = InformasiSDMForm()
            if data_id:
                form = InformasiSDMForm(instance=detail)
        context={
            'data_view':data_view,
            'form_view':form_view,
            'data_id':data_id,
            'newest':newest,
            'form':form,
            'headline':headline,
            'data': data,
            'detail': detail,
            'informasi':'active',
            'infotutorial':'active'
        }
        return render(request, 'infotemplate/admininfotemplate/informasi_master.html', context)

    def post(self, request, **kwargs):
        data_id = kwargs.get('id')
        detail = self.get_object(data_id)
        instance = self.get_object(data_id)
        form = InformasiSDMForm(data=request.POST, files=request.FILES, instance=instance)
        if form.is_valid():
            data = form.save(commit=False)
            if data.headline:
                InformasiSDM.objects.update(headline=False)
                data.active = True
                data.status = 'publish'
            if detail is not None and detail.gambar and data.gambar != detail.gambar and os.path.exists(detail.gambar.path):
                os.remove(detail.gambar.path)
            data.save()
            messages.success(request, 'Data berhasil disimpan!')
            return redirect(reverse('informasi_urls:add_informasi_view'))
        messages.error(request, 'Data gagal disimpan!')
        return redirect(reverse('informasi_urls:add_informasi_view'))
    

class DeleteInformasiView(DeleteView):
    model = InformasiSDM
    success_url = reverse_lazy('informasi_urls:add_informasi_view')
    template_name = 'infotemplate/admininfotemplate/informasi_master.html'

    def get_context_data(self, **kwargs):
        context = super(DeleteInformasiView, self).get_context_data(**kwargs)
        context.update({
            'data':InformasiSDM.objects.all(),
            'data_view':'block',
            'form_view':'none',
            'informasi':'active',
            'infotutorial':'active'
        })
        return context


class VideoTutorialView(LoginRequiredMixin, View):
    def get_object(self, id):
        try:
            data = VideoYoutube.objects.get(id=id)
            return data
        except VideoYoutube.DoesNotExist:
            return None
        
    def get_video(self, video_id):
        try:
            data = VideoYoutube.objects.get(id_video=video_id)
            return data
        except VideoYoutube.DoesNotExist:
            return None
        
    def get(self, request, **kwargs):
        print('get video tutorial')
        get_kategori = request.GET.get('kategori')
        get_video_id = request.GET.get('vid')
        video = self.get_video(get_video_id)
        kategori = KategoriVideo.objects.all()
        data = VideoYoutube.objects.all()
        if get_kategori is not None:
            data = VideoYoutube.objects.filter(kategori__slug=get_kategori)
        headline = data.filter(headline=True).order_by('updated_at').last()
        id_video = headline
        print('id_video', id_video)
        if video:
            id_video = video
            
        initial_comment = {
            'video':id_video,
            'author':request.user
        }
        form = None
        print('get id video', get_video_id)
        get_id = kwargs.get("id")
        instance = self.get_object(get_id)
        if request.user.is_superuser:
            form = VideoYoutubeForm(initial={'author':request.user}, instance=instance)
        commentform = VideoCommentForm(initial=initial_comment)
        recommentform = ReVideoCommentForm()
        context={
            'form':form,
            'commentform':commentform,
            'recommentform': recommentform,
            'get_id': get_id,
            'vid':get_video_id,
            'video':id_video,
            'kategori':kategori,
            'data':data,
            'tutorial':'active',
            'infotutorial':'active'
        }
        return render(request, 'videotemplate/video.html', context)
    
    def post(self, request, *args, **kwargs):
        get_id = kwargs.get("id")
        get_kategori = request.GET.get('kategori')
        get_id_video = request.GET.get('vid')
        instance = self.get_object(get_id)
        commentform = VideoCommentForm(data=request.POST)
        form = VideoYoutubeForm(data=request.POST, instance=instance)
        url_redirect = reverse('informasi_urls:tutorial_view')
        if form.is_valid():
            dataform = form.save(commit=False)
            dataform.headline = form.cleaned_data.get('headline')
            dataform.kategori = form.cleaned_data.get('kategori')
            dataform.id_video = form.cleaned_data.get('id_video')
            if dataform.headline:
                video = VideoYoutube.objects.filter(kategori=dataform.kategori)
                video.update(headline=False)
            dataform.save()
            if get_kategori:
                return redirect(f'{url_redirect}?kategori={get_kategori}&vid={dataform.id_video}#close')
            else:
                return redirect(f'{url_redirect}?vid={dataform.id_video}#close')
        if commentform.is_valid():
            commentform.save()
            messages.success(request, 'Data berhasil diinput!')
            if get_kategori:
                return redirect(f'{url_redirect}?kategori={get_kategori}&vid={get_id_video}')
            else:
                return redirect(f'{url_redirect}?vid={get_id_video}')
        messages.error(request, 'Mohon maaf data gagal disimpan!')
        return redirect(f'{url_redirect}?vid={get_id_video}')