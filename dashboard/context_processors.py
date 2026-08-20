from dokumen.models import DokumenSDM
from dokumen.access import get_selected_nip
from dokumen.requirements import get_required_documents
from dokumen.notifications import (
    get_sip_expiry_notifications,
    get_str_expiry_notifications,
)
from myaccount.models import Users
from layanan.models import (
    JenisLayanan,
    LayananCuti,
    LayananGajiBerkala,
    LayananNaikPangkat,
    LayananNaikJabatan,
    LayananSIP,
    LayananUsulanInovasi,
    LayananUsulanDiklat,
)
from layanan.access.cuti import (
    filter_queryset_for_leave_admin,
    filter_queryset_for_leave_supervisor,
    is_leave_admin,
)
from layanan.access.inovasi import (
    filter_inovasi_queryset,
    is_inovasi_admin,
    is_inovasi_structural_officer,
)
from informasi.models import NasehatdanHadist
from itertools import chain
from django.db.models import Q

from .hadist_modal import hadist_modal_session_key


def _sip_notification_values(queryset):
    """Samakan penanda layanan SIP dengan routing notifikasi dashboard."""
    notifications = list(queryset.values(
        'id', 'pegawai__first_name', 'pegawai__last_name',
        'status', 'created_at'
    ).order_by('-created_at'))
    for notification in notifications:
        notification['layanan__url'] = 'yansip'
    return notifications


def _berkala_notification_values(queryset):
    notifications = list(queryset.values(
        'id', 'pegawai__first_name', 'pegawai__last_name',
        'pegawai__profil_user__nip', 'status', 'created_at'
    ).order_by('-created_at'))
    for notification in notifications:
        notification['layanan__url'] = 'yanberkala'
    return notifications


def _cuti_notification_values(queryset):
    notifications = list(queryset.values(
        'id', 'pegawai__first_name', 'pegawai__last_name',
        'verifikasicuti__persetujuan3', 'status', 'created_at'
    ).order_by('-created_at'))
    for notification in notifications:
        notification['layanan__url'] = 'yancuti'
    return notifications


def _pangkat_notification_values(queryset):
    notifications = list(queryset.values(
        'id', 'pegawai__first_name', 'pegawai__last_name',
        'status', 'created_at'
    ).order_by('-created_at'))
    for notification in notifications:
        notification['layanan__url'] = 'yanpangkat'
    return notifications


def _jabatan_notification_values(queryset):
    notifications = list(queryset.values(
        'id', 'pegawai__first_name', 'pegawai__last_name',
        'status', 'created_at'
    ).order_by('-created_at'))
    for notification in notifications:
        notification['layanan__url'] = 'yanjabatan'
    return notifications


def _diklat_notification_values(queryset):
    notifications = list(queryset.values(
        'id', 'riwayatdiklat__nama_diklat',
        'riwayatdiklat__pegawai__first_name',
        'riwayatdiklat__pegawai__last_name',
        'status', 'created_at',
    ).order_by('-created_at'))
    for notification in notifications:
        notification['layanan__url'] = 'yandiklat'
    return notifications


def _inovasi_notification_values(queryset, user=None):
    notifications = list(queryset.values(
        'id', 'pegawai_id', 'pegawai__first_name', 'pegawai__last_name',
        'status', 'created_at',
    ).order_by('-created_at'))
    for notification in notifications:
        notification['layanan__url'] = 'yaninovasi'
        notification['can_process'] = bool(
            user is None
            or is_inovasi_admin(
                user,
                Users.objects.filter(pk=notification['pegawai_id']).first(),
            )
        )
    return notifications


def menu_riwayat_sdm(request):
    data_dokumen = DokumenSDM.objects.all().order_by('id')
    if request.user.is_authenticated:
        employee = request.user
        if request.user.is_dokumen_admin:
            nip = get_selected_nip(request)
            if not nip:
                return {'data_dokumen': data_dokumen}
            employee = Users.objects.filter(profil_user__nip=nip).first()
        if employee is not None:
            data_dokumen, _employment = get_required_documents(employee)
    return {'data_dokumen': data_dokumen}

def menu_layanan_sdm(request):
    data_layanan = JenisLayanan.objects.filter(status=True).order_by('id')
    status_cuti = ['riwayat', 'baru', 'tunda', 'ambil-tunda']
    return {'data_layanan': data_layanan, 'status_cuti':status_cuti}


