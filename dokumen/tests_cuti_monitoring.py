from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from myaccount.models import Users
from myaccount.roles import ADMIN_LAYANAN_CUTI


class RiwayatCutiMonitoringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_LAYANAN_CUTI)
        cls.admin = Users.objects.create_user(
            email='admin-monitoring-cuti@example.com',
            first_name='Admin',
            last_name='Cuti',
            password='Password-123!',
        )
        cls.admin.groups.add(admin_group)
        cls.pegawai = Users.objects.create_user(
            email='pegawai-monitoring-cuti@example.com',
            first_name='Pegawai',
            last_name='Saldo',
            password='Password-123!',
        )
        cls.non_admin = Users.objects.create_user(
            email='bukan-admin-cuti@example.com',
            first_name='Bukan',
            last_name='Admin',
            password='Password-123!',
        )

    def test_admin_cuti_dapat_melihat_saldo_semua_pegawai(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('riwayat_urls:riwayat_cuti_monitoring')
        )

        self.assertEqual(response.status_code, 200)
        row = next(
            item
            for item in response.context['monitoring_rows']
            if item['pegawai'] == self.pegawai
        )
        self.assertEqual(row['n2']['dapat_digunakan'], 6)
        self.assertEqual(row['n1']['dapat_digunakan'], 6)
        self.assertEqual(row['n']['dapat_digunakan'], 12)
        self.assertEqual(row['total_tersedia'], 24)
        self.assertContains(response, 'Pegawai Saldo')
        self.assertContains(response, 'Monitoring Sisa Cuti Pegawai')

    def test_pencarian_memfilter_pegawai(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('riwayat_urls:riwayat_cuti_monitoring'),
            {'q': 'Pegawai Saldo'},
        )

        self.assertEqual(
            [item['pegawai'] for item in response.context['monitoring_rows']],
            [self.pegawai],
        )

    def test_non_admin_cuti_ditolak(self):
        self.client.force_login(self.non_admin)

        response = self.client.get(
            reverse('riwayat_urls:riwayat_cuti_monitoring')
        )

        self.assertEqual(response.status_code, 403)
