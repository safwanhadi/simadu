from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.http import Http404
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode
from layanan.access.documents import (
    filter_document_queryset,
    is_document_scope_manager,
)


def get_safe_return_url(request):
    """Ambil URL asal internal tanpa membuka celah open redirect."""
    return_to = (
        request.GET.get('return_to')
        or request.GET.get('redirect_to')
        or ''
    ).strip()
    if return_to and url_has_allowed_host_and_scheme(
        return_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return return_to
    return None


def preserve_return_url(request, url):
    """Teruskan tujuan kembali saat view melakukan redirect internal."""
    return_to = get_safe_return_url(request)
    if not return_to:
        return url
    separator = '&' if '?' in url else '?'
    return f'{url}{separator}{urlencode({"return_to": return_to})}'


def is_document_admin(user):
    """Superuser dan anggota grup Admin Dokumen memakai akses lintas pegawai."""
    return bool(
        getattr(user, 'is_authenticated', False)
        and is_document_scope_manager(user)
    )


def get_selected_nip(request):
    """Parameter pemilihan pegawai hanya boleh dipakai Admin Dokumen."""
    if not is_document_admin(request.user):
        return None
    return (request.GET.get('nip') or '').strip() or None


def scope_document_queryset(queryset, user):
    """Batasi queryset ke pemilik dokumen, kecuali untuk Admin Dokumen."""
    if is_document_admin(user):
        model = queryset.model
        relation_lookup = {
            'RiwayatSIPProfesi': 'riwayat_profesi__pegawai',
            'OrangTua': 'keluarga__pegawai',
            'Pasangan': 'keluarga__pegawai',
            'Anak': 'keluarga__pegawai',
        }.get(model.__name__, 'pegawai')
        try:
            return filter_document_queryset(
                queryset,
                user,
                employee_path=relation_lookup,
            )
        except (FieldDoesNotExist, FieldError):
            return queryset.none()

    model = queryset.model
    try:
        model._meta.get_field('pegawai')
    except FieldDoesNotExist:
        relation_lookup = {
            'RiwayatSIPProfesi': 'riwayat_profesi__pegawai',
            'OrangTua': 'keluarga__pegawai',
            'Pasangan': 'keluarga__pegawai',
            'Anak': 'keluarga__pegawai',
        }.get(model.__name__)
        if relation_lookup:
            return queryset.filter(**{relation_lookup: user})
        # Model referensi seperti DokumenSDM tidak memuat dokumen milik pegawai.
        return queryset.none()
    return queryset.filter(pegawai=user)


def get_accessible_document(model, user, **lookup):
    try:
        return scope_document_queryset(model.objects.all(), user).get(**lookup)
    except model.DoesNotExist as exc:
        raise Http404('Dokumen tidak ditemukan atau tidak dapat diakses.') from exc


class DocumentObjectAccessMixin(LoginRequiredMixin):
    """Pengaman object-level untuk Detail/Update/Delete berbasis generic view."""

    def get_queryset(self):
        return scope_document_queryset(super().get_queryset(), self.request.user)


class DocumentAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return is_document_admin(self.request.user)
