from django.test import TestCase
from django.contrib.auth.models import Group
from django.urls import resolve, reverse

from myaccount.models import Users
from myaccount.roles import ADMIN_INFORMASI

from .models import (
    InformasiSDM, KategoriInformasi, KategoriVideo, ReVideoComment,
    VideoComment, VideoYoutube,
)
from .views import VideoTutorialView


class InformasiUserInterfaceTests(TestCase):
    def setUp(self):
        self.user = Users.objects.create_user(
            email='pegawai@example.test',
            first_name='Pegawai',
            last_name='Uji',
            password='test-password',
        )
        self.client.force_login(self.user)
        self.info_category = KategoriInformasi.objects.create(kategori='Kepegawaian')
        self.video_category = KategoriVideo.objects.create(kategori='SIMRS Rawat Jalan')

    def test_tutorial_url_resolves_to_tutorial_view(self):
        match = resolve(reverse('informasi_urls:tutorial_view'))
        self.assertIs(match.func.view_class, VideoTutorialView)

    def test_youtube_id_supports_legacy_url_formats(self):
        cases = {
            'abcdefghijk': 'abcdefghijk',
            'https://www.youtube.com/watch?v=abcdefghijk': 'abcdefghijk',
            'https://youtu.be/abcdefghijk?t=10': 'abcdefghijk',
            'https://www.youtube.com/embed/abcdefghijk': 'abcdefghijk',
            'https://www.youtube.com/shorts/abcdefghijk': 'abcdefghijk',
        }
        for stored_value, expected in cases.items():
            with self.subTest(stored_value=stored_value):
                self.assertEqual(VideoYoutube(id_video=stored_value).youtube_id, expected)

    def test_information_search_and_category_filter(self):
        InformasiSDM.objects.create(
            kategori=self.info_category,
            author=self.user,
            judul='Panduan Kenaikan Pangkat',
            isi='Informasi pengajuan dokumen pegawai',
            status='publish',
        )
        InformasiSDM.objects.create(
            kategori=self.info_category,
            author=self.user,
            judul='Informasi tersembunyi',
            isi='Tidak boleh muncul',
            status='draft',
        )

        response = self.client.get(reverse('informasi_urls:informasi_view'), {'q': 'pangkat'})

        self.assertContains(response, 'Panduan Kenaikan Pangkat')
        self.assertNotContains(response, 'Informasi tersembunyi')
        self.assertEqual(response.context['page_obj'].paginator.count, 1)

    def test_tutorial_filters_category_and_hides_drafts(self):
        published_video = VideoYoutube.objects.create(
            kategori=self.video_category,
            author=self.user,
            judul_video='Pendaftaran Rawat Jalan di SIMRS',
            id_video='published-video',
            status='publish',
        )
        VideoYoutube.objects.create(
            kategori=self.video_category,
            author=self.user,
            judul_video='Video Belum Publik',
            id_video='draft-video',
            status='draft',
        )

        response = self.client.get(
            reverse('informasi_urls:tutorial_view'),
            {'kategori': self.video_category.slug, 'q': 'rawat jalan'},
        )

        self.assertContains(response, published_video.judul_video)
        self.assertNotContains(response, 'Video Belum Publik')
        self.assertEqual(list(response.context['data']), [published_video])

    def test_user_can_reply_to_comment_on_published_video(self):
        video = VideoYoutube.objects.create(
            kategori=self.video_category,
            author=self.user,
            judul_video='Tutorial SIMRS',
            id_video='reply-video',
            status='publish',
        )
        comment = VideoComment.objects.create(
            video=video,
            author=self.user,
            comment='Bagaimana langkah berikutnya?',
        )

        response = self.client.post(
            f"{reverse('informasi_urls:tutorial_view')}?vid={video.id_video}",
            {
                'action': 'reply',
                'video_id': video.pk,
                'comment_id': comment.pk,
                'recomment': 'Silakan lanjutkan ke menu pelayanan.',
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('informasi_urls:tutorial_view')}?vid={video.id_video}#comment-{comment.pk}",
            fetch_redirect_response=False,
        )
        reply = ReVideoComment.objects.get(comment=comment)
        self.assertEqual(reply.author, self.user)
        self.assertEqual(reply.recomment, 'Silakan lanjutkan ke menu pelayanan.')

    def test_admin_dapat_menambahkan_kategori_tutorial_saat_entri_video(self):
        admin = Users.objects.create_superuser(
            email='admin-tutorial@example.test', first_name='Admin', last_name='Tutorial',
            password='test-password',
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse('informasi_urls:tutorial_view'),
            {'action': 'add_category', 'kategori': 'Mandacare IGD'},
        )

        kategori = KategoriVideo.objects.get(kategori='Mandacare IGD')
        self.assertRedirects(
            response,
            f'{reverse("informasi_urls:tutorial_view")}?kategori={kategori.slug}#openModal',
            fetch_redirect_response=False,
        )

    def test_admin_informasi_dapat_menambahkan_video_dan_kategori_tutorial(self):
        admin = Users.objects.create_user(
            email='admin-informasi@example.test', first_name='Admin', last_name='Informasi',
            password='test-password',
        )
        group, _ = Group.objects.get_or_create(name=ADMIN_INFORMASI)
        admin.groups.add(group)
        self.client.force_login(admin)

        response = self.client.get(reverse('informasi_urls:tutorial_view'))
        self.assertContains(response, 'Tambah Video')

        response = self.client.post(
            reverse('informasi_urls:tutorial_view'),
            {'action': 'add_category', 'kategori': 'Panduan Admin Informasi'},
        )

        kategori = KategoriVideo.objects.get(kategori='Panduan Admin Informasi')
        self.assertRedirects(
            response,
            f'{reverse("informasi_urls:tutorial_view")}?kategori={kategori.slug}#openModal',
            fetch_redirect_response=False,
        )

    def test_pengguna_biasa_tidak_dapat_menambahkan_kategori_tutorial(self):
        response = self.client.post(
            reverse('informasi_urls:tutorial_view'),
            {'action': 'add_category', 'kategori': 'Mandacare IGD'},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(KategoriVideo.objects.filter(kategori='Mandacare IGD').exists())
