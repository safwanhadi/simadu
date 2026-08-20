"""Aturan akses terpusat untuk modul disiplin SDM."""

from django.db.models import Q

from myaccount.admin_scopes import (
    PLACEMENT_SCOPE_LOOKUPS,
    _structure_lineage,
    active_admin_scopes,
    filter_queryset_by_admin_scope,
    filter_users_by_admin_scope,
    has_admin_scope,
    has_admin_scope_for_employee,
)
from myaccount.models import AdminScopeAssignment
from myaccount.roles import ADMIN_DISIPLIN
from strukturorg.models import PejabatStruktur


def is_discipline_admin(user, *, employee=None, structure=None):
    """Role Admin Disiplin wajib mempunyai assignment yang sesuai."""
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_active', False) and getattr(user, 'is_superuser', False):
        return True
    if employee is not None:
        return has_admin_scope_for_employee(user, ADMIN_DISIPLIN, employee)
    if structure is not None:
        return has_admin_scope(user, ADMIN_DISIPLIN, structure)
    return active_admin_scopes(user, ADMIN_DISIPLIN).exists()


def filter_queryset_for_discipline_admin(
    queryset,
    user,
    *,
    employee_path='pegawai',
):
    """Batasi queryset disiplin melalui penempatan aktif pegawai."""
    return filter_queryset_by_admin_scope(
        queryset,
        user,
        ADMIN_DISIPLIN,
        employee_path=employee_path,
    )


def filter_users_for_discipline_admin(queryset, user):
    return filter_users_by_admin_scope(queryset, user, ADMIN_DISIPLIN)


def filter_installations_for_discipline_admin(queryset, user):
    """Batasi UnitInstalasi berdasarkan assignment pada semua tingkat induk."""
    if (
        getattr(user, 'is_active', False)
        and getattr(user, 'is_superuser', False)
    ):
        return queryset

    assignments = active_admin_scopes(user, ADMIN_DISIPLIN)
    if not assignments.exists():
        return queryset.none()
    if assignments.filter(scope_type=AdminScopeAssignment.GLOBAL).exists():
        return queryset

    scope_query = Q()
    for assignment in assignments:
        target_id = getattr(assignment, f'{assignment.scope_type}_id', None)
        if assignment.scope_type == AdminScopeAssignment.INSTANSI_DAERAH:
            scope_query |= Q(
                sub_bidang__bidang__unor__satker_induk__instansi_daerah_id=target_id
            )
        elif assignment.scope_type == AdminScopeAssignment.SATUAN_KERJA_INDUK:
            scope_query |= Q(
                sub_bidang__bidang__unor__satker_induk_id=target_id
            )
        elif assignment.scope_type == AdminScopeAssignment.UNIT_ORGANISASI:
            scope_query |= Q(sub_bidang__bidang__unor_id=target_id)
        elif assignment.scope_type == AdminScopeAssignment.BIDANG:
            scope_query |= Q(sub_bidang__bidang_id=target_id)
        elif assignment.scope_type == AdminScopeAssignment.SUB_BIDANG:
            scope_query |= Q(sub_bidang_id=target_id)
        elif assignment.scope_type == AdminScopeAssignment.UNIT_INSTALASI:
            scope_query |= Q(pk=target_id)
    return queryset.filter(scope_query).distinct()


def active_structural_appointments(user):
    """Penugasan struktural aktif milik pengguna."""
    if not getattr(user, 'is_active', False):
        return PejabatStruktur.objects.none()
    return PejabatStruktur.objects.filter(
        pejabat=user,
        pejabat__is_active=True,
        is_active=True,
    )


def is_discipline_structural_officer(
    user,
    *,
    employee=None,
    structure=None,
    allowed_levels=None,
):
    """Periksa kewenangan pejabat terhadap struktur/pegawai tertentu."""
    if not getattr(user, 'is_authenticated', False):
        return False
    appointments = active_structural_appointments(user)
    if allowed_levels:
        level_query = Q()
        for field_name in allowed_levels:
            level_query |= Q(**{f'{field_name}__isnull': False})
        appointments = appointments.filter(level_query)
    if employee is not None:
        from myaccount.admin_scopes import get_employee_scope_structure

        structure = get_employee_scope_structure(employee)
        if structure is None:
            return False
    if structure is None:
        return appointments.exists()

    lineage = _structure_lineage(structure)
    for appointment in appointments:
        field_name = appointment.target_field_name
        if (
            field_name
            and lineage.get(field_name)
            == getattr(appointment, f'{field_name}_id')
        ):
            return True
    return False


