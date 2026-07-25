"""Aturan akses terpusat untuk data dan dokumen cuti."""

from dokumen.models import RiwayatPenempatan
from strukturorg.services import (
    filter_structures_led_by,
    get_active_leader,
    get_active_title,
)


def get_active_placement(pegawai):
    return (
        RiwayatPenempatan.objects.filter(pegawai=pegawai, status=True)
        .select_related(
            "penempatan_level1__satker_induk__instansi_daerah",
            "penempatan_level2__unor__satker_induk__instansi_daerah",
            "penempatan_level3__bidang__unor__satker_induk__instansi_daerah",
            "penempatan_level4__sub_bidang__bidang__unor__satker_induk__instansi_daerah",
        )
        .order_by("-updated_at", "-id")
        .first()
    )


def build_approval_chain(pegawai):
    """Menghasilkan rantai verifikator yang aman dari relasi struktur kosong."""
    rp = get_active_placement(pegawai)
    if not rp:
        return []

    chain = []

    def add(level, obj, name_attr):
        if obj is None:
            chain.append({"level": level, "user": None, "label": "Struktur belum lengkap"})
            return
        name = getattr(obj, name_attr, "") or ""
        prefix = get_active_title(obj)
        chain.append({
            "level": level,
            "user": get_active_leader(obj),
            "label": f"{prefix} {name}".strip(),
        })

    if rp.penempatan_level4_id:
        instalasi = rp.penempatan_level4
        sub_bidang = getattr(instalasi, "sub_bidang", None)
        bidang = getattr(sub_bidang, "bidang", None)
        unor = getattr(bidang, "unor", None)
        add(1, sub_bidang, "sub_bidang")
        add(2, bidang, "bidang")
        add(3, unor, "unor")
    elif rp.penempatan_level3_id:
        sub_bidang = rp.penempatan_level3
        bidang = getattr(sub_bidang, "bidang", None)
        unor = getattr(bidang, "unor", None)
        add(1, bidang, "bidang")
        add(2, unor, "unor")
    elif rp.penempatan_level2_id:
        bidang = rp.penempatan_level2
        unor = getattr(bidang, "unor", None)
        satker = getattr(unor, "satker_induk", None)
        add(1, unor, "unor")
        add(2, satker, "satuan_kerja")
    elif rp.penempatan_level1_id:
        unor = rp.penempatan_level1
        satker = getattr(unor, "satker_induk", None)
        instansi = getattr(satker, "instansi_daerah", None)
        add(1, satker, "satuan_kerja")
        add(2, instansi, "instansi")

    return chain


def ensure_leave_verifier_snapshot(layanan_cuti):
    """Simpan pejabat aktif saat pengajuan dibuat, bukan saat diverifikasi."""
    from .models import VerifikasiCuti

    defaults = {
        f"verifikator{item['level']}": item['user']
        for item in build_approval_chain(layanan_cuti.pegawai)
        if item['user'] is not None
    }
    snapshot, created = VerifikasiCuti.objects.get_or_create(
        layanan_cuti=layanan_cuti,
        defaults=defaults,
    )
    # Data lama mungkin sudah mempunyai record kosong. Isi hanya slot kosong;
    # pejabat yang sudah tersimpan tidak pernah ditimpa oleh mutasi berikutnya.
    if not created:
        changed = []
        for field_name, verifier in defaults.items():
            if getattr(snapshot, field_name) is None:
                setattr(snapshot, field_name, verifier)
                changed.append(field_name)
        if changed:
            snapshot.save(update_fields=changed + ['updated_at'])
    return snapshot


