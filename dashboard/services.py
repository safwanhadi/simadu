from datetime import date

from django.db.models import Count, F, IntegerField, OuterRef, Prefetch, Q, Subquery, Value
from django.db.models.functions import Coalesce

from dokumen.models import Kompetensi, RiwayatJabatan, RiwayatPenempatan, RiwayatProfesi
from jenissdm.models import JenisSDM
from myaccount.models import Users
from strukturorg.models import StandarInstalasi, UnitInstalasi


STATUS_TIDAK_MEMENUHI = 'Tidak Memenuhi Standar'
STATUS_SESUAI = 'Sesuai Standar'
STATUS_DIATAS = 'Diatas Standar'
STATUS_BELUM_TERSEDIA = 'Standar Belum Tersedia'


def active_employees():
    """Pegawai aktif yang mempunyai penempatan aktif dan profesi terisi."""
    return (
        Users.objects
        .filter(
            is_active=True,
            is_superuser=False,
            riwayat_penempatan__status=True,
            riwayatprofesi__profesi__isnull=False,
        )
        .distinct()
    )


def jabatan_cards():
    """Jumlah pegawai berdasarkan ``nama_jabatan`` pada riwayat TMT terakhir."""
    latest_jabatan_pk = (
        RiwayatJabatan.objects
        .filter(
            Q(tmt_jabatan__lte=date.today()) | Q(tmt_jabatan__isnull=True),
            pegawai_id=OuterRef('pegawai_id'),
        )
        .order_by(
            F('tmt_jabatan').desc(nulls_last=True),
            '-updated_at',
            '-pk',
        )
        .values('pk')[:1]
    )
    counts = (
        RiwayatJabatan.objects
        .filter(
            pk=Subquery(latest_jabatan_pk),
            nama_jabatan_id=OuterRef('pk'),
            pegawai__is_active=True,
            pegawai__is_superuser=False,
        )
        .values('nama_jabatan_id')
        .annotate(total=Count('pegawai_id', distinct=True))
        .values('total')[:1]
    )
    return (
        JenisSDM.objects
        .annotate(
            jumlah=Coalesce(
                Subquery(counts, output_field=IntegerField()),
                Value(0),
            ),
        )
        .filter(jumlah__gt=0)
        .order_by('jenis_sdm')
    )


def workforce_summary():
    """Ringkasan kualitas data seluruh SDM aktif (semua kategori)."""
    active = Users.objects.filter(is_active=True, is_superuser=False)
    latest_jabatan = (
        RiwayatJabatan.objects
        .filter(
            Q(tmt_jabatan__lte=date.today()) | Q(tmt_jabatan__isnull=True),
            pegawai_id=OuterRef('pk'),
        )
        .order_by(
            F('tmt_jabatan').desc(nulls_last=True),
            '-updated_at',
            '-pk',
        )
        .values('nama_jabatan_id')[:1]
    )
    return {
        'total_active': active.count(),
        'without_active_placement': (
            active
            .exclude(riwayat_penempatan__status=True)
            .distinct()
            .count()
        ),
        'without_jabatan': (
            active
            .annotate(current_jabatan_id=Subquery(latest_jabatan))
            .filter(current_jabatan_id__isnull=True)
            .count()
        ),
    }


def employees_for_jabatan(jabatan_id):
    """Pegawai aktif berdasarkan ``nama_jabatan`` pada riwayat TMT terakhir."""
    active_placements = (
        RiwayatPenempatan.objects
        .filter(status=True)
        .select_related('penempatan_level4')
        .order_by('-updated_at', '-pk')
    )
    latest_jabatan = (
        RiwayatJabatan.objects
        .filter(
            Q(tmt_jabatan__lte=date.today()) | Q(tmt_jabatan__isnull=True),
            pegawai_id=OuterRef('pk'),
        )
        .order_by(
            F('tmt_jabatan').desc(nulls_last=True),
            '-updated_at',
            '-pk',
        )
        .values('nama_jabatan_id')[:1]
    )
    return (
        Users.objects
        .filter(
            is_active=True,
            is_superuser=False,
        )
        .annotate(current_jabatan_id=Subquery(latest_jabatan))
        .filter(current_jabatan_id=jabatan_id)
        .prefetch_related(
            Prefetch(
                'riwayat_penempatan',
                queryset=active_placements,
                to_attr='penempatan_aktif',
            )
        )
        .distinct()
        .order_by('first_name', 'last_name', 'pk')
    )


def valid_competencies(today=None):
    """Kompetensi tanpa masa berlaku atau yang belum melewati tanggal berlaku."""
    today = today or date.today()
    return (
        Kompetensi.objects
        .filter(
            Q(masa_berlaku__isnull=True)
            | Q(berlaku_sd__gte=today)
        )
        .select_related('kompetensi')
        .order_by('kompetensi__kompetensi', 'pk')
    )


