import csv
from datetime import date, datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.http import Http404, StreamingHttpResponse
from django.utils import timezone
from django.views import View

from .access import get_selected_nip
from .document_registry import DOCUMENT_TYPES
from .models import RiwayatJabatan

EXCLUDED_FIELDS = {'id', 'pegawai', 'dokumen'}


class Echo:
    """File-like object agar csv.writer dapat menghasilkan baris streaming."""

    @staticmethod
    def write(value):
        return value


def csv_safe(value):
    """Ubah nilai menjadi teks dan cegah formula injection saat dibuka di Excel."""
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'Ya' if value else 'Tidak'
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        value = value.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(value, date):
        value = value.isoformat()

    text = str(value)
    if text.startswith(('=', '+', '-', '@', '\t', '\r')):
        return f"'{text}"
    return text


class DocumentExportCSVView(LoginRequiredMixin, View):
    """Ekspor seluruh queryset yang diizinkan, tanpa pagination halaman HTML."""

    http_method_names = ['get']

    def get_configuration(self):
        try:
            return DOCUMENT_TYPES[self.kwargs['document_type']]
        except KeyError as exc:
            raise Http404('Jenis dokumen tidak mendukung ekspor.') from exc

    @staticmethod
    def get_employee_field(model):
        try:
            return model._meta.get_field('pegawai')
        except FieldDoesNotExist as exc:
            raise Http404('Dokumen tidak memiliki relasi pegawai.') from exc

    def get_queryset(self, model):
        employee_field = self.get_employee_field(model)
        queryset = model.objects.all()
        if employee_field.many_to_many:
            queryset = queryset.prefetch_related('pegawai__profil_user')
        else:
            queryset = queryset.select_related('pegawai', 'pegawai__profil_user')

        selected_nip = get_selected_nip(self.request)
        if self.request.user.is_dokumen_admin:
            if selected_nip:
                queryset = queryset.filter(pegawai__profil_user__nip=selected_nip)
        else:
            queryset = queryset.filter(pegawai=self.request.user)

        if (
            model is RiwayatJabatan
            and self.request.user.is_dokumen_admin
            and not selected_nip
        ):
            jabatan = (self.request.GET.get('jabatan') or '').strip()
            if jabatan:
                queryset = queryset.filter(jns_jabatan__icontains=jabatan)

        field_names = {field.name for field in model._meta.fields}
        order_by = ['no_urut_dokumen', 'pk'] if 'no_urut_dokumen' in field_names else ['pk']
        return queryset.order_by(*order_by).distinct()

    @staticmethod
    def get_export_fields(model):
        return [
            field for field in model._meta.fields
            if field.name not in EXCLUDED_FIELDS
        ]

    def get_employees(self, instance, employee_field):
        if employee_field.many_to_many:
            if not self.request.user.is_dokumen_admin:
                return [self.request.user]
            return list(instance.pegawai.all())
        employee = instance.pegawai
        return [employee] if employee else []

    @staticmethod
    def get_nip(employee):
        profile = getattr(employee, 'profil_user', None)
        return getattr(profile, 'nip', '') if profile else ''

    def serialize_field(self, instance, field):
        display_method = getattr(instance, f'get_{field.name}_display', None)
        if callable(display_method):
            return csv_safe(display_method())

        value = getattr(instance, field.name)
        if isinstance(field, models.FileField):
            if not value:
                return ''
            try:
                return csv_safe(self.request.build_absolute_uri(value.url))
            except (ValueError, NotImplementedError):
                return csv_safe(value.name)
        return csv_safe(value)

    def stream_rows(self, queryset, export_fields, employee_field):
        writer = csv.writer(Echo())
        yield '\ufeff'
        yield writer.writerow([
            'Nama Pegawai',
            'NIP',
            *[str(field.verbose_name).title() for field in export_fields],
        ])
        for instance in queryset.iterator(chunk_size=1000):
            employees = self.get_employees(instance, employee_field)
            yield writer.writerow([
                csv_safe('; '.join(employee.full_name for employee in employees)),
                csv_safe('; '.join(self.get_nip(employee) for employee in employees)),
                *[
                    self.serialize_field(instance, field)
                    for field in export_fields
                ],
            ])

    def get(self, request, *args, **kwargs):
        title, model = self.get_configuration()
        queryset = self.get_queryset(model)
        export_fields = self.get_export_fields(model)
        employee_field = self.get_employee_field(model)
        filename = f'{self.kwargs["document_type"]}-{date.today():%Y%m%d}.csv'
        response = StreamingHttpResponse(
            self.stream_rows(queryset, export_fields, employee_field),
            content_type='text/csv; charset=utf-8',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Document-Export'] = title
        return response
