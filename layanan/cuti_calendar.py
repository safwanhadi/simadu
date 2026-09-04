from datetime import timedelta

from django.db.models import Q

from disiplinsdm.models import HariLibur, PolaKerjaPegawai


class PolaKerjaTidakDitemukan(Exception):
    pass


def get_pola_kerja_aktif(pegawai, pada):
    pola = (
        PolaKerjaPegawai.objects.filter(
            pegawai=pegawai,
            berlaku_mulai__lte=pada,
        )
        .filter(
            Q(berlaku_sampai__isnull=True)
            | Q(berlaku_sampai__gte=pada)
        )
        .order_by('-berlaku_mulai', '-pk')
        .first()
    )
    if pola is None:
        raise PolaKerjaTidakDitemukan
    return pola


def hitung_tanggal_akhir_cuti_tahunan(tanggal_mulai, lama_cuti, pola_kerja):
    """Hitung tanggal akhir; Ahad/libur hanya dilewati untuk pegawai reguler."""
    if lama_cuti <= 0:
        raise ValueError('Lama cuti harus lebih dari nol.')
    if pola_kerja == PolaKerjaPegawai.SHIFT:
        return tanggal_mulai + timedelta(days=lama_cuti - 1)

    tanggal = tanggal_mulai
    terhitung = 0
    while True:
        hari_libur = tanggal.weekday() == 6 or HariLibur.objects.filter(
            tanggal=tanggal
        ).exists()
        if not hari_libur:
            terhitung += 1
            if terhitung == lama_cuti:
                return tanggal
        tanggal += timedelta(days=1)


def hitung_lama_cuti_tahunan(tanggal_mulai, tanggal_akhir, pola_kerja):
    """Hitung hari yang mengurangi hak cuti dalam suatu rentang tanggal."""
    if tanggal_akhir < tanggal_mulai:
        raise ValueError('Tanggal akhir tidak boleh sebelum tanggal mulai.')
    if pola_kerja == PolaKerjaPegawai.SHIFT:
        return (tanggal_akhir - tanggal_mulai).days + 1

    hari_libur = set(HariLibur.objects.filter(
        tanggal__range=(tanggal_mulai, tanggal_akhir),
    ).values_list('tanggal', flat=True))
    tanggal = tanggal_mulai
    terhitung = 0
    while tanggal <= tanggal_akhir:
        if tanggal.weekday() != 6 and tanggal not in hari_libur:
            terhitung += 1
        tanggal += timedelta(days=1)
    return terhitung
