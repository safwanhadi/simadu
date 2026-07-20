from urllib.parse import urlencode
from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DeleteView, ListView

from myaccount.models import Users

from .access import DocumentObjectAccessMixin, get_accessible_document, get_selected_nip
from .models import DokumenSDM


class EmployeeDocumentModuleMixin:
    """Konfigurasi bersama untuk satu jenis riwayat dokumen pegawai."""

    model = None
    form_class = None
    template_name = None
    document_url = None
    selected = None
    title_page = None
    success_url_name = None
    order_by = ('no_urut_dokumen',)
    select_related = ()
    file_fields = ()
    pk_url_kwarg = 'id'
    admin_paginate_by = 25

    def validate_configuration(self):
        required = (
            'model', 'template_name', 'document_url', 'selected',
            'title_page', 'success_url_name',
        )
        missing = [name for name in required if not getattr(self, name, None)]
        if missing:
            raise ImproperlyConfigured(
                f'Konfigurasi reusable document view belum lengkap: {", ".join(missing)}'
            )

    def get_document_definition(self):
        document = DokumenSDM.objects.filter(url=self.document_url).first()
        if document is None:
            raise ImproperlyConfigured(
                f'DokumenSDM dengan url "{self.document_url}" belum tersedia.'
            )
        return document

    @staticmethod
    def get_employee_nip(employee):
        profile = getattr(employee, 'profil_user', None)
        return profile.nip if profile else None

    def get_selected_employee(self):
        selected_nip = get_selected_nip(self.request)
        if selected_nip:
            return Users.objects.filter(profil_user__nip=selected_nip).first()
        if not self.request.user.is_dokumen_admin:
            return self.request.user
        return None

    def get_display_nip(self):
        selected_nip = get_selected_nip(self.request)
        if selected_nip:
            return selected_nip
        if not self.request.user.is_dokumen_admin:
            return self.get_employee_nip(self.request.user)
        return None

    def get_document_queryset(self):
        queryset = self.model.objects.all()
        if self.select_related:
            queryset = queryset.select_related(*self.select_related)
        if self.order_by:
            queryset = queryset.order_by(*self.order_by)
        selected_nip = get_selected_nip(self.request)
        if self.request.user.is_dokumen_admin:
            if selected_nip:
                queryset = queryset.filter(pegawai__profil_user__nip=selected_nip)
            return queryset
        return queryset.filter(pegawai=self.request.user)

    def get_common_context(self, **extra):
        employee = extra.get('user') or self.get_selected_employee()
        object_employee = getattr(getattr(self, 'object', None), 'pegawai', None)
        if employee is None and isinstance(object_employee, Users):
            employee = object_employee
        document_queryset = self.get_document_queryset()
        context = {
            'user': employee,
            'data': document_queryset,
            'dok': self.get_document_definition(),
            'page': 'Home',
            'sub_page': 'Riwayat',
            'title_page': self.title_page,
            'nip': self.get_display_nip(),
            'riwayat': 'active',
            'selected': self.selected,
            'document_menu_url': self.get_document_menu_url(employee),
        }
        if isinstance(employee, Users):
            context.update({
                'document_admin_employee': employee,
                'document_admin_document_count': self.model.objects.filter(
                    pegawai=employee,
                ).count(),
            })
        context.update(extra)
        return context

    def get_document_menu_url(self, employee=None):
        url = reverse('riwayat_urls:riwayat_view')
        if self.request.user.is_dokumen_admin and isinstance(employee, Users):
            nip = self.get_employee_nip(employee)
            if nip:
                return f'{url}?{urlencode({"nip": nip})}'
        return url

    def paginate_admin_general_context(self, context):
        """Batasi list lintas pegawai; list satu pegawai tetap ditampilkan penuh."""
        if (
            not self.request.user.is_dokumen_admin
            or get_selected_nip(self.request)
        ):
            return context

        original_data = context.get('data')
        if original_data is None:
            return context
        paginator = Paginator(original_data, self.admin_paginate_by)
        page_obj = paginator.get_page(self.request.GET.get('page'))
        for key, value in tuple(context.items()):
            if value is original_data:
                context[key] = page_obj.object_list
        context.update({
            'paginator': paginator,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'server_side_document_pagination': True,
        })
        return context

    def get_success_query_params(self, employee=None):
        params = {}
        if self.request.user.is_dokumen_admin and employee is not None:
            nip = self.get_employee_nip(employee)
            if nip:
                params['nip'] = nip
        return params

    def get_success_url(self, employee=None):
        url = reverse(self.success_url_name)
        params = self.get_success_query_params(employee)
        return f'{url}?{urlencode(params)}' if params else url

    def capture_old_files(self, instance):
        files = {}
        for field_name in self.file_fields:
            value = getattr(instance, field_name, None)
            if value and value.name:
                files[field_name] = (value.storage, value.name)
        return files

    @staticmethod
    def delete_replaced_files(old_files, instance):
        for field_name, (storage, old_name) in old_files.items():
            new_value = getattr(instance, field_name, None)
            new_name = new_value.name if new_value else ''
            if old_name != new_name:
                transaction.on_commit(
                    lambda storage=storage, name=old_name: storage.delete(name),
                    robust=True,
                )


