from urllib.parse import urlencode

from django.urls import reverse

from myaccount.models import Users

from .access import get_selected_nip
from .requirements import get_required_document_urls


DOCUMENT_QUICK_LINKS = (
    ('Pendidikan', 'riwayat_urls:riwayat_pendidikan', 'pendidikan'),
    ('Pangkat/Golongan', 'riwayat_urls:riwayat_panggol', 'panggol'),
    ('Jabatan', 'riwayat_urls:riwayat_jabatan', 'jabatan'),
    ('Pengangkatan', 'riwayat_urls:riwayat_pengangkatan', 'pengangkatan'),
    ('Penempatan', 'riwayat_urls:riwayat_penempatan', 'penempatan'),
    ('Gaji Berkala', 'riwayat_urls:riwayat_berkala', 'berkala'),
    ('Kinerja', 'riwayat_urls:riwayat_kinerja', 'kinerja'),
    ('PAK', 'riwayat_urls:riwayat_pak', 'pak'),
    ('Uji Kompetensi', 'riwayat_urls:riwayat_ujikom', 'ujikomp'),
    ('Diklat', 'riwayat_urls:riwayat_diklat', 'diklat'),
    ('Penghargaan', 'riwayat_urls:riwayat_penghargaan', 'penghargaan'),
    ('Hukuman', 'riwayat_urls:riwayat_hukuman', 'hukuman'),
    ('Organisasi', 'riwayat_urls:riwayat_organisasi', 'organisasi'),
    ('Profesi/STR', 'riwayat_urls:riwayat_profesi', 'profesi'),
    ('Pengalaman Kerja', 'riwayat_urls:riwayat_bekerja', 'bekerja'),
    ('Keluarga', 'riwayat_urls:riwayat_keluarga', 'keluarga'),
    ('Inovasi', 'riwayat_urls:riwayat_inovasi', 'inovasi'),
    ('Penugasan', 'riwayat_urls:riwayat_penugasan', 'penugasan'),
)

DOCUMENT_EXPORT_URLS = {
    'riwayat_pendidikan': 'pendidikan',
    'riwayat_panggol': 'panggol',
    'riwayat_jabatan': 'jabatan',
    'riwayat_pengangkatan': 'pengangkatan',
    'riwayat_penempatan': 'penempatan',
    'riwayat_berkala': 'berkala',
    'riwayat_kinerja': 'kinerja',
    'riwayat_pak': 'pak',
    'riwayat_ujikom': 'ujikomp',
    'riwayat_penghargaan': 'penghargaan',
    'riwayat_hukuman': 'hukuman',
    'riwayat_cuti': 'cuti',
    'riwayat_diklat': 'diklat',
    'riwayat_kompetensi': 'kompetensi',
    'riwayat_organisasi': 'organisasi',
    'riwayat_profesi': 'profesi',
    'riwayat_bekerja': 'bekerja',
    'riwayat_keluarga': 'keluarga',
    'riwayat_inovasi': 'inovasi',
    'riwayat_penugasan': 'penugasan',
}


def document_quick_navigation(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    menu_url = reverse('riwayat_urls:riwayat_view')
    nip = get_selected_nip(request)
    if nip:
        menu_url = f'{menu_url}?{urlencode({"nip": nip})}'
    resolver_match = getattr(request, 'resolver_match', None)
    url_name = resolver_match.url_name if resolver_match else None
    document_type = DOCUMENT_EXPORT_URLS.get(url_name)
    export_url = None
    if document_type:
        export_url = reverse(
            'riwayat_urls:document_export_csv',
            kwargs={'document_type': document_type},
        )
        params = {}
        if nip:
            params['nip'] = nip
        jabatan = (request.GET.get('jabatan') or '').strip()
        if document_type == 'jabatan' and jabatan:
            params['jabatan'] = jabatan
        if params:
            export_url = f'{export_url}?{urlencode(params)}'
    quick_links = DOCUMENT_QUICK_LINKS
    employee = user
    if user.is_dokumen_admin:
        employee = (
            Users.objects.filter(profil_user__nip=nip).first()
            if nip else None
        )
    if employee is not None:
        required_urls, _employment = get_required_document_urls(employee)
        quick_links = tuple(
            link for link in DOCUMENT_QUICK_LINKS
            if link[2] in required_urls
        )
    return {
        'document_quick_links': quick_links,
        'document_menu_url': menu_url,
        'document_export_url': export_url,
    }


def document_admin_selected_employee(request):
    """Identitas pegawai pada halaman riwayat dokumen.

    Pegawai biasa melihat identitasnya sendiri, sedangkan Admin Dokumen
    melihat identitas pegawai yang dipilih melalui parameter ``nip``.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    resolver_match = getattr(request, 'resolver_match', None)
    if resolver_match is None or resolver_match.namespace != 'riwayat_urls':
        return {}

    if user.is_dokumen_admin:
        nip = get_selected_nip(request)
        if not nip:
            return {}
        employee = (
            Users.objects
            .select_related('profil_user')
            .filter(profil_user__nip=nip)
            .first()
        )
    else:
        employee = (
            Users.objects
            .select_related('profil_user')
            .filter(pk=user.pk)
            .first()
        )
    if employee is None:
        return {}
    return {'document_admin_employee': employee}
