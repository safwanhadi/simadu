from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from oauth2_provider.models import Application

from .models import Users
from .roles import ADMIN_SSO


class SSOManagementTests(TestCase):
    def setUp(self):
        self.admin = Users.objects.create_user(
            email='sso-admin@example.test',
            first_name='Admin',
            last_name='SSO',
            password='rahasia-kuat',
        )
        self.admin.groups.add(Group.objects.create(name=ADMIN_SSO))
        self.regular = Users.objects.create_user(
            email='user@example.test',
            first_name='User',
            last_name='Biasa',
            password='rahasia-kuat',
        )

    def test_role_sso_dapat_membuka_pengelolaan_tanpa_status_staff(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('myaccount_urls:sso_application_list'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.admin.is_staff)

    def test_user_biasa_ditolak(self):
        self.client.force_login(self.regular)
        response = self.client.get(reverse('myaccount_urls:sso_application_list'))
        self.assertEqual(response.status_code, 403)

    def test_admin_sso_dapat_membuat_client_credentials(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('myaccount_urls:sso_application_create'),
            {
                'name': 'Bridge Presensi',
                'client_type': Application.CLIENT_CONFIDENTIAL,
                'authorization_grant_type': Application.GRANT_CLIENT_CREDENTIALS,
                'redirect_uris': '',
                'post_logout_redirect_uris': '',
                'allowed_origins': '',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        application = Application.objects.get(name='Bridge Presensi')
        self.assertEqual(application.user, self.admin)
        self.assertContains(response, 'hanya ditampilkan sekali')
        self.assertNotContains(response, application.client_secret)

    def test_redirect_uri_wajib_untuk_authorization_code(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('myaccount_urls:sso_application_create'),
            {
                'name': 'Portal',
                'client_type': Application.CLIENT_CONFIDENTIAL,
                'authorization_grant_type': Application.GRANT_AUTHORIZATION_CODE,
                'redirect_uris': '',
                'post_logout_redirect_uris': '',
                'allowed_origins': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'redirect_uris',
            'Redirect URI wajib untuk jenis grant ini.',
        )
