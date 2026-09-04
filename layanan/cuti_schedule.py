from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from dokumen.models import RiwayatCuti
from myaccount.models import Users

from .models import PelimpahanTugas, PerubahanJadwalCuti, VerifikasiCuti
from .services import CheckCuti
from .cuti_calendar import (
    PolaKerjaTidakDitemukan,
    get_pola_kerja_aktif,
    hitung_lama_cuti_tahunan,
)


def _iso(value):
    return value.isoformat() if value else None


def _date_from_iso(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


def snapshot_verification(verifikasi):
    if verifikasi is None:
        return {}
    data = {}
    for level in (1, 2, 3):
        data[str(level)] = {
            'verifikator_id': getattr(verifikasi, f'verifikator{level}_id'),
            'keputusan': getattr(verifikasi, f'keputusan{level}'),
            'catatan': getattr(verifikasi, f'catatan{level}'),
            'diputuskan_pada': _iso(getattr(verifikasi, f'diputuskan_pada{level}')),
        }
    return data


def snapshot_delegation(pelimpahan):
    if pelimpahan is None:
        return {}
    return {
        'tgl_mulai': _iso(pelimpahan.tgl_mulai),
        'tgl_selesai': _iso(pelimpahan.tgl_selesai),
        'status': pelimpahan.status,
        'persetujuan_penerima': pelimpahan.persetujuan_penerima,
        'catatan_penerima': pelimpahan.catatan_penerima,
        'atasan_penyetuju_id': pelimpahan.atasan_penyetuju_id,
        'persetujuan_atasan': pelimpahan.persetujuan_atasan,
        'catatan_atasan': pelimpahan.catatan_atasan,
        'butuh_persetujuan_atasan': pelimpahan.butuh_persetujuan_atasan,
    }


def determine_change_type(riwayat):
    if riwayat.usulan.status in ('disetujui', 'selesai'):
        return 'perubahan_final'
    verifikasi = VerifikasiCuti.objects.filter(layanan_cuti=riwayat.usulan).first()
    if verifikasi and any(
        getattr(verifikasi, f'keputusan{level}') != 'belum' for level in (1, 2, 3)
    ):
        return 'revisi_proses'
    return 'langsung'


def _validate_capacity(change, riwayat):
    if riwayat.jenis_cuti != CheckCuti.CUTI_TAHUNAN:
        return
    claims = riwayat.klaim_masuk.aggregate(total=Sum('jumlah_hari_diklaim'))['total'] or 0
    if change.lama_cuti_baru < claims:
        raise ValidationError('Durasi baru lebih kecil daripada jumlah klaim cuti tunda.')
    available = CheckCuti().cek_sisa_cuti(riwayat.pegawai)
    if change.lama_cuti_baru > available + (riwayat.lama_cuti or 0):
        raise ValidationError('Saldo cuti berubah dan tidak lagi mencukupi jadwal baru.')


def _normalize_duration(change, riwayat):
    if riwayat.jenis_cuti == CheckCuti.CUTI_TAHUNAN:
        try:
            pola = get_pola_kerja_aktif(
                riwayat.pegawai, change.tanggal_mulai_baru,
            )
        except PolaKerjaTidakDitemukan as exc:
            raise ValidationError(
                'Pola kerja pegawai belum ditentukan pada tanggal mulai baru.'
            ) from exc
        duration = hitung_lama_cuti_tahunan(
            change.tanggal_mulai_baru,
            change.tanggal_akhir_baru,
            pola.pola_kerja,
        )
    else:
        duration = (change.tanggal_akhir_baru - change.tanggal_mulai_baru).days + 1
    if duration <= 0:
        raise ValidationError('Rentang perubahan tidak memiliki hari cuti yang terhitung.')
    if change.lama_cuti_baru != duration:
        change.lama_cuti_baru = duration
        change.save(update_fields=('lama_cuti_baru', 'updated_at'))


def _reset_verification(verifikasi):
    if verifikasi is None:
        return
    fields = []
    for level in (1, 2, 3):
        setattr(verifikasi, f'keputusan{level}', 'belum')
        setattr(verifikasi, f'catatan{level}', '')
        setattr(verifikasi, f'diputuskan_pada{level}', None)
        fields.extend((f'keputusan{level}', f'catatan{level}', f'diputuskan_pada{level}'))
    verifikasi.tanggal = None
    fields.extend(('tanggal', 'updated_at'))
    verifikasi.save(update_fields=fields)


def _prepare_delegation(pelimpahan, change):
    pelimpahan.tgl_mulai = change.tanggal_mulai_baru
    pelimpahan.tgl_selesai = change.tanggal_akhir_baru
    pelimpahan.status = 'menunggu_penerima'
    pelimpahan.persetujuan_penerima = 'belum'
    pelimpahan.catatan_penerima = ''
    if pelimpahan.requires_atasan_approval():
        pelimpahan.persetujuan_atasan = 'belum'
    else:
        pelimpahan.persetujuan_atasan = 'disetujui'
    pelimpahan.catatan_atasan = ''
    pelimpahan.save()


def _apply_dates(change, riwayat):
    riwayat.tgl_mulai_cuti = change.tanggal_mulai_baru
    riwayat.tgl_akhir_cuti = change.tanggal_akhir_baru
    riwayat.lama_cuti = change.lama_cuti_baru
    riwayat.save(update_fields=('tgl_mulai_cuti', 'tgl_akhir_cuti', 'lama_cuti', 'updated_at'))
    change.status = 'diterapkan'
    change.diterapkan_pada = timezone.now()
    change.save(update_fields=('status', 'diterapkan_pada', 'updated_at'))


@transaction.atomic
def apply_nonfinal_change(change_id):
    change = PerubahanJadwalCuti.objects.select_for_update().select_related(
        'riwayat_cuti__pegawai', 'riwayat_cuti__usulan'
    ).get(pk=change_id)
    riwayat = RiwayatCuti.objects.select_for_update().get(pk=change.riwayat_cuti_id)
    Users.objects.select_for_update().get(pk=riwayat.pegawai_id)
    _normalize_duration(change, riwayat)
    _validate_capacity(change, riwayat)

    verifikasi = VerifikasiCuti.objects.filter(layanan_cuti=riwayat.usulan).first()
    pelimpahan = PelimpahanTugas.objects.filter(riwayat_cuti=riwayat).first()
    change.snapshot_verifikasi = snapshot_verification(verifikasi)
    change.snapshot_pelimpahan = snapshot_delegation(pelimpahan)
    change.save(update_fields=('snapshot_verifikasi', 'snapshot_pelimpahan', 'updated_at'))

    if change.jenis_perubahan == 'revisi_proses':
        _reset_verification(verifikasi)

    riwayat.usulan.status = 'pengajuan'
    riwayat.usulan.save(update_fields=('status', 'updated_at'))
    riwayat.status_cuti = 'Belum'
    riwayat.save(update_fields=('status_cuti', 'updated_at'))

    if pelimpahan:
        _prepare_delegation(pelimpahan, change)
    _apply_dates(change, riwayat)
    return change


@transaction.atomic
def approve_final_change(change_id):
    change = PerubahanJadwalCuti.objects.select_for_update().select_related(
        'riwayat_cuti__pegawai', 'riwayat_cuti__usulan'
    ).get(pk=change_id)
    if change.status != 'menunggu_verifikasi':
        return change
    riwayat = RiwayatCuti.objects.select_for_update().get(pk=change.riwayat_cuti_id)
    Users.objects.select_for_update().get(pk=riwayat.pegawai_id)
    _normalize_duration(change, riwayat)
    _validate_capacity(change, riwayat)
    pelimpahan = PelimpahanTugas.objects.select_for_update().filter(
        riwayat_cuti=riwayat
    ).first()
    if riwayat.jenis_cuti == CheckCuti.CUTI_TAHUNAN:
        if pelimpahan is None:
            raise ValidationError('Pelimpahan tugas cuti tahunan tidak ditemukan.')
        change.snapshot_pelimpahan = snapshot_delegation(pelimpahan)
        change.status = 'menunggu_pelimpahan'
        change.save(update_fields=('snapshot_pelimpahan', 'status', 'updated_at'))
        _prepare_delegation(pelimpahan, change)
    else:
        _apply_dates(change, riwayat)
    return change


@transaction.atomic
def finalize_pending_schedule_change(pelimpahan_id):
    pelimpahan = PelimpahanTugas.objects.select_for_update().select_related(
        'riwayat_cuti'
    ).get(pk=pelimpahan_id)
    if not pelimpahan.is_final_approved():
        return None
    change = PerubahanJadwalCuti.objects.select_for_update().filter(
        riwayat_cuti=pelimpahan.riwayat_cuti,
        status='menunggu_pelimpahan',
    ).first()
    if not change:
        return None
    _apply_dates(change, pelimpahan.riwayat_cuti)
    return change


@transaction.atomic
def reject_pending_schedule_change(pelimpahan_id):
    pelimpahan = PelimpahanTugas.objects.select_for_update().get(pk=pelimpahan_id)
    change = PerubahanJadwalCuti.objects.select_for_update().filter(
        riwayat_cuti=pelimpahan.riwayat_cuti,
        status='menunggu_pelimpahan',
    ).first()
    if not change:
        return None
    snapshot = change.snapshot_pelimpahan or {}
    if snapshot:
        pelimpahan.tgl_mulai = _date_from_iso(snapshot.get('tgl_mulai'))
        pelimpahan.tgl_selesai = _date_from_iso(snapshot.get('tgl_selesai'))
        pelimpahan.status = snapshot.get('status', 'disetujui')
        pelimpahan.persetujuan_penerima = snapshot.get('persetujuan_penerima', 'disetujui')
        pelimpahan.catatan_penerima = snapshot.get('catatan_penerima', '')
        pelimpahan.atasan_penyetuju_id = snapshot.get('atasan_penyetuju_id')
        pelimpahan.persetujuan_atasan = snapshot.get('persetujuan_atasan', 'disetujui')
        pelimpahan.catatan_atasan = snapshot.get('catatan_atasan', '')
        pelimpahan.butuh_persetujuan_atasan = snapshot.get('butuh_persetujuan_atasan')
        pelimpahan.save()
    change.status = 'ditolak'
    change.save(update_fields=('status', 'updated_at'))
    return change


@transaction.atomic
def cancel_schedule_change(change_id):
    initial = PerubahanJadwalCuti.objects.select_related(
        'riwayat_cuti'
    ).get(pk=change_id)
    pelimpahan = None
    if initial.status == 'menunggu_pelimpahan':
        pelimpahan = PelimpahanTugas.objects.select_for_update().filter(
            riwayat_cuti=initial.riwayat_cuti
        ).first()
    change = PerubahanJadwalCuti.objects.select_for_update().select_related(
        'riwayat_cuti'
    ).get(pk=change_id)
    if change.status == 'menunggu_pelimpahan':
        if pelimpahan:
            reject_pending_schedule_change(pelimpahan.pk)
            change.refresh_from_db()
    if change.status not in ('menunggu_verifikasi', 'ditolak'):
        raise ValidationError('Perubahan jadwal ini tidak dapat dibatalkan.')
    change.status = 'dibatalkan'
    change.save(update_fields=('status', 'updated_at'))
    return change
