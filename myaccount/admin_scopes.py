"""Resolver cakupan data untuk peran admin operasional."""

from datetime import date

from django.db.models import Q

from .models import AdminScopeAssignment


def active_admin_scopes(user, role, *, on_date=None):
    """Assignment aktif untuk role; kepemilikan group tetap wajib."""
    if not user or not getattr(user, 'is_active', False):
        return AdminScopeAssignment.objects.none()
    if not user.has_admin_role(role):
        return AdminScopeAssignment.objects.none()

    on_date = on_date or date.today()
    return (
        AdminScopeAssignment.objects.filter(
            user=user,
            group__name=role,
            is_active=True,
            valid_from__lte=on_date,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=on_date))
        .select_related(
            'group',
            'instansi_daerah',
            'satuan_kerja_induk',
            'unit_organisasi',
            'bidang',
            'sub_bidang',
            'unit_instalasi',
        )
    )


def _structure_lineage(structure):
    """Petakan satu simpul ke seluruh induknya berdasarkan model struktur."""
    model_name = structure._meta.model_name
    if model_name == 'unitinstalasi':
        sub_bidang = structure.sub_bidang
        bidang = sub_bidang.bidang
        unit_organisasi = bidang.unor
        satuan_kerja_induk = unit_organisasi.satker_induk
        instansi_daerah = satuan_kerja_induk.instansi_daerah
        return {
            'unit_instalasi': structure.pk,
            'sub_bidang': sub_bidang.pk,
            'bidang': bidang.pk,
            'unit_organisasi': unit_organisasi.pk,
            'satuan_kerja_induk': satuan_kerja_induk.pk,
            'instansi_daerah': instansi_daerah.pk,
        }
    if model_name == 'subbidang':
        bidang = structure.bidang
        unit_organisasi = bidang.unor
        satuan_kerja_induk = unit_organisasi.satker_induk
        return {
            'sub_bidang': structure.pk,
            'bidang': bidang.pk,
            'unit_organisasi': unit_organisasi.pk,
            'satuan_kerja_induk': satuan_kerja_induk.pk,
            'instansi_daerah': satuan_kerja_induk.instansi_daerah_id,
        }
    if model_name == 'bidang':
        unit_organisasi = structure.unor
        satuan_kerja_induk = unit_organisasi.satker_induk
        return {
            'bidang': structure.pk,
            'unit_organisasi': unit_organisasi.pk,
            'satuan_kerja_induk': satuan_kerja_induk.pk,
            'instansi_daerah': satuan_kerja_induk.instansi_daerah_id,
        }
    if model_name == 'unitorganisasi':
        satuan_kerja_induk = structure.satker_induk
        return {
            'unit_organisasi': structure.pk,
            'satuan_kerja_induk': satuan_kerja_induk.pk,
            'instansi_daerah': satuan_kerja_induk.instansi_daerah_id,
        }
    if model_name == 'satuankerjainduk':
        return {
            'satuan_kerja_induk': structure.pk,
            'instansi_daerah': structure.instansi_daerah_id,
        }
    if model_name == 'instansidaerah':
        return {'instansi_daerah': structure.pk}
    raise TypeError('Objek bukan simpul struktur organisasi yang didukung.')


def has_admin_scope(user, role, structure=None, *, on_date=None):
    """Periksa role dan scope; scope induk mencakup semua turunannya."""
    if getattr(user, 'is_active', False) and getattr(user, 'is_superuser', False):
        return True

    assignments = active_admin_scopes(user, role, on_date=on_date)
    if structure is None:
        return assignments.exists()

    lineage = _structure_lineage(structure)
    for assignment in assignments:
        if assignment.scope_type == AdminScopeAssignment.GLOBAL:
            return True
        if lineage.get(assignment.scope_type) == getattr(
            assignment, f'{assignment.scope_type}_id'
        ):
            return True
    return False


