from django import forms

from .models import StandarInstalasi 
from jenissdm.models import ListKompetensi


class StandarInstalasiForm(forms.ModelForm):
    kompetensi_wajib = forms.ModelMultipleChoiceField(queryset=ListKompetensi.objects.all())
    kompetensi_pendukung = forms.ModelMultipleChoiceField(queryset=ListKompetensi.objects.all(), required=False)
    class Meta:
        model = StandarInstalasi
        fields = '__all__'