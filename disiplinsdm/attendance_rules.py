WORK = 'WORK'
HOLIDAY = 'HOLIDAY'
UNASSESSED = 'UNASSESSED'
MISSING_SCHEDULE = 'MISSING_SCHEDULE'


def classify_daily_obligation(is_calendar_holiday, schedule_types):
    """
    Menentukan kewajiban hadir dengan kalender sebagai aturan global dan
    jadwal pegawai sebagai pengecualian/perincian.

    - Pada tanggal merah, hanya jadwal Piket yang tetap wajib masuk.
    - Pada hari biasa, jadwal Libur membebaskan pegawai dari kewajiban masuk.
    - Hari biasa tanpa jadwal yang sah ditandai khusus agar orchestrator
      dapat memberi ALPA dengan keterangan "jadwal belum dibuat".
    """
    normalized_types = {
        str(schedule_type).strip().casefold()
        for schedule_type in schedule_types
        if schedule_type
    }

    if is_calendar_holiday:
        return WORK if 'piket' in normalized_types else HOLIDAY

    if 'libur' in normalized_types:
        return HOLIDAY

    if normalized_types.intersection({'reguler', 'piket'}):
        return WORK

    return MISSING_SCHEDULE


def is_successful_apel(tipe_log, status_ketepatan, devicename=None):
    """
    Hanya tapping apel yang benar-benar dinilai hadir yang boleh masuk rekap.
    Log buatan sistem seperti "Mangkir Apel" tidak pernah dihitung.
    """
    return (
        str(tipe_log).strip().upper() == 'APEL'
        and str(status_ketepatan).strip().upper() == 'APEL'
        and str(devicename or '').strip().casefold() == 'apel'
    )
