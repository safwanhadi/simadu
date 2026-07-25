from django.test import SimpleTestCase

from .attendance_rules import (
    HOLIDAY,
    MISSING_SCHEDULE,
    WORK,
    classify_daily_obligation,
    is_successful_apel,
)


class DailyAttendanceObligationTests(SimpleTestCase):
    def test_regular_schedule_is_holiday_on_calendar_holiday(self):
        result = classify_daily_obligation(True, {'Reguler'})
        self.assertEqual(result, HOLIDAY)

    def test_piket_schedule_still_works_on_calendar_holiday(self):
        result = classify_daily_obligation(True, {'Piket'})
        self.assertEqual(result, WORK)

    def test_regular_schedule_works_on_normal_day(self):
        result = classify_daily_obligation(False, {'Reguler'})
        self.assertEqual(result, WORK)

    def test_employee_schedule_holiday_wins_on_normal_day(self):
        result = classify_daily_obligation(False, {'Libur'})
        self.assertEqual(result, HOLIDAY)

    def test_missing_schedule_on_normal_day_gets_special_classification(self):
        result = classify_daily_obligation(False, set())
        self.assertEqual(result, MISSING_SCHEDULE)

    def test_missing_schedule_on_calendar_holiday_is_holiday(self):
        result = classify_daily_obligation(True, set())
        self.assertEqual(result, HOLIDAY)

    def test_only_real_successful_apel_is_counted(self):
        self.assertTrue(is_successful_apel('APEL', 'Apel', 'apel'))
        self.assertFalse(is_successful_apel('APEL', 'Mangkir Apel', 'Sistem Otomatis'))
        self.assertFalse(is_successful_apel('APEL', 'Tidak Apel', 'apel'))
        self.assertFalse(is_successful_apel('APEL', 'Apel', 'Sistem Otomatis'))

# Create your tests here.
