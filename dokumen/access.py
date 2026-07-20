from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import FieldDoesNotExist
from django.http import Http404


def is_document_admin(user):
    """Superuser dan anggota grup Admin Dokumen memakai akses lintas pegawai."""
    return bool(user.is_authenticated and user.is_dokumen_admin)


def get_selected_nip(request):
    """Parameter pemilihan pegawai hanya boleh dipakai Admin Dokumen."""
    if not is_document_admin(request.user):
        return None
    return (request.GET.get('nip') or '').strip() or None


def scope_document_queryset(queryset, user):
    """Batasi queryset ke pemilik dokumen, kecuali untuk Admin Dokumen."""
    if is_document_admin(user):
        return queryset

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