class EmployeeDocumentManageView(
    EmployeeDocumentModuleMixin,
    LoginRequiredMixin,
    View,
):
    """Reusable list + create view untuk dokumen dengan relasi `pegawai`."""

    def dispatch(self, request, *args, **kwargs):
        self.validate_configuration()
        if self.form_class is None:
            raise ImproperlyConfigured('form_class wajib untuk manage view.')
        if (
            request.user.is_authenticated
            and not request.user.is_dokumen_admin
            and not self.get_employee_nip(request.user)
        ):
            return redirect(reverse(
                'riwayat_urls:notfound_view',
                kwargs={'bagian': 'riwayat', 'selected': self.selected},
            ))
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, **kwargs):
        employee = self.get_selected_employee()
        initial = {'dokumen': self.get_document_definition()}
        if employee is not None:
            initial['pegawai'] = employee
        kwargs.setdefault('initial', initial)
        kwargs['request'] = self.request
        return self.form_class(**kwargs)

    def get(self, request, *args, **kwargs):
        context = self.get_common_context(
            form=self.get_form(),
            form_view='none',
            data_view='block',
        )
        context = self.paginate_admin_general_context(context)
        return render(request, self.template_name, context)

    def can_create_document(self, form):
        """Hook aturan bisnis sebelum dokumen disimpan."""
        return True

    def get_creation_denied_message(self, form):
        return 'Data belum dapat ditambahkan.'

    def save_document(self, form):
        """Hook penyimpanan untuk modul dengan efek bisnis tambahan."""
        return form.save()

    def form_valid(self, form):
        if not self.can_create_document(form):
            messages.warning(
                self.request,
                self.get_creation_denied_message(form),
            )
            return redirect(self.get_success_url(form.cleaned_data.get('pegawai')))

        document = self.save_document(form)
        self.object = document
        messages.success(self.request, 'Data berhasil disimpan!')
        return redirect(
            self.get_success_url(getattr(document, 'pegawai', None))
        )

    def form_invalid(self, form):
        messages.error(self.request, 'Periksa kembali data yang belum valid.')
        context = self.get_common_context(
            form=form,
            form_view='block',
            data_view='none',
        )
        context = self.paginate_admin_general_context(context)
        return render(
            self.request,
            self.template_name,
            context,
            status=400,
        )

    def post(self, request, *args, **kwargs):
        form = self.get_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)


class EmployeeDocumentCreateView(EmployeeDocumentManageView):
    """Reusable create-only view untuk modul dengan halaman form terpisah."""

    def get(self, request, *args, **kwargs):
        context = self.get_common_context(
            form=self.get_form(),
            form_view='block',
            data_view='none',
        )
        return render(request, self.template_name, context)


class EmployeeDocumentListView(
    EmployeeDocumentModuleMixin,
    LoginRequiredMixin,
    ListView,
):
    """Reusable list-only view untuk modul dengan halaman daftar terpisah."""

    context_object_name = 'data'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        self.validate_configuration()
        if (
            request.user.is_authenticated
            and not request.user.is_dokumen_admin
            and not self.get_employee_nip(request.user)
        ):
            return redirect(reverse(
                'riwayat_urls:notfound_view',
                kwargs={'bagian': 'riwayat', 'selected': self.selected},
            ))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_document_queryset()

    def get_paginate_by(self, queryset):
        if self.request.user.is_dokumen_admin and not get_selected_nip(self.request):
            return self.paginate_by
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        common_context = self.get_common_context()
        common_context.pop('data', None)
        context.update(common_context)
        context['server_side_document_pagination'] = bool(
            self.request.user.is_dokumen_admin
            and not get_selected_nip(self.request)
        )
        return context


