from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from .models import ProfilSDM, Users
from .views_api import PegawaiAPIView


class PegawaiAPISearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pegawai = Users.objects.create_user(
            email='pencarian@example.com', first_name='Budi', last_name='Santoso',
        )
        ProfilSDM.objects.create(
            user=cls.pegawai, nip='198001012010011001',
            no_hp='', email_pribadi='pribadi@example.com',
        )
        cls.lain = Users.objects.create_user(
            email='lain@example.com', first_name='Siti', last_name='Aminah',
        )

    def search_ids(self, params):
        view = PegawaiAPIView()
        view.request = Request(APIRequestFactory().get('/api/pegawai/', params))
        queryset = view.filter_queryset(view.get_queryset())
        return set(queryset.values_list('pk', flat=True))

    def test_search_nama_nip_dan_email(self):
        for term in ['bUd', 'SANTOS', 'Budi Santoso', '201001', 'PENCARIAN@']:
            with self.subTest(term=term):
                self.assertEqual(self.search_ids({'search': term}), {self.pegawai.pk})

    def test_search_tidak_cocok(self):
        self.assertEqual(self.search_ids({'search': 'tidak-ditemukan'}), set())

    def test_search_kosong(self):
        for params in [{}, {'search': ''}, {'search': '   '}]:
            with self.subTest(params=params):
                self.assertEqual(self.search_ids(params), {self.pegawai.pk, self.lain.pk})

    def test_filter_nip_persis_dan_kombinasi_search(self):
        nip = '198001012010011001'
        self.assertEqual(self.search_ids({'nip': nip}), {self.pegawai.pk})
        self.assertEqual(self.search_ids({'nip': '201001'}), set())
        self.assertEqual(self.search_ids({'nip': nip, 'search': 'Budi'}), {self.pegawai.pk})
        self.assertEqual(self.search_ids({'nip': nip, 'search': 'Siti'}), set())

    def test_search_pegawai_tanpa_profil(self):
        self.assertEqual(self.search_ids({'search': 'Siti'}), {self.lain.pk})
