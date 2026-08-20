"""Aturan akses terpusat untuk layanan Diklat."""

from django.db.models import Exists, OuterRef

from myaccount.roles import ADMIN_LAYANAN_DIKLAT

from .base import RoleScopeAccess
from .cuti import (
    can_supervise_employee,
    filter_queryset_for_leave_supervisor,
    is_leave_structural_officer,
)

_access = RoleScopeAccess(
    ADMIN_LAYANAN_DIKLAT,
    filter_queryset_for_leave_supervisor,
    can_supervise_employee,
    is_leave_structural_officer,
)


def get_diklat_employees(layanan_diklat):
    if layanan_diklat is None:
        return []
    from dokumen.models import RiwayatDiklat

    return list(
        RiwayatDiklat.objects.filter(
            usulan=layanan_diklat,
            pegawai__isnull=False,
        )
        .values_list('pegawai', flat=True)
        .distinct()
    )


def is_diklat_admin(user, employee=None):
    """Role Admin Diklat wajib disertai assignment aktif."""
    return _access.is_admin(user, employee)


def is_diklat_structural_officer(user):
    return _access.is_structural_officer(user)


def can_administer_diklat(user, layanan_diklat):
    employee_ids = get_diklat_employees(layanan_diklat)
    if not employee_ids:
        return False
    from myaccount.models import Users

    employees = Users.objects.filter(pk__in=employee_ids)
    return all(is_diklat_admin(user, employee) for employee in employees)


def filter_queryset_for_diklat_admin(queryset, user):
    scoped = _access.filter_queryset(
        queryset,
        user,
        employee_path='riwayatdiklat__pegawai',
        include_self=False,
        include_subordinates=False,
    )
    allowed_users = filter_users_for_diklat_admin(
        _active_employees(),
        user,
    )
    return _exclude_proposals_with_outside_employees(
        scoped,
        allowed_users,
    )


def filter_users_for_diklat_admin(queryset, user):
    return _access.filter_queryset(
        queryset,
        user,
        employee_path='',
        include_self=False,
        include_subordinates=False,
    )


def filter_queryset_for_diklat_supervisor(queryset, user):
    scoped = filter_queryset_for_leave_supervisor(
        queryset,
        user,
        employee_path='riwayatdiklat__pegawai',
    )
    allowed_users = filter_users_for_diklat_supervisor(
        _active_employees(),
        user,
    )
    return _exclude_proposals_with_outside_employees(
        scoped,
        allowed_users,
    )


def filter_users_for_diklat_supervisor(queryset, user):
    return filter_queryset_for_leave_supervisor(
        queryset,
        user,
        employee_path='',
    )


def _active_employees():
    from myaccount.models import Users

    return Users.objects.filter(is_active=True)


def _exclude_proposals_with_outside_employees(queryset, allowed_users):
    """Usulan multi-peserta tampil hanya bila seluruh peserta ada dalam scope."""
    from myaccount.models import Users

    outside_employee = Users.objects.filter(
        riwayatdiklat__usulan_id=OuterRef('pk'),
    ).exclude(pk__in=allowed_users.values('pk'))
    return queryset.annotate(
        _has_outside_diklat_employee=Exists(outside_employee),
    ).filter(_has_outside_diklat_employee=False)


def is_diklat_supervisor(user, layanan_diklat):
    employee_ids = get_diklat_employees(layanan_diklat)
    if not employee_ids:
        return False
    from myaccount.models import Users

    employees = Users.objects.filter(pk__in=employee_ids)
    return all(can_supervise_employee(user, employee) for employee in employees)


def is_diklat_participant(user, layanan_diklat):
    return bool(
        getattr(user, 'is_authenticated', False)
        and layanan_diklat.riwayatdiklat_set.filter(pegawai=user).exists()
    )


def is_diklat_verifier(user, layanan_diklat, *, level=None):
    if not getattr(user, 'is_active', False):
        return False
    verification = getattr(layanan_diklat, 'verifikasidiklat', None)
    if verification is None:
        return False
    if level in {'1', '2', '3'}:
        return getattr(verification, f'verifikator{level}_id') == user.pk
    return user.pk in {
        verification.verifikator1_id,
        verification.verifikator2_id,
        verification.verifikator3_id,
    }


def can_view_diklat(user, layanan_diklat):
    return bool(
        is_diklat_participant(user, layanan_diklat)
        or can_administer_diklat(user, layanan_diklat)
        or is_diklat_supervisor(user, layanan_diklat)
        or is_diklat_verifier(user, layanan_diklat)
    )


def get_history_employees(riwayat_diklat):
    if riwayat_diklat is None:
        return []
    return list(
        riwayat_diklat.pegawai.filter(is_active=True)
        .values_list('pk', flat=True)
    )


def can_manage_diklat_history(user, riwayat_diklat):
    employee_ids = get_history_employees(riwayat_diklat)
    if not employee_ids:
        return False
    if user.pk in employee_ids:
        return True
    from myaccount.models import Users

    employees = Users.objects.filter(pk__in=employee_ids)
    return bool(
        all(is_diklat_admin(user, employee) for employee in employees)
        or all(can_supervise_employee(user, employee) for employee in employees)
    )


def filter_diklat_history_queryset(queryset, user):
    """Riwayat pribadi + seluruh riwayat yang lengkap berada dalam kewenangan."""
    scoped = _access.filter_queryset(
        queryset, user, employee_path='pegawai'
    )
    allowed_users = _access.filter_users(_active_employees(), user)
    outside_employee = _active_employees().filter(
        riwayatdiklat__pk=OuterRef('pk'),
    ).exclude(pk__in=allowed_users.values('pk'))
    return scoped.annotate(
        _has_outside_history_employee=Exists(outside_employee),
    ).filter(_has_outside_history_employee=False)


def filter_users_for_diklat_role(queryset, user, *, include_self=True):
    return _access.filter_users(queryset, user, include_self=include_self)
