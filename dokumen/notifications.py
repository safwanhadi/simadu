from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import F

from .models import RiwayatProfesi, RiwayatSIPProfesi


def get_sip_expiry_notifications(user, today=None, reminder_months=None):
    """SIP terbaru per profesi yang kedaluwarsa atau berakhir dalam periode pengingat."""
    if not user or not user.is_authenticated:
        return []

    today = today or date.today()
    reminder_months = reminder_months or getattr(
        settings,
        'SIP_EXPIRY_REMINDER_MONTHS',
        6,
    )
    reminder_limit = today + relativedelta(months=reminder_months)
    sip_records = (
        RiwayatSIPProfesi.objects
        .filter(riwayat_profesi__pegawai=user, berlaku_sd__isnull=False)
        .select_related('riwayat_profesi', 'riwayat_profesi__profesi')
        .order_by(
            'riwayat_profesi_id',
            F('berlaku_sd').desc(nulls_last=True),
            '-pk',
        )
    )

    notifications = []
    seen_professions = set()
    for sip in sip_records:
        if sip.riwayat_profesi_id in seen_professions:
            continue
        seen_professions.add(sip.riwayat_profesi_id)
        if sip.berlaku_sd > reminder_limit:
            continue

        remaining_days = (sip.berlaku_sd - today).days
        sip.is_expired = remaining_days < 0
        sip.remaining_days = remaining_days
        if remaining_days < 0:
            sip.expiry_message = f'Kedaluwarsa {abs(remaining_days)} hari lalu'
        elif remaining_days == 0:
            sip.expiry_message = 'Berakhir hari ini'
        else:
            sip.expiry_message = f'Berakhir dalam {remaining_days} hari'
        notifications.append(sip)

    return notifications


def get_latest_str_records(user, today=None):
    """Ambil satu STR terbaru untuk setiap profesi dan beri status masa berlaku."""
    if not user or not user.is_authenticated:
        return []

    today = today or date.today()
    records = RiwayatProfesi.objects
    if not (user.is_superuser or user.is_dokumen_admin):
        records = records.filter(pegawai=user)
    records = (
        records
        .select_related('pegawai', 'pegawai__profil_user', 'profesi')
        .order_by(
            'pegawai_id',
            'profesi_id',
            F('tgl_str').desc(nulls_last=True),
            F('str_seumur_hidup').desc(),
            F('berlaku_sd_str').desc(nulls_last=True),
            '-pk',
        )
    )

    latest_records = []
    seen_professions = set()
    for str_record in records:
        profession_key = (
            ('pegawai_profesi', str_record.pegawai_id, str_record.profesi_id)
            if str_record.profesi_id
            else ('record', str_record.pk)
        )
        if profession_key in seen_professions:
            continue
        seen_professions.add(profession_key)

        if str_record.str_seumur_hidup:
            str_record.validity_status = 'seumur_hidup'
            str_record.validity_message = 'Berlaku seumur hidup'
            str_record.is_expired = False
            str_record.remaining_days = None
        elif str_record.berlaku_sd_str:
            remaining_days = (str_record.berlaku_sd_str - today).days
            str_record.validity_status = 'berbatas_waktu'
            str_record.is_expired = remaining_days < 0
            str_record.remaining_days = remaining_days
            if remaining_days < 0:
                str_record.validity_message = (
                    f'Kedaluwarsa {abs(remaining_days)} hari lalu'
                )
            elif remaining_days == 0:
                str_record.validity_message = 'Berakhir hari ini'
            else:
                str_record.validity_message = (
                    f'Berakhir dalam {remaining_days} hari'
                )
        else:
            str_record.validity_status = 'belum_teridentifikasi'
            str_record.validity_message = 'Masa berlaku belum teridentifikasi'
            str_record.is_expired = False
            str_record.remaining_days = None
        str_record.expiry_message = str_record.validity_message
        latest_records.append(str_record)

    return latest_records


def get_str_expiry_notifications(user, today=None, reminder_months=None):
    """STR berbatas waktu yang kedaluwarsa atau berakhir dalam periode pengingat."""
    today = today or date.today()
    reminder_months = reminder_months or getattr(
        settings,
        'STR_EXPIRY_REMINDER_MONTHS',
        6,
    )
    reminder_limit = today + relativedelta(months=reminder_months)
    notifications = []
    for str_record in get_latest_str_records(user, today=today):
        if str_record.validity_status != 'berbatas_waktu':
            continue
        if str_record.berlaku_sd_str > reminder_limit:
            continue
        notifications.append(str_record)

    return notifications
