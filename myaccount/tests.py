from django.contrib.auth.models import Group
from django.contrib.auth import authenticate
from django.test import TestCase, override_settings
from django.template.loader import render_to_string
from django.urls import reverse
from urllib.parse import parse_qs, urlparse

from allauth.socialaccount.models import SocialApp

from .adapters import RestrictToExistingUserAdapter
from .models import AccountRegistration, ProfilSDM, Users
from .roles import ADMIN_AKUN, ADMIN_DOKUMEN


class AccountManagementTests(TestCase):
    password = 'Password-Awal-123!'

    @classmethod
    def setUpTestData(cls):
        cls.admin = Users.objects.create_user(
            email='admin-akun@example.com',
            first_name='Admin',
            last_name='Akun',
            password=cls.password,
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_AKUN)
        cls.admin.groups.add(group)
        cls.user = Users.objects.create_user(
            email='pegawai@example.com',
            first_name='Pegawai',
            last_name='Uji',
            password=cls.password,
        )
        cls.regular_user = Users.objects.create_user(
            email='bukan-admin@example.com',
            first_name='Bukan',
            last_name='Admin',
            password=cls.password,
        )
        cls.superuser = Users.objects.create_superuser(
            email='root@example.com',
            first_name='Root',
            last_name='User',
            password=cls.password,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_admin_akun_dapat_membuka_daftar(self):
        response = self.client.get(reverse('myaccount_urls:account_management_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.email)
        self.assertNotContains(response, self.superuser.email)

    def test_user_biasa_ditolak(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse('myaccount_urls:account_management_list'))

        self.assertEqual(response.status_code, 403)

    def test_admin_dapat_reset_password(self):
        new_password = 'Password-Baru-456!'

        response = self.client.post(
            reverse('myaccount_urls:account_reset_password', args=[self.user.pk]),
            {'new_password1': new_password, 'new_password2': new_password},
        )

        self.assertRedirects(response, reverse('myaccount_urls:account_management_list'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_admin_dapat_toggle_status_aktif_dan_staff(self):
        self.client.post(
            reverse('myaccount_urls:account_toggle_active', args=[self.user.pk])
        )
        self.client.post(
            reverse('myaccount_urls:account_toggle_staff', args=[self.user.pk])
        )

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(self.user.is_staff)

    def test_admin_akun_dapat_memberikan_peran_admin_dokumen(self):
        response = self.client.post(
            reverse(
                'myaccount_urls:account_toggle_document_admin',
                args=[self.user.pk],
            )
        )

        self.assertRedirects(response, reverse('myaccount_urls:account_management_list'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.groups.filter(name=ADMIN_DOKUMEN).exists())

    def test_admin_tidak_dapat_mengubah_status_akun_sendiri(self):
        self.client.post(
            reverse('myaccount_urls:account_toggle_active', args=[self.admin.pk])
        )
        self.client.post(
            reverse('myaccount_urls:account_toggle_staff', args=[self.admin.pk])
        )

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertFalse(self.admin.is_staff)

    def test_superuser_tidak_dapat_dimutasi_dari_menu(self):
        response = self.client.post(
            reverse('myaccount_urls:account_toggle_active', args=[self.superuser.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)


class EmployeeRegistrationTests(TestCase):
    password = 'Password-Registrasi-123!'

    @classmethod
    def setUpTestData(cls):
        cls.admin = Users.objects.create_user(
            email='admin-verifikasi@example.com',
            first_name='Admin',
            last_name='Verifikasi',
            password='Password-Admin-123!',
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_AKUN)
        cls.admin.groups.add(group)

    def registration_data(self, **overrides):
        data = {
            'first_name': 'Pegawai',
            'last_name': 'Baru',
            'email': 'pegawai-baru@example.com',
            'nip': '1987.6543 210',
            'no_hp': '+62 812-3456-7890',
            'password1': self.password,
            'password2': self.password,
            'agree_privacy': True,
        }
        data.update(overrides)
        return data

    def test_halaman_registrasi_dapat_diakses_tanpa_login(self):
        response = self.client.get(reverse('myaccount_urls:account_registration'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registrasi Akun Pegawai')

    def test_registrasi_membuat_akun_nonaktif_dan_profil(self):
        response = self.client.post(
            reverse('myaccount_urls:account_registration'),
            self.registration_data(),
        )

        self.assertRedirects(
            response,
            reverse('myaccount_urls:account_registration_success'),
        )
        user = Users.objects.get(email='pegawai-baru@example.com')
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password(self.password))
        self.assertEqual(user.profil_user.nip, '19876543210')
        self.assertEqual(user.profil_user.no_hp, '081234567890')
        self.assertEqual(
            user.registration_request.status,
            AccountRegistration.PENDING,
        )

    def test_akun_baru_tidak_bisa_login_sebelum_diverifikasi(self):
        self.client.post(
            reverse('myaccount_urls:account_registration'),
            self.registration_data(),
        )

        user = authenticate(
            username='pegawai-baru@example.com',
            password=self.password,
        )

        self.assertIsNone(user)

    def test_admin_dapat_verifikasi_lalu_akun_bisa_login(self):
        self.client.post(
            reverse('myaccount_urls:account_registration'),
            self.registration_data(),
        )
        user = Users.objects.get(email='pegawai-baru@example.com')
        registration = user.registration_request
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                'myaccount_urls:account_registration_approve',
                args=[registration.pk],
            ),
        )

        self.assertRedirects(
            response,
            reverse('myaccount_urls:account_registration_review_list'),
        )
        user.refresh_from_db()
        registration.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(registration.status, AccountRegistration.APPROVED)
        self.assertEqual(registration.reviewed_by, self.admin)

        authenticated_user = authenticate(
            username=user.email,
            password=self.password,
        )
        self.assertEqual(authenticated_user, user)

    def test_email_dan_nip_tidak_boleh_ganda(self):
        self.client.post(
            reverse('myaccount_urls:account_registration'),
            self.registration_data(),
        )

        response = self.client.post(
            reverse('myaccount_urls:account_registration'),
            self.registration_data(email='pegawai-lain@example.com'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NIP/NIK pegawai sudah terdaftar.')
        self.assertFalse(Users.objects.filter(email='pegawai-lain@example.com').exists())

    def test_registrasi_baru_terpisah_dari_akun_lama_nonaktif(self):
        old_user = Users.objects.create_user(
            email='pegawai-lama@example.com',
            first_name='Pegawai',
            last_name='Lama',
            password=self.password,
            is_active=False,
        )
        self.client.post(
            reverse('myaccount_urls:account_registration'),
            self.registration_data(),
        )
        new_user = Users.objects.get(email='pegawai-baru@example.com')
        self.client.force_login(self.admin)

        account_response = self.client.get(
            reverse('myaccount_urls:account_management_list') + '?status=inactive'
        )
        registration_response = self.client.get(
            reverse('myaccount_urls:account_registration_review_list')
        )

        self.assertContains(account_response, old_user.email)
        self.assertNotContains(account_response, new_user.email)
        self.assertContains(registration_response, new_user.email)
        self.assertNotContains(registration_response, old_user.email)

    def test_toggle_aktif_tidak_bisa_melewati_verifikasi_registrasi(self):
        self.client.post(
            reverse('myaccount_urls:account_registration'),
            self.registration_data(),
        )
        user = Users.objects.get(email='pegawai-baru@example.com')
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('myaccount_urls:account_toggle_active', args=[user.pk]),
        )

        self.assertEqual(response.status_code, 404)
        user.refresh_from_db()
        self.assertFalse(user.is_active)


class GoogleLoginConfigurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SocialApp.objects.create(
            provider='google',
            name='Google Test',
            client_id='google-test-client-id',
            secret='google-test-secret',
        )

    def test_tombol_google_menggunakan_post_dengan_csrf(self):
        response = self.client.get(reverse('myaccount_urls:login_view'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'method="post"')
        self.assertContains(
            response,
            f'action="{reverse("google_login")}?process=login"',
        )
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_post_google_memulai_oauth_dengan_callback_yang_benar(self):
        response = self.client.post(
            reverse('google_login'),
            HTTP_HOST='127.0.0.1:8000',
        )

        self.assertEqual(response.status_code, 302)
        redirect_url = urlparse(response['Location'])
        params = parse_qs(redirect_url.query)
        self.assertEqual(redirect_url.netloc, 'accounts.google.com')
        self.assertEqual(
            params['redirect_uri'][0],
            'http://127.0.0.1:8000/auth/google/login/callback/',
        )
        self.assertIn('code_challenge', params)

    def test_social_signup_baru_ditutup(self):
        adapter = RestrictToExistingUserAdapter()

        self.assertFalse(adapter.is_open_for_signup(None, None))


class PrivacyPolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SocialApp.objects.create(
            provider='google',
            name='Google Test',
            client_id='google-test-client-id',
            secret='google-test-secret',
        )

    def test_halaman_dapat_diakses_tanpa_login(self):
        response = self.client.get(reverse('privacy_policy'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kebijakan Privasi')
        self.assertContains(response, 'Data dari Google')
        self.assertContains(response, 'Login dengan Google')

    @override_settings(PRIVACY_CONTACT_EMAIL='privacy@example.com')
    def test_kontak_privasi_ditampilkan_dari_environment(self):
        response = self.client.get(reverse('privacy_policy'))

        self.assertContains(response, 'privacy@example.com')

    def test_halaman_login_memiliki_tautan_privasi(self):
        response = self.client.get(reverse('myaccount_urls:login_view'))

        self.assertContains(response, reverse('privacy_policy'))


class AboutSimaduTests(TestCase):
    def test_halaman_dapat_diakses_tanpa_login(self):
        response = self.client.get(reverse('about_simadu'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tentang SIMADU')
        self.assertContains(response, 'e-ticket digital')
        self.assertContains(response, 'Single Sign-On')
        self.assertContains(response, 'Layanan Kepegawaian')
        self.assertContains(response, 'Akses Berbasis Peran')

    def test_halaman_memiliki_tautan_login_dan_privasi(self):
        response = self.client.get(reverse('about_simadu'))

        self.assertContains(response, reverse('myaccount_urls:login_view'))
        self.assertContains(response, reverse('privacy_policy'))


class SignupClosedTemplateTests(TestCase):
    def test_override_template_allauth_menampilkan_pesan_simadu(self):
        content = render_to_string('account/signup_closed.html')

        self.assertIn('Akun Anda belum terdaftar', content)
        self.assertIn('SIMADU tidak membuka pendaftaran akun secara mandiri', content)
        self.assertIn(reverse('myaccount_urls:login_view'), content)
        self.assertIn(reverse('privacy_policy'), content)


class SocialAuthenticationErrorTemplateTests(TestCase):
    def test_override_template_allauth_menampilkan_pesan_simadu(self):
        content = render_to_string('socialaccount/authentication_error.html')

        self.assertIn('Login Google tidak berhasil', content)
        self.assertIn('Coba login kembali dari awal', content)
        self.assertIn(reverse('myaccount_urls:login_view'), content)
        self.assertIn(reverse('privacy_policy'), content)
