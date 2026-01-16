# utils/jabatan.py (atau taruh di views.py)
from __future__ import annotations

from typing import Optional, Tuple
from datetime import date

from django.db.models import QuerySet

from dokumen.models import RiwayatJabatan  # sesuaikan import


def _get_last_riwayat_jabatan(pegawai) -> Optional[RiwayatJabatan]:
    if not pegawai:
        return None

    return (
        RiwayatJabatan.objects
        .filter(pegawai=pegawai)
        .select_related(
            "nama_jabatan",
            "jenjang_jabatan",
            "unor",
            "bidang",
            "sub_bidang",
            "instalasi",
            # (opsional) kalau mau akses satker_induk via unor:
            "unor__satker_induk",
        )
        .order_by(
            "-tmt_jabatan",
            "-tmt_pelantikan",
            "-updated_at",
            "-created_at",
            "-id",
        )
        .first()
    )


def _build_jabatan_from_riwayat(rj: RiwayatJabatan) -> str:
    # Prioritas 1: profesi
    profesi = None
    if rj.nama_jabatan and rj.nama_jabatan.profesi:
        profesi = str(rj.nama_jabatan.profesi)  # ProfesiSDM.__str__()

    base = profesi or (rj.nama_jabatan.jenis_sdm if rj.nama_jabatan else "-")

    # detail opsional (kalau suatu saat Anda isi)
    if rj.detail_nama_jabatan:
        base = f"{base} ({rj.detail_nama_jabatan})"

    # jenjang opsional
    if rj.jenjang_jabatan:
        base = f"{base} - {rj.jenjang_jabatan}"

    return base


def _get_unit_label_unor(rj: RiwayatJabatan) -> Optional[str]:
    return rj.unor.unor if rj.unor else None


def _get_unit_label_bidang(rj: RiwayatJabatan) -> Optional[str]:
    return rj.bidang.bidang if rj.bidang else None


def _get_unit_label_subbidang(rj: RiwayatJabatan) -> Optional[str]:
    return rj.sub_bidang.sub_bidang if rj.sub_bidang else None


def _get_unit_label_instalasi(rj: RiwayatJabatan) -> Optional[str]:
    # ambil nama instalasi saja (bukan __str__ yang mengandung subbidang)
    return rj.instalasi.instalasi if rj.instalasi else None


def _build_unit_top_only(rj: RiwayatJabatan) -> str:
    """
    Untuk surat: tampilkan unit tertinggi yang tersedia sesuai hirarki:
    UNOR > Bidang > SubBidang > Instalasi
    """
    return (
        _get_unit_label_unor(rj)
        or _get_unit_label_bidang(rj)
        or _get_unit_label_subbidang(rj)
        or _get_unit_label_instalasi(rj)
        or "-"
    )


def _build_unit_hierarchy_full(rj: RiwayatJabatan, include_satker: bool = False) -> str:
    """
    Tampilkan hirarki lengkap: (opsional) Satker Induk → UNOR → Bidang → SubBidang → Instalasi
    Aman dari duplikasi karena kita pakai field mentah, bukan __str__ instalasi.
    """
    parts = []

    if include_satker and rj.unor and getattr(rj.unor, "satker_induk", None):
        parts.append(str(rj.unor.satker_induk))  # SatkerInduk.__str__ => satuan_kerja

    unor = _get_unit_label_unor(rj)
    bidang = _get_unit_label_bidang(rj)
    subbidang = _get_unit_label_subbidang(rj)
    instalasi = _get_unit_label_instalasi(rj)

    for p in (unor, bidang, subbidang, instalasi):
        if p:
            parts.append(p)

    return " - ".join(parts) if parts else "-"


def get_jabatan_unit(pegawai, mode: str = "top") -> Tuple[str, str]:
    """
    mode:
    - "top"  : hanya unit tertinggi (default, cocok untuk surat)
    - "full" : hirarki lengkap (UNOR-Bidang-SubBidang-Instalasi)
    """
    rj = _get_last_riwayat_jabatan(pegawai)
    if not rj:
        return ("-", "-")

    jabatan = _build_jabatan_from_riwayat(rj)

    if mode == "full":
        unit = _build_unit_hierarchy_full(rj, include_satker=False)
    else:
        unit = _build_unit_top_only(rj)

    return jabatan, unit
