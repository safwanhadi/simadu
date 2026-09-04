"""Aturan akses terpusat untuk data dan dokumen cuti."""

from django.db.models import Q

from dokumen.models import RiwayatPenempatan
from myaccount.admin_scopes import (
    PLACEMENT_SCOPE_LOOKUPS,
    active_admin_scopes,
    filter_queryset_by_admin_scope,
    filter_users_by_admin_scope,
    has_admin_scope_for_employee,
)
from myaccount.roles import ADMIN_LAYANAN_CUTI
from myaccount.models import CoordinationAssignment
from .base import RoleScopeAccess
from strukturorg.models import PejabatStruktur
from strukturorg.services import (
    get_active_leader,
    get_active_title,
    is_active_leader,
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
    from ..models import VerifikasiCuti

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
    from ..models import VerifikasiDiklat

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


def is_leave_admin(user, pegawai=None):
    """Role Admin Cuti harus memiliki assignment yang mencakup pegawai."""
    return _leave_access.is_admin(user, pegawai)


def filter_queryset_for_leave_admin(queryset, user, *, employee_path='pegawai'):
    return _leave_access.filter_queryset(
        queryset,
        user,
        employee_path=employee_path,
        include_self=False,
        include_subordinates=False,
    )


def filter_users_for_leave_admin(queryset, user):
    return _leave_access.filter_queryset(
        queryset,
        user,
        employee_path='',
        include_self=False,
        include_subordinates=False,
    )


def filter_users_for_leave_supervisor(queryset, user):
    return filter_queryset_for_leave_supervisor(
        queryset,
        user,
        employee_path='',
    )


def _is_structural_officer(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    return PejabatStruktur.objects.filter(
        pejabat=user,
        pejabat__is_active=True,
        is_active=True,
    ).exists() or CoordinationAssignment.objects.filter(
        coordinator=user,
        employee__is_active=True,
        is_active=True,
    ).exists()


def is_leave_structural_officer(user):
    return _leave_access.is_structural_officer(user)


def filter_users_for_leave_role(queryset, user, *, include_self=True):
    return _leave_access.filter_users(
        queryset, user, include_self=include_self
    )


def filter_cuti_history_queryset(queryset, user):
    """Riwayat pribadi, assignment Admin Cuti, dan bawahan struktural."""
    return _leave_access.filter_queryset(queryset, user)


def can_manage_cuti_history(user, riwayat_cuti):
    return _leave_access.can_access(user, riwayat_cuti)


def _appointment_scope_filter(appointments, placement_path):
    scope_query = Q()
    for appointment in appointments:
        for field_name in PejabatStruktur.TARGET_FIELDS:
            target_id = appointment.get(f'{field_name}_id')
            if target_id is None:
                continue
            for lookup in PLACEMENT_SCOPE_LOOKUPS.get(field_name, ()):
                scope_query |= Q(**{f'{placement_path}__{lookup}': target_id})
            break
    return scope_query


def filter_queryset_for_leave_supervisor(queryset, user, *, employee_path='pegawai'):
    """Data bawahan berdasarkan penugasan struktural aktif, tanpa ProfilAdmin."""
    if not getattr(user, 'is_active', False):
        return queryset.none()
    appointments = PejabatStruktur.objects.filter(
        pejabat=user,
        pejabat__is_active=True,
        is_active=True,
    ).values(*(f'{field_name}_id' for field_name in PejabatStruktur.TARGET_FIELDS))
    placement_path = (
        f'{employee_path}__riwayat_penempatan'
        if employee_path else 'riwayat_penempatan'
    )
    scope_query = _appointment_scope_filter(appointments, placement_path)
    direct_employee_ids = CoordinationAssignment.objects.filter(
        coordinator=user,
        coordinator__is_active=True,
        employee__is_active=True,
        is_active=True,
    ).values('employee_id')
    direct_lookup = f'{employee_path}__in' if employee_path else 'pk__in'
    direct_query = Q(**{direct_lookup: direct_employee_ids})
    structural_query = Q()
    if scope_query:
        structural_query = scope_query & Q(**{f'{placement_path}__status': True})
    scoped = queryset.filter(structural_query | direct_query)
    if employee_path:
        scoped = scoped.exclude(**{employee_path: user})
    else:
        scoped = scoped.exclude(pk=user.pk)
    return scoped.distinct()


def can_supervise_employee(user, pegawai):
    """Samakan akses detail dengan lingkup bawahan pada halaman daftar."""
    if (
        not getattr(user, 'is_authenticated', False)
        or not getattr(user, 'is_active', False)
        or user.pk == getattr(pegawai, 'pk', None)
    ):
        return False

    if CoordinationAssignment.objects.filter(
        coordinator=user,
        employee=pegawai,
        is_active=True,
        coordinator__is_active=True,
        employee__is_active=True,
    ).exists():
        return True

    penempatan = get_active_placement(pegawai)
    if penempatan is None:
        return False

    structures = [
        penempatan.penempatan_level4,
        penempatan.penempatan_level3,
        penempatan.penempatan_level2,
        penempatan.penempatan_level1,
    ]
    if penempatan.penempatan_level4:
        structures.extend([
            penempatan.penempatan_level4.sub_bidang,
            penempatan.penempatan_level4.sub_bidang.bidang,
            penempatan.penempatan_level4.sub_bidang.bidang.unor,
        ])
    elif penempatan.penempatan_level3:
        structures.extend([
            penempatan.penempatan_level3.bidang,
            penempatan.penempatan_level3.bidang.unor,
        ])
    elif penempatan.penempatan_level2:
        structures.append(penempatan.penempatan_level2.unor)
    return any(
        structure is not None and is_active_leader(user, structure)
        for structure in structures
    )


_leave_access = RoleScopeAccess(
    ADMIN_LAYANAN_CUTI,
    filter_queryset_for_leave_supervisor,
    can_supervise_employee,
    _is_structural_officer,
)


def can_view_leave(user, layanan_cuti):
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return False
    return bool(
        user.pk == layanan_cuti.pegawai_id
        or is_leave_admin(user, layanan_cuti.pegawai)
        or is_leave_approver(user, layanan_cuti)
        or can_supervise_employee(user, layanan_cuti.pegawai)
    )


def can_view_delegation(user, pelimpahan):
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return False
    return bool(
        is_leave_admin(user, pelimpahan.riwayat_cuti.pegawai)
        or user.pk in {
            pelimpahan.pemberi_tugas_id,
            pelimpahan.penerima_tugas_id,
            pelimpahan.atasan_penyetuju_id,
        }
        or can_view_leave(user, pelimpahan.riwayat_cuti.usulan)
    )
