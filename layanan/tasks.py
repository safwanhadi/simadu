from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from dokumen.models import RiwayatCuti


STATUS_PELAKSANAAN_BERDASARKAN_TANGGAL = (
    'Belum',
    'Berlangsung',
    'Selesai',
)


def sync_status_pelaksanaan_cuti(pada=None):
    """
    Sinkronkan status pelaksanaan berdasarkan periode cuti.

    Hanya cuti yang pengajuannya sudah disetujui/selesai dan riwayat manual
    tanpa pengajuan yang diproses. Cuti yang masih diajukan/diverifikasi, ditunda,
    atau dibatalkan tidak diubah oleh scheduler.
    """
    if pada is None:
        sekarang = timezone.now()
        tanggal = (
            timezone.localtime(sekarang).date()
            if timezone.is_aware(sekarang)
            else sekarang.date()
        )
    else:
        tanggal = pada
    eligible = (
        RiwayatCuti.objects
        .filter(
            status_cuti__in=STATUS_PELAKSANAAN_BERDASARKAN_TANGGAL,
            tgl_mulai_cuti__isnull=False,
            tgl_akhir_cuti__isnull=False,
        )
        .filter(Q(usulan__status__in=('disetujui', 'selesai')) | Q(usulan__isnull=True))
    )

    with transaction.atomic():
        menjadi_belum = (
            eligible
            .filter(tgl_mulai_cuti__gt=tanggal)
            .exclude(status_cuti='Belum')
            .update(status_cuti='Belum')
        )
        menjadi_berlangsung = (
            eligible
            .filter(
                tgl_mulai_cuti__lte=tanggal,
                tgl_akhir_cuti__gte=tanggal,
            )
            .exclude(status_cuti='Berlangsung')
            .update(status_cuti='Berlangsung')
        )
        menjadi_selesai = (
            eligible
            .filter(tgl_akhir_cuti__lt=tanggal)
            .exclude(status_cuti='Selesai')
            .update(status_cuti='Selesai')
        )

    hasil = {
        'tanggal': tanggal.isoformat(),
        'menjadi_belum': menjadi_belum,
        'menjadi_berlangsung': menjadi_berlangsung,
        'menjadi_selesai': menjadi_selesai,
        'total_diubah': menjadi_belum + menjadi_berlangsung + menjadi_selesai,
    }
    return hasil
