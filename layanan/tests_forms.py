from django import forms
from django.test import TestCase

from myaccount.models import Users

from .forms import LayananNaikPangkatForm


class LayananNaikPangkatFormTests(TestCase):
    def test_form_pegawai_dapat_diinisialisasi_untuk_user_biasa(self):
        user = Users.objects.create_user(
            email='form-pangkat@example.com',
            first_name='Form',
            last_name='Pangkat',
            password=None,
        )

        form = LayananNaikPangkatForm(user=user)

        self.assertEqual(
            list(form.fields['pegawai'].queryset.values_list('pk', flat=True)),
            [user.pk],
        )
        self.assertEqual(form.fields['pegawai'].initial, user)
        self.assertIsInstance(form.fields['pegawai'].widget, forms.HiddenInput)
