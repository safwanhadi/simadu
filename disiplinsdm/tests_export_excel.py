from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from PIL import Image

from .views import generate_qr_with_logo_for_excel


class GenerateQrExcelTests(SimpleTestCase):
    def test_qr_tetap_dibuat_ketika_finders_tidak_menemukan_logo(self):
        buffer = generate_qr_with_logo_for_excel('jadwal-dinas', None, size=120)

        with Image.open(buffer) as result:
            self.assertEqual(result.format, 'PNG')
            self.assertEqual(result.size, (120, 120))

    def test_qr_tetap_dibuat_ketika_path_logo_tidak_ada(self):
        with TemporaryDirectory() as directory:
            logo_path = Path(directory) / 'logo-tidak-ada.png'
            buffer = generate_qr_with_logo_for_excel(
                'jadwal-dinas', str(logo_path), size=120
            )

        with Image.open(buffer) as result:
            self.assertEqual(result.format, 'PNG')