class EmployeeDocumentUpdateView(
    EmployeeDocumentModuleMixin,
    LoginRequiredMixin,
    View,
):
    """Reusable update view dengan object-scope dan penghapusan file lama aman."""

    def dispatch(self, request, *args, **kwargs):
        self.validate_configuration()
        if self.form_class is None:
            raise ImproperlyConfigured('form_class wajib untuk update view.')
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.object = get_accessible_document(
            self.model,
            request.user,
            pk=kwargs[self.pk_url_kwarg],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, **kwargs):
        kwargs.setdefault('instance', self.object)
        kwargs['request'] = self.request
        return self.form_class(**kwargs)

    def get_context(self, form):
        employee = getattr(self.object, 'pegawai', None)
        return self.get_common_context(
            user=employee,
            nip=self.get_employee_nip(employee),
            form=form,
            update_form=True,
            form_view='block',
            data_view='none',
        )

    def save_document(self, form):
        """Hook penyimpanan untuk modul dengan efek bisnis tambahan."""
        return form.save()

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context(self.get_form()))

    def post(self, request, *args, **kwargs):
        old_files = self.capture_old_files(self.object)
        form = self.get_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            with transaction.atomic():
                self.object = self.save_document(form)
                self.delete_replaced_files(old_files, self.object)
            messages.success(request, 'Data berhasil diperbarui!')
            return redirect(
                self.get_success_url(getattr(self.object, 'pegawai', None))
            )
        messages.error(request, 'Periksa kembali data yang belum valid.')
        return render(
            request,
            self.template_name,
            self.get_context(form),
            status=400,
        )


class EmployeeDocumentDeleteView(
    EmployeeDocumentModuleMixin,
    DocumentObjectAccessMixin,
    DeleteView,
):
    """Reusable delete view yang menghapus file setelah transaksi berhasil."""

    pk_url_kwarg = 'pk'

    def dispatch(self, request, *args, **kwargs):
        self.validate_configuration()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_common_context(form_view='none', data_view='block'))
        return self.paginate_admin_general_context(context)

    def form_valid(self, form):
        employee = getattr(self.object, 'pegawai', None)
        old_files = self.capture_old_files(self.object)
        with transaction.atomic():
            response = super().form_valid(form)
            for storage, old_name in old_files.values():
                transaction.on_commit(
                    lambda storage=storage, name=old_name: storage.delete(name),
                    robust=True,
                )
        messages.success(self.request, 'Data berhasil dihapus!')
        response['Location'] = self.get_success_url(employee)
        return response


@dataclass(frozen=True)
class EmployeeDocumentModule:
    """Satu object konfigurasi yang menghasilkan seluruh CRUD view satu modul."""

    model: object
    form_class: object
    template_name: str
    document_url: str
    selected: str
    title_page: str
    success_url_name: str
    file_fields: tuple = ()
    order_by: tuple = ('no_urut_dokumen',)
    pk_url_kwarg: str = 'id'
    select_related: tuple = ()

    def _view_attributes(self):
        return {
            'model': self.model,
            'form_class': self.form_class,
            'template_name': self.template_name,
            'document_url': self.document_url,
            'selected': self.selected,
            'title_page': self.title_page,
            'success_url_name': self.success_url_name,
            'file_fields': self.file_fields,
            'order_by': self.order_by,
            'pk_url_kwarg': self.pk_url_kwarg,
            'select_related': self.select_related,
            '__module__': self.model.__module__.rsplit('.', 1)[0] + '.views',
        }

    def manage_view(self, class_name, mixins=()):
        return type(
            class_name,
            (*mixins, EmployeeDocumentManageView),
            self._view_attributes(),
        )

    def create_view(self, class_name, mixins=(), template_name=None):
        attributes = self._view_attributes()
        if template_name:
            attributes['template_name'] = template_name
        return type(
            class_name,
            (*mixins, EmployeeDocumentCreateView),
            attributes,
        )

    def list_view(self, class_name, mixins=(), template_name=None):
        attributes = self._view_attributes()
        if template_name:
            attributes['template_name'] = template_name
        return type(
            class_name,
            (*mixins, EmployeeDocumentListView),
            attributes,
        )

    def update_view(self, class_name, mixins=(), template_name=None):
        attributes = self._view_attributes()
        if template_name:
            attributes['template_name'] = template_name
        return type(
            class_name,
            (*mixins, EmployeeDocumentUpdateView),
            attributes,
        )

    def delete_view(self, class_name, mixins=(), template_name=None):
        attributes = self._view_attributes()
        attributes['pk_url_kwarg'] = 'pk'
        if template_name:
            attributes['template_name'] = template_name
        return type(
            class_name,
            (*mixins, EmployeeDocumentDeleteView),
            attributes,
        )
