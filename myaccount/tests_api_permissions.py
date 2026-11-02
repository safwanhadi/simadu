import base64

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from oauth2_provider.models import Application

from .models import Users
from .roles import ADMIN_DOKUMEN


class EmployeeListAPIPermissionTests(TestCase):
    endpoint_names = (
        'myaccount_urls:pegawai_api_view',
        'myaccount_urls:dokter_spesialis_api_view',
        'myaccount_urls:pegawai_perawat_aktif_api_view',
    )

    @classmethod
    def setUpTestData(cls):
        cls.user = Users.objects.create_user(
            email='pegawai@example.test',
            first_name='Pegawai',
            last_name='Biasa',
        )
        cls.admin = Users.objects.create_user(
            email='admin@example.test',
            first_name='Admin',
            last_name='SIMADU',
        )
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_DOKUMEN)
        cls.admin.groups.add(admin_group)

    def test_session_user_without_admin_role_is_denied(self):
        self.client.force_login(self.user)

        for endpoint_name in self.endpoint_names:
            with self.subTest(endpoint=endpoint_name):
                response = self.client.get(reverse(endpoint_name))
                self.assertEqual(response.status_code, 403)

    def test_app_admin_session_can_access_employee_lists(self):
        self.client.force_login(self.admin)

        for endpoint_name in self.endpoint_names:
            with self.subTest(endpoint=endpoint_name):
                response = self.client.get(reverse(endpoint_name))
                self.assertEqual(response.status_code, 200)

    def test_oauth_token_with_list_scope_can_access_employee_lists(self):
        access_token = self._get_access_token('read:listpegawai')

        for endpoint_name in self.endpoint_names:
            with self.subTest(endpoint=endpoint_name):
                response = self.client.get(
                    reverse(endpoint_name),
                    HTTP_AUTHORIZATION=f'Bearer {access_token}',
                )
                self.assertEqual(response.status_code, 200)

    def test_oauth_token_without_list_scope_is_denied(self):
        access_token = self._get_access_token('read:dash')

        for endpoint_name in self.endpoint_names:
            with self.subTest(endpoint=endpoint_name):
                response = self.client.get(
                    reverse(endpoint_name),
                    HTTP_AUTHORIZATION=f'Bearer {access_token}',
                )
                self.assertEqual(response.status_code, 403)

    def _get_access_token(self, scope):
        client_secret = 'test-client-secret'
        application = Application.objects.create(
            name='API permission test',
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            client_secret=client_secret,
        )
        credentials = base64.b64encode(
            f'{application.client_id}:{client_secret}'.encode('utf-8')
        ).decode('ascii')
        response = self.client.post(
            reverse('oauth2_provider:token'),
            {'grant_type': 'client_credentials', 'scope': scope},
            HTTP_AUTHORIZATION=f'Basic {credentials}',
        )
        self.assertEqual(response.status_code, 200)
        return response.json()['access_token']
