from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from myaccount.models import Users
from myaccount.roles import ADMIN_AKUN

from .models import LogKehadiran, MappingMesinAbsensi


class MappingMesinAbsensiViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_AKUN)
        cls.admin = Users.objects.create_user(
            email='admin-mapping@example.com',
            first_name='Admin',
            last_name='Mapping',
            password='Password-123!',
        )
        cls.admin.groups.add(admin_group)
        cls.employee = Users.objects.create_user(
            email='employee-mapping@example.com',
            first_name='Pegawai',
            last_name='Terpetakan',
            password='Password-123!',
        )
        cls.unmapped = Users.objects.create_user(
            email='unmapped-mapping@example.com',
            first_name='Pegawai',
            last_name='Belum Mapping',
            password='Password-123!',
        )
        cls.mapping = MappingMesinAbsensi.objects.create(
            mesin_id='FP-001',
            pegawai=cls.employee,
        )
        LogKehadiran.objects.create(
            mapping=cls.mapping,
            datetime='2026-08-19T07:00:00Z',
            direction='IN',
            devicename='DEVICE-01',
            personname='Pegawai Terpetakan',
        )

    def test_admin_akun_melihat_ringkasan_mapping(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('disiplinsdm_urls:mapping_mesin_absensi_list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['mapped_count'], 1)
        self.assertEqual(response.context['unmapped_count'], 1)
        self.assertEqual(response.context['recorded_count'], 1)
        self.assertContains(response, 'FP-001')
        self.assertContains(response, 'Sudah terpetakan')

    def test_admin_akun_dapat_membuat_mapping(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('disiplinsdm_urls:mapping_mesin_absensi_create'),
            {'mesin_id': 'FP-002', 'pegawai': self.unmapped.pk},
        )

        self.assertRedirects(response, reverse('disiplinsdm_urls:mapping_mesin_absensi_list'))
        self.assertTrue(MappingMesinAbsensi.objects.filter(mesin_id='FP-002', pegawai=self.unmapped).exists())

    def test_admin_akun_dapat_mengubah_mapping(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('disiplinsdm_urls:mapping_mesin_absensi_update', kwargs={'pk': self.mapping.pk}),
            {'mesin_id': 'FP-009', 'pegawai': self.employee.pk},
        )

        self.assertRedirects(response, reverse('disiplinsdm_urls:mapping_mesin_absensi_list'))
        self.mapping.refresh_from_db()
        self.assertEqual(self.mapping.mesin_id, 'FP-009')

    def test_pengguna_biasa_ditolak(self):
        self.client.force_login(self.employee)

        response = self.client.get(reverse('disiplinsdm_urls:mapping_mesin_absensi_list'))

        self.assertEqual(response.status_code, 403)
