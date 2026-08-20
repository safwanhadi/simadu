"""Aturan akses bersama untuk layanan SIP dan riwayat profesi."""

from myaccount.roles import ADMIN_LAYANAN_SIP

from .base import RoleScopeAccess
from .cuti import (
    can_supervise_employee,
    filter_queryset_for_leave_supervisor,
    is_leave_structural_officer,
)

_access = RoleScopeAccess(
    role_name=ADMIN_LAYANAN_SIP,
    supervisor_filter=filter_queryset_for_leave_supervisor,
    supervisor_check=can_supervise_employee,
    structural_check=is_leave_structural_officer,
)


def is_sip_admin(user, pegawai=None):
    return _access.is_admin(user, pegawai)


def is_sip_structural_officer(user):
    return _access.is_structural_officer(user)


def filter_queryset_for_sip_admin(queryset, user, *, employee_path="pegawai"):
    return _access.filter_queryset(
        queryset,
        user,
        employee_path=employee_path,
        include_self=False,
        include_subordinates=False,
    )


def filter_users_for_sip_role(queryset, user, *, include_self=True):
    return _access.filter_users(queryset, user, include_self=include_self)


def _filter_employee_queryset(queryset, user, employee_path):
    return _access.filter_queryset(
        queryset, user, employee_path=employee_path
    )


def filter_sip_service_queryset(queryset, user):
    return _filter_employee_queryset(queryset, user, "pegawai")


def filter_profession_history_queryset(queryset, user):
    return _filter_employee_queryset(queryset, user, "pegawai")


def filter_profession_sip_queryset(queryset, user):
    return _filter_employee_queryset(queryset, user, "riwayat_profesi__pegawai")


def can_manage_sip(user, layanan_sip):
    return _access.can_access(user, layanan_sip)


def can_manage_profession_history(user, riwayat_profesi):
    return _access.can_access(user, riwayat_profesi)
