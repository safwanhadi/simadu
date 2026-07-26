from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.urls import reverse

from myaccount.models import ProfilSDM, Users

from .models import RiwayatProfesi, RiwayatSIPProfesi
from .notifications import (
    get_latest_str_records,
    get_sip_expiry_notifications,
    get_str_expiry_notifications,
)


class SIPExpiryNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Users.objects.create_user(
            email='sip-reminder@example.com',
            first_name='Pegawai',
            last_name='SIP',
            password='Password-SIP-123!',
        )
        ProfilSDM.objects.create(
            user=cls.user,
            nip='19990001',
            no_hp='081200000099',
            email_pribadi=cls.user.email,
        )
        cls.profession = RiwayatProfesi.objects.create(pegawai=cls.user)

        cls.other_user = Users.objects.create_user(
            email='sip-reminder-other@example.com',
            first_name='Pegawai',
            last_name='Lain',
            password='Password-SIP-123!',
        )
        ProfilSDM.objects.create(
            user=cls.other_user,
            nip='19990002',
            no_hp='081200000098',
            email_pribadi=cls.other_user.email,
        )
        cls.other_profession = RiwayatProfesi.objects.create(
            pegawai=cls.other_user,
        )

    def create_sip(self, profession=None, **overrides):
        values = {
            'riwayat_profesi': profession or self.profession,
            'no_sip': 'SIP-001',
            'tgl_sip': date(2025, 1, 1),
            'berlaku_sd': date(2027, 1, 1),
        }
        values.update(overrides)
        return RiwayatSIPProfesi.objects.create(**values)

    def test_sip_tepat_enam_bulan_sebelum_expired_muncul(self):
        today = date(2026, 1, 15)
        sip = self.create_sip(berlaku_sd=today + relativedelta(months=6))

        notifications = get_sip_expiry_notifications(self.user, today=today)

        self.assertEqual([item.pk for item in notifications], [sip.pk])
        self.assertFalse(notifications[0].is_expired)

    def test_sip_di_luar_enam_bulan_tidak_muncul(self):
        today = date(2026, 1, 15)
        self.create_sip(
            berlaku_sd=today + relativedelta(months=6) + timedelta(days=1),
        )

        self.assertEqual(
            get_sip_expiry_notifications(self.user, today=today),
            [],
        )

    def test_sip_expired_tetap_muncul_dengan_status_kedaluwarsa(self):
        today = date(2026, 1, 15)
        self.create_sip(berlaku_sd=today - timedelta(days=10))

        notification = get_sip_expiry_notifications(self.user, today=today)[0]

        self.assertTrue(notification.is_expired)
        self.assertEqual(notification.expiry_message, 'Kedaluwarsa 10 hari lalu')

    def test_sip_lama_tidak_muncul_jika_sudah_diperbarui(self):
        today = date(2026, 1, 15)
        self.create_sip(no_sip='SIP-LAMA', berlaku_sd=today - timedelta(days=1))
        self.create_sip(
            no_sip='SIP-BARU',
            berlaku_sd=today + relativedelta(years=1),
        )

        self.assertEqual(
            get_sip_expiry_notifications(self.user, today=today),
            [],
        )

    def test_sip_pegawai_lain_tidak_muncul(self):
        today = date(2026, 1, 15)
        self.create_sip(
            profession=self.other_profession,
            berlaku_sd=today + timedelta(days=10),
        )

        self.assertEqual(
            get_sip_expiry_notifications(self.user, today=today),
            [],
        )

    def test_pengingat_tampil_di_dropdown_notifikasi(self):
        self.create_sip(
            no_sip='SIP-NOTIFIKASI',
            berlaku_sd=date.today() + timedelta(days=30),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('riwayat_urls:riwayat_view'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SIP SIP-NOTIFIKASI')
        self.assertContains(response, 'Berakhir dalam 30 hari')

    def test_pengingat_sip_dapat_dibuka_dari_menu_sidebar(self):
        self.create_sip(
            no_sip='SIP-MENU',
            berlaku_sd=date.today() + timedelta(days=30),
        )
        self.client.force_login(self.user)

        response = self.client.get(
            f"{reverse('layanan_urls:notifikasi_view')}?layanan=sip-expiry"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pengingat Masa Berlaku SIP')
        self.assertContains(response, 'SIP-MENU')
        self.assertContains(response, 'Pengingat SIP')

    def test_str_tepat_enam_bulan_sebelum_expired_muncul(self):
        today = date(2026, 1, 15)
        self.profession.no_str = 'STR-ENAM-BULAN'
        self.profession.berlaku_sd_str = today + relativedelta(months=6)
        self.profession.save(update_fields=['no_str', 'berlaku_sd_str'])

        notifications = get_str_expiry_notifications(
            self.user,
            today=today,
        )

        self.assertEqual([item.pk for item in notifications], [self.profession.pk])
        self.assertFalse(notifications[0].is_expired)

    def test_str_di_luar_enam_bulan_tidak_muncul(self):
        today = date(2026, 1, 15)
        self.profession.berlaku_sd_str = (
            today + relativedelta(months=6) + timedelta(days=1)
        )
        self.profession.save(update_fields=['berlaku_sd_str'])

        self.assertEqual(
            get_str_expiry_notifications(self.user, today=today),
            [],
        )

    def test_str_expired_tetap_muncul(self):
        today = date(2026, 1, 15)
        self.profession.berlaku_sd_str = today - timedelta(days=10)
        self.profession.save(update_fields=['berlaku_sd_str'])

        notification = get_str_expiry_notifications(
            self.user,
            today=today,
        )[0]

        self.assertTrue(notification.is_expired)
        self.assertEqual(notification.expiry_message, 'Kedaluwarsa 10 hari lalu')

    def test_tab_pengingat_str_dapat_dibuka(self):
        self.profession.no_str = 'STR-TAB'
        self.profession.berlaku_sd_str = date.today() + timedelta(days=30)
        self.profession.save(update_fields=['no_str', 'berlaku_sd_str'])
        self.client.force_login(self.user)

        response = self.client.get(
            f"{reverse('layanan_urls:notifikasi_view')}?layanan=str-expiry"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pengingat Masa Berlaku STR')
        self.assertContains(response, 'STR-TAB')
        self.assertContains(response, 'Masa Berlaku SIP')
        self.assertContains(response, 'Masa Berlaku STR')

    def test_str_seumur_hidup_tidak_menghasilkan_pengingat_expiry(self):
        today = date(2026, 1, 15)
        self.profession.no_str = 'STR-SEUMUR-HIDUP'
        self.profession.berlaku_sd_str = today - timedelta(days=1)
        self.profession.str_seumur_hidup = True
        self.profession.save(update_fields=[
            'no_str', 'berlaku_sd_str', 'str_seumur_hidup',
        ])

        self.assertEqual(
            get_str_expiry_notifications(self.user, today=today),
            [],
        )
        record = get_latest_str_records(self.user, today=today)[0]
        self.assertEqual(record.validity_status, 'seumur_hidup')

    def test_tab_str_dapat_filter_status_seumur_hidup(self):
        self.profession.no_str = 'STR-SEUMUR-HIDUP'
        self.profession.str_seumur_hidup = True
        self.profession.berlaku_sd_str = None
        self.profession.save(update_fields=[
            'no_str', 'str_seumur_hidup', 'berlaku_sd_str',
        ])
        RiwayatProfesi.objects.create(
            pegawai=self.user,
            no_str='STR-BELUM-ID',
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('layanan_urls:notifikasi_view'),
            {'layanan': 'str-expiry', 'status_str': 'seumur_hidup'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'STR-SEUMUR-HIDUP')
        self.assertNotContains(response, 'STR-BELUM-ID')

    def test_tab_str_memberi_info_jika_semua_str_seumur_hidup(self):
        self.profession.str_seumur_hidup = True
        self.profession.berlaku_sd_str = None
        self.profession.save(update_fields=[
            'str_seumur_hidup', 'berlaku_sd_str',
        ])
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('layanan_urls:notifikasi_view'),
            {'layanan': 'str-expiry'},
        )

        self.assertContains(
            response,
            'Semua STR terbaru sudah teridentifikasi berlaku seumur hidup.',
        )
