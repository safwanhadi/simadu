import calendar

from django.test import SimpleTestCase

from .templatetags.template_tags import month_name


class MonthNameFilterTests(SimpleTestCase):
    def test_menerima_nomor_bulan_dalam_bentuk_string(self):
        self.assertEqual(month_name('7'), calendar.month_name[7])

    def test_nilai_kosong_atau_di_luar_rentang_tidak_error(self):
        self.assertEqual(month_name(''), '')
        self.assertEqual(month_name(None), '')
        self.assertEqual(month_name('13'), '')