def notifikasi_layanan(request):
    """
    Context processor untuk menyediakan notifikasi layanan di seluruh aplikasi.
    Kode ini sudah dioptimalkan untuk struktur hirarki admin.
    """
    # === Blok 1: Untuk user yang tidak login ===
    if not request.user.is_authenticated:
        return {
            'notifikasi_layanan': [], 'notif_cuti': [], 'notif_cuti_admin': [],
            'notif_berkala': [], 'notif_diklat': [], 'notif_diklat_admin': [],
            'notif_inovasi': [], 'notif_sip': [], 'notif_pangkat': [],
            'notif_jabatan': [], 'sip_expiry_notifications': [],
            'str_expiry_notifications': [],
            'expiry_notification_total': 0,
            'notification_total': 0,
            'is_cuti_scope_admin': False,
        }

    sip_expiry_notifications = get_sip_expiry_notifications(request.user)
    str_expiry_notifications = get_str_expiry_notifications(request.user)

    # === Blok 2: Untuk Superuser (Melihat Semua Notifikasi Pengajuan) ===
    if request.user.is_superuser:
        layanan_cuti = _cuti_notification_values(
            LayananCuti.objects.filter(status__in=("pengajuan", "tindaklanjut"))
        )
        layanan_berkala = _berkala_notification_values(
            LayananGajiBerkala.objects.filter(status="pengajuan")
        )
        layanan_diklat = _diklat_notification_values(
            LayananUsulanDiklat.objects.filter(status='usulan')
        )
        layanan_inovasi = _inovasi_notification_values(
            LayananUsulanInovasi.objects.filter(status='usulan')
        )
        layanan_sip = _sip_notification_values(
            LayananSIP.objects.filter(status="belum", is_read=False)
        )
        layanan_pangkat = _pangkat_notification_values(
            LayananNaikPangkat.objects.filter(status='pengajuan')
        )
        layanan_jabatan = _jabatan_notification_values(
            LayananNaikJabatan.objects.filter(status='pengajuan')
        )
        
        notifikasi = list(chain(layanan_cuti, layanan_berkala, layanan_diklat, layanan_inovasi, layanan_sip, layanan_pangkat, layanan_jabatan))
        return {
            'notifikasi_layanan': notifikasi, 'notif_cuti': layanan_cuti, 'notif_berkala': layanan_berkala,
            'notif_diklat': layanan_diklat, 'notif_inovasi': layanan_inovasi, 'notif_sip': layanan_sip,
            'notif_pangkat': layanan_pangkat,
            'notif_jabatan': layanan_jabatan,
            'notif_cuti_admin': [], 'notif_diklat_admin': [],
            'sip_expiry_notifications': sip_expiry_notifications,
            'str_expiry_notifications': str_expiry_notifications,
            'expiry_notification_total': (
                len(sip_expiry_notifications) + len(str_expiry_notifications)
            ),
            'notification_total': (
                len(notifikasi)
                + len(sip_expiry_notifications)
                + len(str_expiry_notifications)
            ),
            'is_cuti_scope_admin': True,
        }

    # === Blok 3: Untuk User Biasa dan Admin Hirarki ===
    # Inisialisasi awal agar tidak terjadi NameError jika kondisi tidak terpenuhi
    layanan_cuti_admin = LayananCuti.objects.none()
    layanan_diklat_admin = LayananUsulanDiklat.objects.none()

    # Query notifikasi untuk admin hirarki (jika user adalah staff)
    if (
        request.user.is_staff
        and hasattr(request.user, 'profil_admin')
    ):
        from strukturorg.models import Bidang, PejabatStruktur, SubBidang
        from strukturorg.services import filter_structures_led_by
        profil_admin = request.user.profil_admin

        instalasi_aktif = filter_structures_led_by(profil_admin.instalasi.all(), request.user)
        sub_bidang_aktif = filter_structures_led_by(profil_admin.sub_bidang.all(), request.user)
        bidang_aktif = filter_structures_led_by(profil_admin.bidang.all(), request.user)
        unor_aktif = filter_structures_led_by(profil_admin.unor.all(), request.user)

        # Level 4: Kepala Instalasi
        if instalasi_aktif.exists() and profil_admin.is_pejabat:
            instalasi_pks = instalasi_aktif.values_list('pk', flat=True)
            layanan_cuti_admin = LayananCuti.objects.filter(
                status__in=("pengajuan", "tindaklanjut"),
                pegawai__riwayat_penempatan__penempatan_level4__in=instalasi_pks, 
                pegawai__riwayat_penempatan__status=True
            )
            layanan_diklat_admin = LayananUsulanDiklat.objects.filter(
                status="usulan", 
                riwayatdiklat__pegawai__riwayat_penempatan__penempatan_level4__in=instalasi_pks, 
                riwayatdiklat__pegawai__riwayat_penempatan__status=True
            ).distinct()

        # Level 3: Kepala Seksi/Sub-Bagian
        elif sub_bidang_aktif.exists() and profil_admin.is_pejabat:
            # Perbaikan typo: values_list & flat=True
            sub_bidang_pks = sub_bidang_aktif.values_list('pk', flat=True)
            layanan_cuti_admin = LayananCuti.objects.filter(
                status__in=("pengajuan", "tindaklanjut"),
                pegawai__riwayat_penempatan__penempatan_level3__in=sub_bidang_pks, 
                pegawai__riwayat_penempatan__status=True
            ).exclude(pegawai=request.user)
            
            layanan_diklat_admin = LayananUsulanDiklat.objects.filter(
                status="usulan", 
                riwayatdiklat__pegawai__riwayat_penempatan__penempatan_level3__in=sub_bidang_pks, 
                riwayatdiklat__pegawai__riwayat_penempatan__status=True
            ).distinct()

        # Level 2: Kepala Bidang (UPDATED)
        elif bidang_aktif.exists() and profil_admin.is_pejabat:
            # 1. Ambil semua PK bidang yang ditekuni admin ini
            bidang_pks = bidang_aktif.values_list('pk', flat=True)
            
            # 2. Cari semua SubBidang yang berada di bawah bidang-bidang tersebut
            sub_bidangs = SubBidang.objects.filter(bidang__in=bidang_pks)
            
            # 3. Ambil pimpinan_ids (Kepala Seksi/Sub-Bagian) dari sub-bidang terkait
            pimpinan_ids = list(PejabatStruktur.objects.filter(
                is_active=True,
                sub_bidang__in=sub_bidangs,
            ).values_list('pejabat_id', flat=True).distinct())

            # Filter Cuti: Bawahan di penempatan level 3 ATAU user pimpinan itu sendiri
            q_filter = Q(pegawai__riwayat_penempatan__penempatan_level3__in=sub_bidangs) | Q(pegawai_id__in=pimpinan_ids)
            layanan_cuti_admin = LayananCuti.objects.filter(
                q_filter, 
                status__in=("pengajuan", "tindaklanjut"),
                pegawai__riwayat_penempatan__status=True
            ).distinct()
            
            # Filter Diklat
            q_filter_diklat = Q(riwayatdiklat__pegawai__riwayat_penempatan__penempatan_level3__in=sub_bidangs) | Q(riwayatdiklat__pegawai__id__in=pimpinan_ids)
            layanan_diklat_admin = LayananUsulanDiklat.objects.filter(
                q_filter_diklat, 
                status="usulan", 
                riwayatdiklat__pegawai__riwayat_penempatan__status=True
            ).distinct()

        # Level 1: Direktur / Pimpinan Unit Organisasi (UPDATED)
        elif unor_aktif.exists() and profil_admin.is_pejabat:
            # 1. Ambil semua PK unor yang ditekuni admin ini
            unor_pks = unor_aktif.values_list('pk', flat=True)
            
            # 2. Cari semua Bidang yang berada di bawah unor-unor tersebut
            bidangs = Bidang.objects.filter(unor__in=unor_pks)
            
            # 3. Ambil pimpinan_ids (Kepala Bidang) dari bidang terkait
            pimpinan_ids = list(PejabatStruktur.objects.filter(
                is_active=True,
                bidang__in=bidangs,
            ).values_list('pejabat_id', flat=True).distinct())

            # Filter Cuti: Bawahan di penempatan level 2 ATAU pimpinan bidang terkait
            q_filter = Q(pegawai__riwayat_penempatan__penempatan_level2__in=bidangs) | Q(pegawai__id__in=pimpinan_ids)
            layanan_cuti_admin = LayananCuti.objects.filter(
                q_filter, 
                status__in=("pengajuan", "tindaklanjut"),
                pegawai__riwayat_penempatan__status=True, 
                verifikasicuti__persetujuan2=True
            ).distinct()

            # Filter Diklat
            q_filter_diklat = Q(riwayatdiklat__pegawai__riwayat_penempatan__penempatan_level2__in=bidangs) | Q(riwayatdiklat__pegawai__id__in=pimpinan_ids)
            layanan_diklat_admin = LayananUsulanDiklat.objects.filter(
                q_filter_diklat, 
                status="usulan", 
                riwayatdiklat__pegawai__riwayat_penempatan__status=True
            ).distinct()

    pending_cuti = LayananCuti.objects.filter(
        status__in=("pengajuan", "tindaklanjut"),
    )
    layanan_cuti_admin = filter_queryset_for_leave_supervisor(
        pending_cuti,
        request.user,
    )

    # Admin Cuti menerima pengajuan melalui daftar utama sesuai assignment.
    if is_leave_admin(request.user):
        layanan_cuti_admin = LayananCuti.objects.none()
    if request.user.is_diklat_admin:
        layanan_diklat_admin = LayananUsulanDiklat.objects.none()

    layanan_cuti_admin = _cuti_notification_values(layanan_cuti_admin)
    layanan_diklat_admin = _diklat_notification_values(layanan_diklat_admin)

    # Query notifikasi untuk pegawai (pribadi)
    if is_leave_admin(request.user):
        layanan_cuti_pegawai = _cuti_notification_values(
            filter_queryset_for_leave_admin(
                pending_cuti,
                request.user,
            )
        )
    else:
        layanan_cuti_pegawai = _cuti_notification_values(
            LayananCuti.objects.filter(
                pegawai=request.user,
                status__in=('disetujui', 'ditolak'),
                is_read=False,
            )
        )
    if request.user.is_berkala_admin:
        layanan_berkala = _berkala_notification_values(
            LayananGajiBerkala.objects.filter(status="pengajuan")
        )
    else:
        layanan_berkala = _berkala_notification_values(
            LayananGajiBerkala.objects.filter(
                pegawai=request.user, status='selesai', is_read=False,
            )
        )
    if request.user.is_diklat_admin:
        layanan_diklat = _diklat_notification_values(
            LayananUsulanDiklat.objects.filter(status='usulan')
        )
    else:
        layanan_diklat = _diklat_notification_values(
            LayananUsulanDiklat.objects.filter(
                riwayatdiklat__pegawai=request.user,
                status='selesai',
                is_read=False,
            )
        )
    if (
        request.user.is_inovasi_admin
        or is_inovasi_structural_officer(request.user)
    ):
        layanan_inovasi = _inovasi_notification_values(
            filter_inovasi_queryset(
                LayananUsulanInovasi.objects.filter(status='usulan'),
                request.user,
            ),
            request.user,
        )
    else:
        layanan_inovasi = _inovasi_notification_values(
            LayananUsulanInovasi.objects.filter(
                pegawai=request.user, status='selesai', is_read=False,
            )
        )
    if request.user.is_sip_admin:
        layanan_sip = _sip_notification_values(
            LayananSIP.objects.filter(status="belum", is_read=False)
        )
    else:
        layanan_sip = _sip_notification_values(
            LayananSIP.objects.filter(
                pegawai=request.user, status="selesai", is_read=False
            )
        )
    if request.user.is_pangkat_admin:
        layanan_pangkat = _pangkat_notification_values(
            LayananNaikPangkat.objects.filter(status='pengajuan')
        )
    else:
        layanan_pangkat = _pangkat_notification_values(
            LayananNaikPangkat.objects.filter(
                pegawai=request.user, status='selesai', is_read=False
            )
        )
    if request.user.is_jabatan_admin:
        layanan_jabatan = _jabatan_notification_values(
            LayananNaikJabatan.objects.filter(status='pengajuan')
        )
    else:
        layanan_jabatan = _jabatan_notification_values(
            LayananNaikJabatan.objects.filter(
                pegawai=request.user, status='selesai', is_read=False
            )
        )

    # Gabungkan semua notifikasi
    notifikasi = list(chain(layanan_cuti_admin, layanan_diklat_admin, layanan_cuti_pegawai, layanan_berkala, layanan_diklat, layanan_inovasi, layanan_sip, layanan_pangkat, layanan_jabatan))

    return {
        'notifikasi_layanan': notifikasi,
        'notif_cuti': layanan_cuti_pegawai,
        'notif_berkala': layanan_berkala,
        'notif_diklat': layanan_diklat,
        'notif_inovasi': layanan_inovasi,
        'notif_sip': layanan_sip,
        'notif_pangkat': layanan_pangkat,
        'notif_jabatan': layanan_jabatan,
        'notif_cuti_admin': layanan_cuti_admin,
        'notif_diklat_admin': layanan_diklat_admin,
        'sip_expiry_notifications': sip_expiry_notifications,
        'str_expiry_notifications': str_expiry_notifications,
        'expiry_notification_total': (
            len(sip_expiry_notifications) + len(str_expiry_notifications)
        ),
        'notification_total': (
            len(notifikasi)
            + len(sip_expiry_notifications)
            + len(str_expiry_notifications)
        ),
        'is_cuti_scope_admin': is_leave_admin(request.user),
    }
    

def runningtext(request):
    agama = None
    data = None
    show_hadist_modal = False
    if request.user.is_authenticated and hasattr(request.user, 'profil_user'):
        agama = request.user.profil_user.agama
    eligible_for_hadist = (
        request.user.is_authenticated
        and (agama == 'Islam' or request.user.is_superuser)
    )
    if eligible_for_hadist:
        data = NasehatdanHadist.objects.order_by("?").first()
        session_key = hadist_modal_session_key(request.user)
        if data is not None and not request.session.get(session_key, False):
            show_hadist_modal = True
    return {
        'agama': agama,
        'hadist': data,
        'show_hadist_modal': show_hadist_modal,
    }
    
    
