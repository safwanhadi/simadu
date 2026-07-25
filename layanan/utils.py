from strukturorg.services import get_active_leader, get_active_title


def get_nip(user) -> str:
    profil = getattr(user, "profil_user", None)
    return getattr(profil, "nip", None) or "-"


def get_rp_aktif(user):
    qs = getattr(user, "riwayat_penempatan", None)
    if not qs:
        return None
    return qs.filter(status=True).order_by("-updated_at", "-id").first()


def get_jabatan_unit(user) -> tuple[str, str]:
    """
    Unit: pakai rp.penempatan (property Anda)
    Jabatan: default 'Pegawai' (bisa Anda tingkatkan sesuai kebutuhan)
    """
    rp = get_rp_aktif(user)
    if not rp:
        return ("Pegawai", "N/A")

    unit = rp.penempatan or "N/A"
    jabatan = "Pegawai"

    obj, level = rp._penempatan_aktif  # property Anda
    try:
        if level == "level4" and obj and get_active_leader(obj) == user:
            jabatan = f'{get_active_title(obj) or "Kepala Instalasi"} {getattr(obj, "instalasi", "")}'
        elif level == "level3" and obj and get_active_leader(obj) == user:
            jabatan = f'{get_active_title(obj) or "Kepala Seksi/Subbag"} {getattr(obj, "sub_bidang", "")}'
        elif level == "level2" and obj and get_active_leader(obj) == user:
            jabatan = f'{get_active_title(obj) or "Kepala Bidang"} {getattr(obj, "bidang", "")}'
        elif level == "level1" and obj and get_active_leader(obj) == user:
            jabatan = f'{get_active_title(obj) or "Kepala Unit Organisasi"} {getattr(obj, "unor", "")}'
    except Exception:
        pass

    return (jabatan, unit)


def resolve_atasan_level3_for_level4(user):
    """
    Jika user penempatan aktif level4 => atasan aktif pada struktur level4.
    """
    rp = get_rp_aktif(user)
    if not rp:
        return None
    obj, level = rp._penempatan_aktif
    if level == "level4" and obj:
        return get_active_leader(obj)
    return None
