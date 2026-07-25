from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from myaccount.models import Users

from .models import (
    InstansiDaerah, PejabatStruktur, SatuanKerjaInduk, UnitOrganisasi,
)
from .services import get_active_leader, get_active_title


class PejabatStrukturTests(TestCase):
    def setUp(self):
        self.old_leader = Users.objects.create_user(
            email='pejabat-lama@example.com', first_name='Pejabat',
            last_name='Lama', password='test-password',
        )
        self.new_leader = Users.objects.create_user(
            email='pejabat-baru@example.com', first_name='Pejabat',
            last_name='Baru', password='test-password',
        )
        instansi = InstansiDaerah.objects.create(instansi='Pemerintah Uji')
        satker = SatuanKerjaInduk.objects.create(
            instansi_daerah=instansi, satuan_kerja='Rumah Sakit Uji',
        )
        self.unor = UnitOrganisasi.objects.create(
            satker_induk=satker, unor='Direktorat Uji',
            pimpinan='Direktur', nama_pimpinan=self.old_leader,
        )

    def test_legacy_leader_remains_available_during_rollout(self):
        self.assertEqual(get_active_leader(self.unor), self.old_leader)

    def test_turnover_deactivates_old_term_and_updates_legacy_cache(self):
        old_term = PejabatStruktur.objects.create(
            unit_organisasi=self.unor,
            pejabat=self.old_leader,
            nama_jabatan='Direktur',
            tanggal_mulai=date(2025, 1, 1),
        )
        new_term = PejabatStruktur.objects.create(
            unit_organisasi=self.unor,
            pejabat=self.new_leader,
            nama_jabatan='Plt. Direktur',
            tanggal_mulai=date(2026, 7, 20),
        )

        old_term.refresh_from_db()
        self.unor.refresh_from_db()
        self.assertFalse(old_term.is_active)
        self.assertEqual(old_term.tanggal_selesai, new_term.tanggal_mulai)
        self.assertEqual(get_active_leader(self.unor), self.new_leader)
        self.assertEqual(get_active_title(self.unor), 'Plt. Direktur')
        self.assertEqual(self.unor.nama_pimpinan, self.new_leader)

    def test_exactly_one_structure_target_is_required(self):
        term = PejabatStruktur(
            pejabat=self.new_leader,
            tanggal_mulai=date(2026, 7, 20),
        )
        with self.assertRaises(ValidationError):
            term.save()