PLACEMENT_SCOPE_LOOKUPS = {
    AdminScopeAssignment.INSTANSI_DAERAH: (
        'penempatan_level1__satker_induk__instansi_daerah_id',
        'penempatan_level2__unor__satker_induk__instansi_daerah_id',
        'penempatan_level3__bidang__unor__satker_induk__instansi_daerah_id',
        'penempatan_level4__sub_bidang__bidang__unor__satker_induk__instansi_daerah_id',
    ),
    AdminScopeAssignment.SATUAN_KERJA_INDUK: (
        'penempatan_level1__satker_induk_id',
        'penempatan_level2__unor__satker_induk_id',
        'penempatan_level3__bidang__unor__satker_induk_id',
        'penempatan_level4__sub_bidang__bidang__unor__satker_induk_id',
    ),
    AdminScopeAssignment.UNIT_ORGANISASI: (
        'penempatan_level1_id',
        'penempatan_level2__unor_id',
        'penempatan_level3__bidang__unor_id',
        'penempatan_level4__sub_bidang__bidang__unor_id',
    ),
    AdminScopeAssignment.BIDANG: (
        'penempatan_level2_id',
        'penempatan_level3__bidang_id',
        'penempatan_level4__sub_bidang__bidang_id',
    ),
    AdminScopeAssignment.SUB_BIDANG: (
        'penempatan_level3_id',
        'penempatan_level4__sub_bidang_id',
    ),
    AdminScopeAssignment.UNIT_INSTALASI: (
        'penempatan_level4_id',
    ),
}


def get_employee_scope_structure(employee):
    """Simpul penempatan aktif paling spesifik milik seorang pegawai."""
    if employee is None:
        return None
    placement = (
        employee.riwayat_penempatan.filter(status=True)
        .select_related(
            'penempatan_level1',
            'penempatan_level2',
            'penempatan_level3',
            'penempatan_level4',
        )
        .order_by('-updated_at', '-id')
        .first()
    )
    if placement is None:
        return None
    return (
        placement.penempatan_level4
        or placement.penempatan_level3
        or placement.penempatan_level2
        or placement.penempatan_level1
    )


def has_admin_scope_for_employee(user, role, employee, *, on_date=None):
    """Periksa role dan assignment terhadap penempatan aktif pegawai."""
    if (
        getattr(user, 'is_active', False)
        and getattr(user, 'is_superuser', False)
    ):
        return True

    structure = get_employee_scope_structure(employee)
    if structure is not None:
        return has_admin_scope(
            user,
            role,
            structure,
            on_date=on_date,
        )

    # Data pegawai tanpa penempatan hanya dapat dikelola scope global.
    return active_admin_scopes(
        user,
        role,
        on_date=on_date,
    ).filter(scope_type=AdminScopeAssignment.GLOBAL).exists()


def _scope_query(assignments, placement_path):
    if assignments.filter(
        scope_type=AdminScopeAssignment.GLOBAL
    ).exists():
        return None

    scope_query = Q()
    for assignment in assignments:
        target_id = getattr(assignment, f'{assignment.scope_type}_id', None)
        for lookup in PLACEMENT_SCOPE_LOOKUPS.get(
            assignment.scope_type,
            (),
        ):
            scope_query |= Q(**{f'{placement_path}__{lookup}': target_id})
    return scope_query


def filter_queryset_by_admin_scope(
    queryset,
    user,
    role,
    *,
    employee_path='pegawai',
    on_date=None,
):
    """Filter queryset bermodel pegawai menggunakan role dan assignment."""
    if (
        getattr(user, 'is_active', False)
        and getattr(user, 'is_superuser', False)
    ):
        return queryset

    assignments = active_admin_scopes(user, role, on_date=on_date)
    if not assignments.exists():
        return queryset.none()

    placement_path = (
        f'{employee_path}__riwayat_penempatan'
        if employee_path else 'riwayat_penempatan'
    )
    scope_query = _scope_query(assignments, placement_path)
    if scope_query is None:
        return queryset
    return queryset.filter(
        scope_query,
        **{f'{placement_path}__status': True},
    ).distinct()


def filter_users_by_admin_scope(queryset, user, role, *, on_date=None):
    """Shortcut filtering ketika queryset langsung berisi model Users."""
    return filter_queryset_by_admin_scope(
        queryset,
        user,
        role,
        employee_path='',
        on_date=on_date,
    )
