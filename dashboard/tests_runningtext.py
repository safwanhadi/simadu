from types import SimpleNamespace

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from dashboard.context_processors import runningtext
from dashboard.hadist_modal import hadist_modal_session_key
from dashboard.views import tandai_hadist_modal_sudah_tampil
from informasi.models import NasehatdanHadist


class RunningTextSessionModalTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.hadist = NasehatdanHadist.objects.create(
            hadist='Sesungguhnya bersama kesulitan ada kemudahan.',
            author_perawi='QS. Al-Insyirah',
        )

    def _request(
        self,
        session=None,
        agama='Islam',
        is_superuser=False,
        user_id=1,
    ):
        request = self.factory.get('/')
        SessionMiddleware(lambda req: None).process_request(request)
        if session:
            request.session.update(session)
        request.user = SimpleNamespace(
            pk=user_id,
            is_authenticated=True,
            is_superuser=is_superuser,
            profil_user=SimpleNamespace(agama=agama),
        )
        return request

    def test_modal_hanya_berhenti_setelah_browser_menandai_sudah_tampil(self):
        request = self._request()

        context_pertama = runningtext(request)
        request.method = 'POST'
        response = tandai_hadist_modal_sudah_tampil(request)
        context_setelah_modal_tampil = runningtext(request)

        self.assertTrue(context_pertama['show_hadist_modal'])
        self.assertEqual(response.status_code, 204)
        self.assertFalse(context_setelah_modal_tampil['show_hadist_modal'])
        self.assertEqual(context_pertama['hadist'], self.hadist)

    def test_modal_tampil_kembali_pada_session_baru(self):
        user = SimpleNamespace(pk=1)
        session_lama = {hadist_modal_session_key(user): True}

        self.assertFalse(
            runningtext(self._request(session=session_lama))['show_hadist_modal']
        )
        self.assertTrue(runningtext(self._request())['show_hadist_modal'])

    def test_modal_tidak_tampil_untuk_pengguna_non_islam(self):
        context = runningtext(self._request(agama='Kristen'))

        self.assertFalse(context['show_hadist_modal'])
        self.assertIsNone(context['hadist'])

    def test_modal_tampil_untuk_superuser_tanpa_agama_islam(self):
        context = runningtext(
            self._request(agama=None, is_superuser=True)
        )

        self.assertTrue(context['show_hadist_modal'])
        self.assertEqual(context['hadist'], self.hadist)

    def test_setiap_user_mendapat_modal_dalam_session_browser_yang_sama(self):
        request_user_pertama = self._request(user_id=1)
        context_user_pertama = runningtext(request_user_pertama)
        request_user_pertama.method = 'POST'
        tandai_hadist_modal_sudah_tampil(request_user_pertama)

        request_user_kedua = self._request(
            session=dict(request_user_pertama.session),
            user_id=2,
        )
        context_user_kedua = runningtext(request_user_kedua)

        self.assertTrue(context_user_pertama['show_hadist_modal'])
        self.assertTrue(context_user_kedua['show_hadist_modal'])
        self.assertIn(
            hadist_modal_session_key(request_user_pertama.user),
            request_user_kedua.session,
        )
        self.assertNotIn(
            hadist_modal_session_key(request_user_kedua.user),
            request_user_kedua.session,
        )
