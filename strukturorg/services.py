"""Resolver pejabat struktur aktif.

Semua proses baru yang memerlukan verifikator/pengesah saat ini sebaiknya
melewati fungsi di modul ini. Snapshot verifikator yang sudah tersimpan pada
pengajuan tetap harus dipakai ketika menampilkan riwayat.
"""

from .models import PejabatStruktur


def get_active_appointment(structure):
    if structure is None:
        return None
    manager = getattr(structure, 'riwayat_pejabat', None)
    if manager is None:
        return None
    return manager.filter(is_active=True).select_related('pejabat').first()


def get_active_leader(structure, *, fallback=True):
    appointment = get_active_appointment(structure)
    if appointment:
        return appointment.pejabat if appointment.pejabat.is_active else None
    if fallback:
        # Fallback diperlukan selama masa deploy/migrasi data lama.
        return getattr(structure, 'nama_pimpinan', None)
    return None


def get_active_title(structure):
    appointment = get_active_appointment(structure)
    if appointment and appointment.nama_jabatan:
        return appointment.nama_jabatan
    return getattr(structure, 'pimpinan', '') if structure else ''


def is_active_leader(user, structure):
    leader = get_active_leader(structure)
    return bool(user and leader and user.pk == leader.pk)


def get_active_leader_ids(structure_model):
    """ID pejabat aktif untuk kebutuhan filter queryset lintas struktur."""
    field_by_model = {
        'instansidaerah': 'instansi_daerah',
        'satuankerjainduk': 'satuan_kerja_induk',
        'unitorganisasi': 'unit_organisasi',
        'bidang': 'bidang',
        'subbidang': 'sub_bidang',
        'unitinstalasi': 'unit_instalasi',
    }
    field_name = field_by_model[structure_model._meta.model_name]
    return PejabatStruktur.objects.filter(
        is_active=True,
        pejabat__is_active=True,
        **{f'{field_name}__isnull': False},
    ).values_list('pejabat_id', flat=True)


def filter_structures_led_by(queryset, user):
    """Batasi queryset struktur ke simpul yang sedang dipimpin user."""
    if not user or not getattr(user, 'is_active', False):
        return queryset.none()
    return queryset.filter(
        riwayat_pejabat__pejabat=user,
        riwayat_pejabat__is_active=True,
        riwayat_pejabat__pejabat__is_active=True,
    ).distinct()