def _standard_status(competency_ids, standard):
    required_ids = {item.pk for item in standard.kompetensi_wajib.all()}
    partial_ids = {item.pk for item in standard.kompetensi_wajib_parsial.all()}
    supporting_ids = {item.pk for item in standard.kompetensi_pendukung.all()}

    meets_required = required_ids.issubset(competency_ids)
    meets_partial = not partial_ids or bool(partial_ids.intersection(competency_ids))
    if not meets_required or not meets_partial:
        return STATUS_TIDAK_MEMENUHI
    if supporting_ids.intersection(competency_ids):
        return STATUS_DIATAS
    return STATUS_SESUAI


def _combined_status(statuses):
    if not statuses:
        return STATUS_BELUM_TERSEDIA
    if STATUS_TIDAK_MEMENUHI in statuses:
        return STATUS_TIDAK_MEMENUHI
    if STATUS_BELUM_TERSEDIA in statuses:
        return STATUS_BELUM_TERSEDIA
    # Setelah semua pegawai memenuhi kompetensi wajib, satu pegawai dengan
    # kompetensi pendukung sudah cukup menjadikan instalasi di atas standar.
    if STATUS_DIATAS in statuses:
        return STATUS_DIATAS
    return STATUS_SESUAI


def installation_groups():
    """Kelompok instalasi logis berdasarkan slug, lintas struktur organisasi."""
    standard_slugs = (
        StandarInstalasi.objects
        .values_list('instalasi__slug', flat=True)
        .distinct()
    )
    units = (
        UnitInstalasi.objects
        .filter(slug__in=standard_slugs)
        .order_by('instalasi', 'pk')
    )
    grouped = {}
    for unit in units:
        key = unit.slug or f'instalasi-{unit.pk}'
        group = grouped.setdefault(key, {
            'slug': key,
            'instalasi': unit.instalasi,
            'installation_ids': [],
        })
        group['installation_ids'].append(unit.pk)
    return list(grouped.values())


def _installation_group(installation):
    if isinstance(installation, dict):
        return installation
    return {
        'slug': installation.slug or f'instalasi-{installation.pk}',
        'instalasi': installation.instalasi,
        'installation_ids': [installation.pk],
    }


def installation_standard_data(installation, today=None):
    """Evaluasi satu instalasi logis; standar tetap dicocokkan per profesi."""
    group = _installation_group(installation)
    installation_ids = group['installation_ids']
    standards = list(
        StandarInstalasi.objects
        .filter(instalasi_id__in=installation_ids)
        .select_related('jenis_sdm')
        .prefetch_related(
            'kompetensi_wajib',
            'kompetensi_wajib_parsial',
            'kompetensi_pendukung',
        )
        .order_by('jenis_sdm__jenis_sdm', 'pk')
    )
    standards_by_profession = {}
    for standard in standards:
        standards_by_profession.setdefault(standard.jenis_sdm_id, []).append(standard)

    profession_history = (
        RiwayatProfesi.objects
        .filter(profesi__isnull=False)
        .select_related('profesi')
        .order_by('profesi__jenis_sdm', 'pk')
    )
    latest_active_installation = (
        RiwayatPenempatan.objects
        .filter(pegawai_id=OuterRef('pk'), status=True)
        .order_by('-updated_at', '-pk')
        .values('penempatan_level4_id')[:1]
    )
    users = list(
        active_employees()
        .annotate(
            current_installation_id=Subquery(latest_active_installation),
        )
        .filter(current_installation_id__in=installation_ids)
        .prefetch_related(
            Prefetch(
                'riwayatprofesi_set',
                queryset=profession_history,
                to_attr='profesi_aktif',
            ),
            Prefetch(
                'pegawai_old',
                queryset=valid_competencies(today),
                to_attr='kompetensi_berlaku',
            ),
        )
        .order_by('first_name', 'last_name', 'pk')
    )

    installation_statuses = []
    for user in users:
        profession_map = {
            item.profesi_id: item.profesi
            for item in user.profesi_aktif
            if item.profesi_id
        }
        user.profesi_display = ', '.join(
            profession.jenis_sdm
            for profession in profession_map.values()
        )
        user.kompetensi_display = user.kompetensi_berlaku
        competency_ids = {
            item.kompetensi_id
            for item in user.kompetensi_berlaku
            if item.kompetensi_id
        }

        matching_standards = []
        for profession_id in profession_map:
            profession_standards = standards_by_profession.get(profession_id, [])
            if profession_standards:
                matching_standards.extend(profession_standards)

        user.status_kompetensi = _combined_status([
            _standard_status(competency_ids, standard)
            for standard in matching_standards
        ])
        installation_statuses.append(user.status_kompetensi)

    return {
        'group': group,
        'users': users,
        'status': _combined_status(installation_statuses),
    }


def installation_standard_summaries(installations, today=None):
    summaries = []
    for installation in installations:
        result = installation_standard_data(installation, today=today)
        group = result['group']
        summaries.append({
            'slug': group['slug'],
            'instalasi': group['instalasi'],
            'installation_count': len(group['installation_ids']),
            'status': result['status'],
        })
    return summaries
