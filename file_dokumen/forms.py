from django import forms
from tinymce.widgets import TinyMCE
from .models import TextSPTDiklat

class TinyMCEWidget(TinyMCE): 
	def use_required_attribute(self, *args): 
		return False

class TextSPTDiklatForm(forms.ModelForm):
    dasar_pelaksanaan = forms.CharField(widget=TinyMCEWidget(attrs={'required': False, 'cols': 30, 'rows': 10}))
    tujuan_pelaksanaan = forms.CharField(widget=TinyMCEWidget(attrs={'required': False, 'cols': 30, 'rows': 10}))
    class Meta:
        model = TextSPTDiklat
        fields = ('diklat', 'dasar_pelaksanaan', 'tujuan_pelaksanaan')

    def __init__(self, *args, **kwargs):
        self.diklat = kwargs.pop("diklat", None)
        super(TextSPTDiklatForm, self).__init__(*args, **kwargs)
        if self.diklat:
            self.fields['diklat'].initial = self.diklat
            self.fields["diklat"].widget = forms.HiddenInput()