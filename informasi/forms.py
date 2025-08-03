from django import forms
from tinymce.widgets import TinyMCE

from .models import VideoComment, ReVideoComment, VideoYoutube, InformasiSDM


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


class VideoCommentForm(forms.ModelForm):
    class Meta:
        model = VideoComment
        fields = ('video', 'author', 'comment')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(VideoCommentForm, self).__init__(*args, **kwargs)
        self.fields['video'].widget = forms.HiddenInput()
        self.fields['author'].widget = forms.HiddenInput()
        self.fields['comment'].label = ''
        self.fields['comment'].widget.attrs.update({'cols': 80, 'rows': 3})


class ReVideoCommentForm(forms.ModelForm):
    class Meta:
        model = ReVideoComment
        fields = ('comment', 'author', 'recomment')

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop("request", None)
        super(ReVideoCommentForm, self).__init__(*args, **kwargs)
        self.fields['comment'].widget = forms.HiddenInput()
        self.fields['author'].widget = forms.HiddenInput()
        self.fields['recomment'].label = ''