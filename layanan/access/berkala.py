"""Aturan akses bersama untuk layanan dan riwayat gaji berkala."""

from myaccount.roles import ADMIN_LAYANAN_BERKALA

from .base import RoleScopeAccess
from .cuti import (
    can_supervise_employee,
    filter_queryset_for_leave_supervisor,
    is_leave_structural_officer,
)

_access = RoleScopeAccess(
    ADMIN_LAYANAN_BERKALA,
    filter_queryset_for_leave_supervisor,
    can_supervise_employee,
    is_leave_structural_officer,
)


def is_berkala_admin(user, pegawai=None):
    return _access.is_admin(user, pegawai)


def is_berkala_structural_officer(user):
    return _access.is_structural_officer(user)


def filter_berkala_queryset(queryset, user, *, employee_path="pegawai"):
    return _access.filter_queryset(
        queryset, user, employee_path=employee_path
    )


def filter_users_for_berkala_role(queryset, user, *, include_self=True):
    return _access.filter_users(queryset, user, include_self=include_self)


def can_access_berkala(user, obj):
    return _access.can_access(user, obj)
