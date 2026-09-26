from django import forms
from tinymce.widgets import TinyMCE

from .models import KategoriVideo, VideoComment, ReVideoComment, VideoYoutube, InformasiSDM


class TinyMCEWidget(TinyMCE): 
	def use_required_attribute(self, *args): 
		return False


class InformasiSDMForm(forms.ModelForm): 
    judul = forms.CharField(max_length=250)
    isi = forms.CharField(widget=TinyMCEWidget(attrs={'required': False, 'cols': 30, 'rows': 10}))
    class Meta: 
        model = InformasiSDM
        fields = ('kategori', 'author', 'judul', 'isi', 'gambar', 'status', 'headline', 'active', 'pdf_file')
         


class VideoYoutubeForm(forms.ModelForm):
    class Meta:
        model = VideoYoutube
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(VideoYoutubeForm, self).__init__(*args, **kwargs)
        self.fields['author'].widget = forms.HiddenInput()
        self.fields['slug'].widget = forms.HiddenInput()


class KategoriVideoForm(forms.ModelForm):
    class Meta:
        model = KategoriVideo
        fields = ('kategori',)
        widgets = {
            'kategori': forms.TextInput(attrs={
                'placeholder': 'Contoh: Penggunaan Mandacare',
                'autocomplete': 'off',
            }),
        }

    def clean_kategori(self):
        kategori = self.cleaned_data['kategori'].strip()
        if KategoriVideo.objects.filter(kategori__iexact=kategori).exists():
            raise forms.ValidationError('Kategori tutorial tersebut sudah tersedia.')
        return kategori


class VideoCommentForm(forms.ModelForm):
    class Meta:
        model = VideoComment
        fields = ('comment',)

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(VideoCommentForm, self).__init__(*args, **kwargs)
        self.fields['comment'].label = ''
        self.fields['comment'].required = True
        self.fields['comment'].widget.attrs.update({
            'cols': 80,
            'rows': 3,
            'placeholder': 'Tulis pertanyaan atau tanggapan tentang tutorial ini...',
        })


class ReVideoCommentForm(forms.ModelForm):
    class Meta:
        model = ReVideoComment
        fields = ('recomment',)

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(ReVideoCommentForm, self).__init__(*args, **kwargs)
        self.fields['recomment'].label = ''
        self.fields['recomment'].required = True
        self.fields['recomment'].widget.attrs.update({
            'rows': 2,
            'placeholder': 'Tulis balasan Anda...',
        })
