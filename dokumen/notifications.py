from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import F

from .models import RiwayatSIPProfesi


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
