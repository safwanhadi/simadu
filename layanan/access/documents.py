"""Cakupan Admin Dokumen untuk modul riwayat tanpa role layanan khusus."""

from myaccount.roles import ADMIN_DOKUMEN

from .base import RoleScopeAccess


def _no_subordinates(queryset, user, *, employee_path='pegawai'):
    return queryset.none()


def _cannot_supervise(user, employee):
    return False


def _not_structural_document_manager(user):
    return False

document_access = RoleScopeAccess(
    ADMIN_DOKUMEN,
    _no_subordinates,
    _cannot_supervise,
    _not_structural_document_manager,
)


def is_document_scope_admin(user, employee=None):
    return document_access.is_admin(user, employee)


def is_document_scope_manager(user):
    """Akses lintas pegawai hanya untuk Admin Dokumen/superuser."""
    return document_access.is_admin(user)


def filter_document_queryset(queryset, user, *, employee_path="pegawai"):
    return document_access.filter_queryset(
        queryset,
        user,
        employee_path=employee_path,
        include_subordinates=False,
    )


def filter_document_users(queryset, user, *, include_self=True):
    return document_access.filter_users(
        queryset,
        user,
        include_self=include_self,
        include_subordinates=False,
    )


def can_access_document(user, obj):
    employee = getattr(obj, 'pegawai', None)
    return bool(
        employee
        and (
            user.pk == employee.pk
            or document_access.is_admin(user, employee)
        )
    )
