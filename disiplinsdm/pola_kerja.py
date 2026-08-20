from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q

from .models import ApprovedJadwalDinasSDM, PolaKerjaPegawai


def tentukan_pola_kerja_jadwal(jadwal_sdm):
    """Piket mengindikasikan shift; Reguler mengindikasikan non-shift."""
    kategori = set(
        ApprovedJadwalDinasSDM.objects.filter(
            pegawai=jadwal_sdm,
            tanggal__month=jadwal_sdm.bulan,
            tanggal__year=jadwal_sdm.tahun,
            is_approved=True,
        ).values_list(
            'kategori_jadwal__kategori_dinas__kategori_dinas',
            flat=True,
        )
    )
    kategori = {(value or '').strip().lower() for value in kategori}
    if any('piket' in value for value in kategori):
        return PolaKerjaPegawai.SHIFT
    if any('reguler' in value for value in kategori):
        return PolaKerjaPegawai.REGULER
    # Jadwal yang hanya berisi Libur tidak cukup untuk menentukan pola.
    return None


@transaction.atomic
def sinkronkan_pola_kerja_dari_jadwal(jadwal_sdm):
    pola_baru = tentukan_pola_kerja_jadwal(jadwal_sdm)
    if pola_baru is None:
        return None, False

    mulai = date(jadwal_sdm.tahun, jadwal_sdm.bulan, 1)
    riwayat = PolaKerjaPegawai.objects.select_for_update().filter(
        pegawai=jadwal_sdm.pegawai,
    )
    berlaku = riwayat.filter(
        berlaku_mulai__lte=mulai,
    ).filter(
        Q(berlaku_sampai__isnull=True) | Q(berlaku_sampai__gte=mulai)
    ).order_by('-berlaku_mulai', '-pk').first()

    if berlaku and berlaku.pola_kerja == pola_baru:
        return berlaku, False

    # Persetujuan ulang pada bulan yang sama memperbarui titik perubahan itu,
    # tanpa membuat record periode yang saling tumpang tindih.
    if berlaku and berlaku.berlaku_mulai == mulai:
        berlaku.pola_kerja = pola_baru
        berlaku.keterangan = 'Sinkronisasi otomatis dari jadwal dinas disetujui.'
        berlaku.save(update_fields=('pola_kerja', 'keterangan', 'updated_at'))
        return berlaku, True

    periode_berikutnya = riwayat.filter(
        berlaku_mulai__gt=mulai,
    ).order_by('berlaku_mulai', 'pk').first()

    if berlaku:
        berlaku.berlaku_sampai = mulai - timedelta(days=1)
        berlaku.save(update_fields=('berlaku_sampai', 'updated_at'))

    pola = PolaKerjaPegawai.objects.create(
        pegawai=jadwal_sdm.pegawai,
        pola_kerja=pola_baru,
        berlaku_mulai=mulai,
        berlaku_sampai=(
            periode_berikutnya.berlaku_mulai - timedelta(days=1)
            if periode_berikutnya else None
        ),
        keterangan='Sinkronisasi otomatis dari jadwal dinas disetujui.',
    )
    return pola, True
