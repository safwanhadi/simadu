"""Primitif reusable untuk role, assignment scope, dan struktur organisasi."""

from dataclasses import dataclass
from typing import Callable

from myaccount.admin_scopes import (
    active_admin_scopes,
    filter_queryset_by_admin_scope,
    filter_users_by_admin_scope,
    has_admin_scope_for_employee,
)


@dataclass(frozen=True)
class RoleScopeAccess:
    """Gabungkan akses pribadi, assignment admin, dan bawahan struktural."""

    role_name: str
    supervisor_filter: Callable
    supervisor_check: Callable
    structural_check: Callable

    def is_admin(self, user, employee=None):
        if not getattr(user, "is_authenticated", False):
            return False
        if (
            getattr(user, "is_active", False)
            and getattr(user, "is_superuser", False)
        ):
            return True
        if employee is None:
            return active_admin_scopes(user, self.role_name).exists()
        return has_admin_scope_for_employee(
            user, self.role_name, employee
        )

    def is_structural_officer(self, user):
        return self.structural_check(user)

    def filter_queryset(
        self,
        queryset,
        user,
        *,
        employee_path="pegawai",
        include_self=True,
        include_subordinates=True,
    ):
        branches = [
            filter_queryset_by_admin_scope(
                queryset,
                user,
                self.role_name,
                employee_path=employee_path,
            ).distinct()
        ]
        if include_subordinates:
            branches.append(
                self.supervisor_filter(
                    queryset, user, employee_path=employee_path
                ).distinct()
            )
        if include_self:
            branches.append(
                queryset.filter(**{employee_path: user}).distinct()
            )
        result = branches[0]
        for branch in branches[1:]:
            result = result | branch
        return result.distinct()

    def filter_users(
        self,
        queryset,
        user,
        *,
        include_self=True,
        include_subordinates=True,
    ):
        branches = [
            filter_users_by_admin_scope(
                queryset, user, self.role_name
            ).distinct(),
        ]
        if include_subordinates:
            branches.append(self.supervisor_filter(
                queryset, user, employee_path=""
            ).distinct())
        if include_self:
            branches.append(queryset.filter(pk=user.pk).distinct())
        result = branches[0]
        for branch in branches[1:]:
            result = result | branch
        return result.distinct()

    def can_access(self, user, obj, *, employee_attr="pegawai"):
        employee = getattr(obj, employee_attr, None)
        return bool(
            employee
            and (
                user.pk == employee.pk
                or self.is_admin(user, employee)
                or self.supervisor_check(user, employee)
            )
        )
