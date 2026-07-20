from datetime import date

from django.db.models import BooleanField, Exists, F, OuterRef, Q, Value

from .models import DokumenSDM, KewajibanDokumen, RiwayatPengangkatan


def get_current_employment_record(employee, on_date=None):
    """Ambil status terbaru yang sudah efektif; riwayat tanpa TMT menjadi fallback."""
    if employee is None or not getattr(employee, 'pk', None):
        return None
    on_date = on_date or date.today()
    records = RiwayatPengangkatan.objects.filter(pegawai=employee)
    return (
        records
        .filter(Q(tmt_pegawai__lte=on_date) | Q(tmt_pegawai__isnull=True))
        .order_by(
            F('tmt_pegawai').desc(nulls_last=True),
            '-tgl_srt_putusan',
            '-pk',
        )
        .first()
    )


def get_required_documents(employee):
    employment = get_current_employment_record(employee)
    documents = DokumenSDM.objects.all().order_by('id')
    if employment is None:
        return documents.filter(url='pengangkatan').annotate(
            is_required=Value(True, output_field=BooleanField()),
        ), None
    applicable_rules = KewajibanDokumen.objects.filter(
        dokumen_id=OuterRef('pk'),
        status_pegawai=employment.status_pegawai,
    )
    return (
        documents
        .filter(Exists(applicable_rules))
        .annotate(
            is_required=Exists(applicable_rules.filter(wajib=True)),
        ),
        employment,
    )


def get_required_document_urls(employee):
    documents, employment = get_required_documents(employee)
    return set(documents.values_list('url', flat=True)), employment