def ensure_diklat_verifier_snapshot(layanan_diklat, pegawai):
    """Bekukan pejabat verifikator diklat pada saat usulan dikirim."""
    from .models import VerifikasiDiklat

    defaults = {
        f"verifikator{item['level']}": item['user']
        for item in build_approval_chain(pegawai)
        if item['user'] is not None
    }
    snapshot, created = VerifikasiDiklat.objects.get_or_create(
        layanan_diklat=layanan_diklat,
        defaults=defaults,
    )
    if not created:
        changed = []
        for field_name, verifier in defaults.items():
            if getattr(snapshot, field_name) is None:
                setattr(snapshot, field_name, verifier)
                changed.append(field_name)
        if changed:
            snapshot.save(update_fields=changed + ['updated_at'])
    return snapshot


def is_leave_approver(user, layanan_cuti):
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return False
    snapshot = getattr(layanan_cuti, 'verifikasicuti', None)
    if snapshot and user.pk in {
        snapshot.verifikator1_id,
        snapshot.verifikator2_id,
        snapshot.verifikator3_id,
    }:
        return True
    return any(
        item["user"] is not None and item["user"].pk == user.pk
        for item in build_approval_chain(layanan_cuti.pegawai)
    )


def can_supervise_employee(user, pegawai):
    """Samakan akses detail dengan lingkup bawahan pada halaman daftar."""
    if (
        not getattr(user, 'is_authenticated', False)
        or not getattr(user, 'is_active', False)
        or user.pk == getattr(pegawai, 'pk', None)
    ):
        return False

    profil_admin = getattr(user, 'profil_admin', None)
    if profil_admin is None:
        return False
    penempatan = get_active_placement(pegawai)
    if penempatan is None:
        return False

    instalasi = filter_structures_led_by(profil_admin.instalasi.all(), user)
    if (
        penempatan.penempatan_level4_id
        and instalasi.filter(pk=penempatan.penempatan_level4_id).exists()
    ):
        return True

    sub_bidang = filter_structures_led_by(profil_admin.sub_bidang.all(), user)
    sub_bidang_id = (
        penempatan.penempatan_level3_id
        or getattr(
            getattr(penempatan, 'penempatan_level4', None),
            'sub_bidang_id',
            None,
        )
    )
    if sub_bidang_id and sub_bidang.filter(pk=sub_bidang_id).exists():
        return True

    bidang = filter_structures_led_by(profil_admin.bidang.all(), user)
    bidang_id = penempatan.penempatan_level2_id
    if not bidang_id:
        sub_bidang_obj = (
            getattr(penempatan, 'penempatan_level3', None)
            or getattr(
                getattr(penempatan, 'penempatan_level4', None),
                'sub_bidang',
                None,
            )
        )
        bidang_id = getattr(sub_bidang_obj, 'bidang_id', None)
    if bidang_id and bidang.filter(pk=bidang_id).exists():
        return True

    unor = filter_structures_led_by(profil_admin.unor.all(), user)
    unor_id = penempatan.penempatan_level1_id
    if not unor_id:
        bidang_obj = getattr(penempatan, 'penempatan_level2', None)
        if bidang_obj is None:
            sub_bidang_obj = (
                getattr(penempatan, 'penempatan_level3', None)
                or getattr(
                    getattr(penempatan, 'penempatan_level4', None),
                    'sub_bidang',
                    None,
                )
            )
            bidang_obj = getattr(sub_bidang_obj, 'bidang', None)
        unor_id = getattr(bidang_obj, 'unor_id', None)
    return bool(unor_id and unor.filter(pk=unor_id).exists())


def can_view_leave(user, layanan_cuti):
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return False
    return bool(
        user.pk == layanan_cuti.pegawai_id
        or user.is_cuti_admin
        or is_leave_approver(user, layanan_cuti)
        or can_supervise_employee(user, layanan_cuti.pegawai)
    )


def can_view_delegation(user, pelimpahan):
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return False
    return bool(
        user.is_cuti_admin
        or user.pk in {
            pelimpahan.pemberi_tugas_id,
            pelimpahan.penerima_tugas_id,
            pelimpahan.atasan_penyetuju_id,
        }
        or can_view_leave(user, pelimpahan.riwayat_cuti.usulan)
    )
