from django.test import TestCase
from django.urls import reverse

from myaccount.models import ProfilAdmin, Users

from .views import get_accessible_takah


class DashboardTakahAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = Users.objects.create_user(
            email='staff-tanpa-profil@example.com',
            first_name='Staff',
            last_name='Tanpa Profil',
            password='Password-123!',
            is_staff=True,
        )
        cls.staff_empty_scope = Users.objects.create_user(
            email='staff-scope-kosong@example.com',
            first_name='Staff',
            last_name='Scope Kosong',
            password='Password-123!',
            is_staff=True,
        )
        ProfilAdmin.objects.create(user=cls.staff_empty_scope)
        cls.pegawai = Users.objects.create_user(
            email='pegawai-dashboard@example.com',
            first_name='Pegawai',
            last_name='Dashboard',
            password='Password-123!',
        )

    def test_staff_tanpa_profil_admin_mendapat_queryset_kosong(self):
        self.assertFalse(get_accessible_takah(self.staff).exists())

    def test_staff_tanpa_cakupan_mendapat_queryset_kosong(self):
        self.assertFalse(get_accessible_takah(self.staff_empty_scope).exists())

    def test_dashboard_staff_tanpa_profil_tidak_error(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('dashboard_urls:dashboard_view'))

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['takah'], [])
