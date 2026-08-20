from django.test import TestCase

from .forms import ProfilForm
from .models import ProfilSDM, Users


class ProfilFormNameTests(TestCase):
    def test_profil_tetap_dapat_disimpan_saat_file_foto_hilang(self):
        user = Users.objects.create_user(
            email='foto-hilang-profil@example.com',
            first_name='Foto',
            last_name='Hilang',
        )
        profil = ProfilSDM.objects.create(
            user=user,
            no_hp='08123456781',
            email_pribadi=user.email,
        )
        profil.foto.name = 'profil/foto/file-yang-sudah-hilang.jpg'

        profil.alamat = 'Alamat tetap tersimpan'
        profil.save()

        profil.refresh_from_db()
        self.assertEqual(profil.alamat, 'Alamat tetap tersimpan')

    def test_form_valid_saat_referensi_foto_lama_sudah_hilang(self):
        user = Users.objects.create_user(
            email='validasi-foto-hilang@example.com',
            first_name='Validasi',
            last_name='Foto Hilang',
        )
        profil = ProfilSDM.objects.create(
            user=user,
            no_hp='08123456782',
            email_pribadi=user.email,
        )
        profil.foto.name = 'profil/foto/file-validasi-yang-hilang.jpg'
        profil.save(update_fields=['foto'])
        form = ProfilForm(
            data={
                'first_name': user.first_name,
                'last_name': user.last_name,
                'no_hp': profil.no_hp,
                'email_pribadi': profil.email_pribadi,
                'agama': '',
            },
            instance=profil,
            user=user,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_field_nama_di_atas_dan_pilihan_user_disembunyikan(self):
        user = Users.objects.create_user(
            email='urutan-form-profil@example.com',
            first_name='Urutan',
            last_name='Form',
        )
        profil = ProfilSDM.objects.create(
            user=user,
            no_hp='08123456780',
            email_pribadi=user.email,
        )

        form = ProfilForm(instance=profil, user=user)

        self.assertEqual(list(form.fields)[:2], ['first_name', 'last_name'])
        self.assertNotIn('user', form.fields)

    def test_edit_profil_memperbarui_nama_akun(self):
        user = Users.objects.create_user(
            email='edit-nama-profil@example.com',
            first_name='Nama',
            last_name='Lama',
        )
        profil = ProfilSDM.objects.create(
            user=user,
            no_hp='08123456789',
            email_pribadi='edit-nama-profil@example.com',
        )
        form = ProfilForm(
            data={
                'user': user.pk,
                'first_name': 'Nama Depan Baru',
                'last_name': 'Nama Belakang Baru',
                'no_hp': profil.no_hp,
                'email_pribadi': profil.email_pribadi,
                'agama': '',
            },
            instance=profil,
            user=user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Nama Depan Baru')
        self.assertEqual(user.last_name, 'Nama Belakang Baru')
