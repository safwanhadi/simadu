import os
from urllib.parse import urlencode
from django.db.models import Count, Prefetch, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, DeleteView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from hitcount.views import HitCountDetailView

from .models import (
    InformasiSDM, KategoriInformasi, KategoriVideo, ReVideoComment,
    VideoComment, VideoYoutube,
)
from .forms import (
    InformasiSDMForm, KategoriVideoForm, ReVideoCommentForm,
    VideoCommentForm, VideoYoutubeForm,
)

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
        search_query = self.request.GET.get('q', '').strip()
        queryset = self.model.objects.filter(active=True, status='publish').select_related('kategori', 'author')
        if get_kategori:
            queryset = queryset.filter(kategori__slug=get_kategori)
        if search_query:
            queryset = queryset.filter(
                Q(judul__icontains=search_query)
                | Q(isi__icontains=search_query)
                | Q(kategori__kategori__icontains=search_query)
            )
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super(InformasiListView, self).get_context_data(**kwargs)
        get_kategori = self.request.GET.get('kat')
        search_query = self.request.GET.get('q', '').strip()
        published_information = self.model.objects.filter(active=True, status='publish')
        info_populer = published_information.order_by('-hit_count_generic__hits')[:2]
        context.update({
            'headline': published_information.filter(headline=True).order_by('-updated_at').first(),
            'info_populer': info_populer,
            'kategori': KategoriInformasi.objects.annotate(
                jumlah_informasi=Count(
                    'informasisdm',
                    filter=Q(informasisdm__active=True, informasisdm__status='publish'),
                )
            ).order_by('kategori'),
            'slug':get_kategori,
            'query': search_query,
            'jumlah_informasi': published_information.count(),
            'informasi':'active',
            'infotutorial':'active'
        })
        return context
    
    
