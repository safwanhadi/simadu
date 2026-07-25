from django.test import SimpleTestCase

from .views import _build_catatan_cuti_tahunan, _status_checkbox_line


class FormulirCutiPdfHelperTests(SimpleTestCase):
    def test_catatan_cuti_memakai_snapshot_yang_disimpan(self):
        snapshot = {
            'dibuat_pada': '2026-07-25',
            'total_tersedia': 9,
            'rows': [
                {
                    'label': 'N-2',
                    'tahun': 2024,
                    'terpakai': 4,
                    'sisa_hak': 8,
                    'dapat_digunakan': 3,
                    'sisa_tunda': 3,
                },
                {
                    'label': 'N-1',
                    'tahun': 2025,
                    'terpakai': 6,
                    'sisa_hak': 6,
                    'dapat_digunakan': 2,
                    'sisa_tunda': 0,
                },
                {
                    'label': 'N',
                    'tahun': 2026,
                    'terpakai': 4,
                    'sisa_hak': 8,
                    'dapat_digunakan': 4,
                    'sisa_tunda': 0,
                },
            ],
        }

        catatan = _build_catatan_cuti_tahunan(
            pegawai=None,
            tahun_ref=2026,
            snapshot=snapshot,
        )

        self.assertEqual(catatan['dibuat_pada'], '2026-07-25')
        self.assertEqual(catatan['total_tersedia'], 9)
        self.assertEqual([row[4] for row in catatan['rows']], ['3', '2', '4'])
        self.assertEqual(catatan['rows'][2][2], '8')
        self.assertEqual(catatan['rows'][2][3], '4')
        self.assertIn('Hak tunda 3 hari', catatan['rows'][0][5])
        self.assertIn('Kompensasi hak tahun 2025', catatan['rows'][1][5])
        self.assertIn('terpakai 8 hari', catatan['rows'][2][5])

    def test_status_verifikasi_baru_ditampilkan_pada_checkbox(self):
        self.assertIn('[✓] DISETUJUI', _status_checkbox_line('setuju'))
        self.assertIn('[✓] DITANGGUHKAN', _status_checkbox_line('tunda'))
        self.assertIn('[✓] TIDAK DISETUJUI', _status_checkbox_line('tolak'))