def can_approve_discipline_schedule(user, employee):
    """Persetujuan individual adalah kewenangan Kepala Ruangan terkait."""
    return bool(
        is_discipline_admin(user, employee=employee)
        or is_discipline_structural_officer(
            user,
            employee=employee,
            allowed_levels={'unit_instalasi'},
        )
    )


def can_approve_discipline_installation(user, installation):
    """Approval instalasi: admin scoped atau Kepala Ruangan terkait."""
    return bool(
        is_discipline_admin(user, structure=installation)
        or is_discipline_structural_officer(
            user,
            structure=installation,
            allowed_levels={'unit_instalasi'},
        )
    )


def _structural_scope_query(user, placement_path):
    scope_query = Q()
    appointments = active_structural_appointments(user).values(
        *(f'{field_name}_id' for field_name in PejabatStruktur.TARGET_FIELDS)
    )
    for appointment in appointments:
        for field_name in PejabatStruktur.TARGET_FIELDS:
            target_id = appointment.get(f'{field_name}_id')
            if target_id is None:
                continue
            for lookup in PLACEMENT_SCOPE_LOOKUPS.get(field_name, ()):
                scope_query |= Q(**{f'{placement_path}__{lookup}': target_id})
            break
    return scope_query


def filter_queryset_for_structural_officer(
    queryset,
    user,
    *,
    employee_path='pegawai',
):
    """Batasi data ke pegawai pada struktur yang dipimpin."""
    placement_path = (
        f'{employee_path}__riwayat_penempatan'
        if employee_path else 'riwayat_penempatan'
    )
    scope_query = _structural_scope_query(user, placement_path)
    if not scope_query:
        return queryset.none()
    return queryset.filter(
        scope_query,
        **{f'{placement_path}__status': True},
    ).distinct()


def filter_users_for_structural_officer(queryset, user):
    return filter_queryset_for_structural_officer(
        queryset,
        user,
        employee_path='',
    )


def filter_installations_for_structural_officer(queryset, user):
    """Unit instalasi di bawah seluruh simpul yang sedang dipimpin."""
    scope_query = Q()
    for appointment in active_structural_appointments(user):
        field_name = appointment.target_field_name
        target_id = getattr(appointment, f'{field_name}_id', None)
        if field_name == 'instansi_daerah':
            scope_query |= Q(
                sub_bidang__bidang__unor__satker_induk__instansi_daerah_id=target_id
            )
        elif field_name == 'satuan_kerja_induk':
            scope_query |= Q(
                sub_bidang__bidang__unor__satker_induk_id=target_id
            )
        elif field_name == 'unit_organisasi':
            scope_query |= Q(sub_bidang__bidang__unor_id=target_id)
        elif field_name == 'bidang':
            scope_query |= Q(sub_bidang__bidang_id=target_id)
        elif field_name == 'sub_bidang':
            scope_query |= Q(sub_bidang_id=target_id)
        elif field_name == 'unit_instalasi':
            scope_query |= Q(pk=target_id)
    if not scope_query:
        return queryset.none()
    return queryset.filter(scope_query).distinct()


def can_manage_discipline_employee(user, employee):
    return bool(
        is_discipline_admin(user, employee=employee)
        or is_discipline_structural_officer(user, employee=employee)
    )


def can_delete_discipline_schedule(user, schedule):
    """Admin dapat menghapus jadwal; pejabat hanya draft/ditolak di lingkupnya."""
    employee = getattr(schedule, 'pegawai', None)
    if employee is None:
        return False
    if is_discipline_admin(user, employee=employee):
        return True
    return bool(
        getattr(schedule, 'status', None) in {'draft', 'ditolak'}
        and is_discipline_structural_officer(user, employee=employee)
    )


def can_manage_discipline_structure(user, structure):
    return bool(
        is_discipline_admin(user, structure=structure)
        or is_discipline_structural_officer(user, structure=structure)
    )


def filter_users_for_discipline_role(queryset, user):
    """Gabungkan cakupan admin dan jabatan struktural tanpa akses global implisit."""
    admin_queryset = filter_users_for_discipline_admin(queryset, user)
    officer_queryset = filter_users_for_structural_officer(queryset, user)
    return (admin_queryset | officer_queryset).distinct()


def filter_installations_for_discipline_role(queryset, user):
    admin_queryset = filter_installations_for_discipline_admin(queryset, user)
    officer_queryset = filter_installations_for_structural_officer(queryset, user)
    return (admin_queryset | officer_queryset).distinct()