class InformasiDetailView(LoginRequiredMixin, HitCountDetailView):
    model = InformasiSDM
    template_name = 'infotemplate/userinfotemplate/user_informasi_master.html'
    context_object_name = 'detail'
    count_hit = True

    def get_queryset(self):
        return self.model.objects.filter(active=True, status='publish').select_related('kategori', 'author')

    def get_context_data(self, **kwargs):
        context = super(InformasiDetailView, self).get_context_data(**kwargs)
        get_case = self.request.GET.get('case')
        published_information = self.model.objects.filter(active=True, status='publish')
        context.update({
            'kategori': KategoriInformasi.objects.annotate(
                jumlah_informasi=Count(
                    'informasisdm',
                    filter=Q(informasisdm__active=True, informasisdm__status='publish'),
                )
            ).order_by('kategori'),
            'slug': self.object.kategori.slug,
            'jumlah_informasi': published_information.count(),
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
    @staticmethod
    def can_manage_tutorial(user):
        return user.is_informasi_admin

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
        get_kategori = request.GET.get('kategori')
        get_video_id = request.GET.get('vid')
        search_query = request.GET.get('q', '').strip()
        published_videos = VideoYoutube.objects.filter(status='publish').select_related(
            'kategori', 'author'
        ).prefetch_related(
            Prefetch(
                'videocomment_set',
                queryset=VideoComment.objects.select_related('author').prefetch_related(
                    Prefetch(
                        'revideocomment_set',
                        queryset=ReVideoComment.objects.select_related('author').order_by('created_at'),
                    )
                ).order_by('-created_at'),
            )
        )
        data = published_videos
        if get_kategori:
            data = data.filter(kategori__slug=get_kategori)
        if search_query:
            data = data.filter(
                Q(judul_video__icontains=search_query)
                | Q(kategori__kategori__icontains=search_query)
            )
        data = data.order_by('-headline', '-updated_at')

        video = published_videos.filter(id_video=get_video_id).first() if get_video_id else None
        if video and get_kategori and video.kategori.slug != get_kategori:
            video = None
        id_video = data.filter(headline=True).first() or data.first()
        if video:
            id_video = video
            
        form = None
        get_id = kwargs.get("id")
        instance = self.get_object(get_id)
        if self.can_manage_tutorial(request.user):
            kategori_awal = KategoriVideo.objects.filter(slug=get_kategori).first()
            form = VideoYoutubeForm(
                initial={'author': request.user, 'kategori': kategori_awal},
                instance=instance,
            )
        commentform = VideoCommentForm()
        recommentform = ReVideoCommentForm()
        context={
            'form':form,
            'kategori_form': KategoriVideoForm(),
            'commentform':commentform,
            'recommentform': recommentform,
            'get_id': get_id,
            'vid':get_video_id,
            'video':id_video,
            'kategori': KategoriVideo.objects.annotate(
                jumlah_video=Count('videoyoutube', filter=Q(videoyoutube__status='publish'))
            ).order_by('kategori'),
            'data':data,
            'kategori_aktif': get_kategori,
            'query': search_query,
            'jumlah_video': published_videos.count(),
            'tutorial':'active',
            'infotutorial':'active'
        }
        return render(request, 'videotemplate/video.html', context)
    
    def post(self, request, *args, **kwargs):
        get_id = kwargs.get("id")
        get_kategori = request.GET.get('kategori')
        get_id_video = request.GET.get('vid')
        instance = self.get_object(get_id)
        url_redirect = reverse('informasi_urls:tutorial_view')
        redirect_params = {}
        if get_kategori:
            redirect_params['kategori'] = get_kategori
        if get_id_video:
            redirect_params['vid'] = get_id_video
        redirect_url = url_redirect
        if redirect_params:
            redirect_url = f'{url_redirect}?{urlencode(redirect_params)}'

        action = request.POST.get('action')
        if action == 'comment':
            video = get_object_or_404(
                VideoYoutube,
                pk=request.POST.get('video_id'),
                status='publish',
            )
            redirect_params['vid'] = video.id_video
            redirect_url = f'{url_redirect}?{urlencode(redirect_params)}'
            commentform = VideoCommentForm(data=request.POST)
            if commentform.is_valid():
                comment = commentform.save(commit=False)
                comment.video = video
                comment.author = request.user
                comment.save()
                messages.success(request, 'Komentar berhasil dikirim.')
                return redirect(f'{redirect_url}#discussion')
            messages.error(request, 'Komentar belum dapat dikirim. Pastikan komentar tidak kosong.')
            return redirect(f'{redirect_url}#discussion')

        if action == 'reply':
            parent_comment = get_object_or_404(
                VideoComment.objects.select_related('video'),
                pk=request.POST.get('comment_id'),
                video__pk=request.POST.get('video_id'),
                video__status='publish',
            )
            redirect_params['vid'] = parent_comment.video.id_video
            redirect_url = f'{url_redirect}?{urlencode(redirect_params)}'
            recommentform = ReVideoCommentForm(data=request.POST)
            if recommentform.is_valid():
                reply = recommentform.save(commit=False)
                reply.comment = parent_comment
                reply.author = request.user
                reply.save()
                messages.success(request, 'Balasan berhasil dikirim.')
                return redirect(f'{redirect_url}#comment-{parent_comment.pk}')
            messages.error(request, 'Balasan belum dapat dikirim. Pastikan balasan tidak kosong.')
            return redirect(f'{redirect_url}#comment-{parent_comment.pk}')

        if action == 'add_category':
            if not self.can_manage_tutorial(request.user):
                raise PermissionDenied
            kategori_form = KategoriVideoForm(data=request.POST)
            if kategori_form.is_valid():
                kategori = kategori_form.save()
                messages.success(request, 'Kategori tutorial berhasil ditambahkan.')
                return redirect(f'{url_redirect}?kategori={kategori.slug}#openModal')
            messages.error(request, kategori_form.errors['kategori'][0])
            return redirect(f'{url_redirect}#openCategoryModal')

        if not self.can_manage_tutorial(request.user):
            raise PermissionDenied

        form = VideoYoutubeForm(data=request.POST, instance=instance)
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
        messages.error(request, 'Mohon maaf data gagal disimpan!')
        return redirect(redirect_url)
