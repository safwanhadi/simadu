from django import forms
from .models import LaporanMasalah, Saran

class LaporanForm(forms.ModelForm):
    class Meta:
        model = LaporanMasalah
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop('request', None)
        super(LaporanForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['status'].widget = forms.HiddenInput()
            self.fields['keterangan'].widget = forms.HiddenInput()


class SaranForm(forms.ModelForm):
    class Meta:
        model = Saran
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request=kwargs.pop('request', None)
        super(SaranForm, self).__init__(*args, **kwargs)
        if self.request and not self.request.user.is_superuser:
            self.fields['pegawai'].widget = forms.HiddenInput()
            self.fields['tanggapan'].widget = forms.HiddenInput()