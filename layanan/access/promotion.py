"""Cakupan akses bersama untuk kenaikan pangkat dan kenaikan jabatan."""

from myaccount.roles import ADMIN_LAYANAN_JABATAN, ADMIN_LAYANAN_PANGKAT

from .base import RoleScopeAccess
from .cuti import (
    can_supervise_employee,
    filter_queryset_for_leave_supervisor,
    is_leave_structural_officer,
)

_pangkat_access = RoleScopeAccess(
    ADMIN_LAYANAN_PANGKAT,
    filter_queryset_for_leave_supervisor,
    can_supervise_employee,
    is_leave_structural_officer,
)
_jabatan_access = RoleScopeAccess(
    ADMIN_LAYANAN_JABATAN,
    filter_queryset_for_leave_supervisor,
    can_supervise_employee,
    is_leave_structural_officer,
)


def is_pangkat_admin(user, pegawai=None):
    return _pangkat_access.is_admin(user, pegawai)


def is_jabatan_admin(user, pegawai=None):
    return _jabatan_access.is_admin(user, pegawai)


def is_promotion_structural_officer(user):
    return _pangkat_access.is_structural_officer(user)


def filter_pangkat_queryset(queryset, user, *, employee_path="pegawai"):
    return _pangkat_access.filter_queryset(
        queryset, user, employee_path=employee_path
    )


def filter_jabatan_queryset(queryset, user, *, employee_path="pegawai"):
    return _jabatan_access.filter_queryset(
        queryset, user, employee_path=employee_path
    )


def filter_users_for_pangkat_role(queryset, user, *, include_self=True):
    return _pangkat_access.filter_users(
        queryset, user, include_self=include_self
    )


def filter_users_for_jabatan_role(queryset, user, *, include_self=True):
    return _jabatan_access.filter_users(
        queryset, user, include_self=include_self
    )


def can_access_pangkat(user, obj):
    return _pangkat_access.can_access(user, obj)


def can_access_jabatan(user, obj):
    return _jabatan_access.can_access(user, obj)
