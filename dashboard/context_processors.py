from dokumen.models import DokumenSDM
from layanan.models import JenisLayanan, LayananCuti, LayananGajiBerkala, LayananUsulanInovasi, LayananUsulanDiklat
from informasi.models import NasehatdanHadist
from itertools import chain
from django.db.models import Q


def menu_riwayat_sdm(request):
    data_dokumen = DokumenSDM.objects.all().order_by('id')
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
            'notif_inovasi': []
        }

    # === Blok 2: Untuk Superuser (Melihat Semua Notifikasi Pengajuan) ===
    if request.user.is_superuser:
        layanan_cuti = LayananCuti.objects.filter(status="pengajuan").values('id', 'pegawai__first_name', 'pegawai__last_name', 'layanan__url', 'status', 'created_at').order_by('-created_at')
        layanan_berkala = LayananGajiBerkala.objects.filter(status="pengajuan").values('id', 'pegawai__first_name', 'pegawai__last_name', 'layanan__url', 'status', 'created_at')
        layanan_diklat = LayananUsulanDiklat.objects.filter(status="usulan").values('id', 'riwayatdiklat__nama_diklat', 'riwayatdiklat__pegawai__first_name', 'layanan__url', 'status', 'created_at')
        layanan_inovasi = LayananUsulanInovasi.objects.filter(status="usulan").values('id', 'pegawai__first_name', 'pegawai__last_name', 'layanan__url', 'status', 'created_at')
        
        notifikasi = list(chain(layanan_cuti, layanan_berkala, layanan_diklat, layanan_inovasi))
        return {
            'notifikasi_layanan': notifikasi, 'notif_cuti': layanan_cuti, 'notif_berkala': layanan_berkala,
            'notif_diklat': layanan_diklat, 'notif_inovasi': layanan_inovasi,
            'notif_cuti_admin': [], 'notif_diklat_admin': []
        }

    # === Blok 3: Untuk User Biasa dan Admin Hirarki ===
    # Inisialisasi awal agar tidak terjadi NameError jika kondisi tidak terpenuhi
    layanan_cuti_admin = LayananCuti.objects.none()
    layanan_diklat_admin = LayananUsulanDiklat.objects.none()

    # Query notifikasi untuk admin hirarki (jika user adalah staff)
    if request.user.is_staff and hasattr(request.user, 'profil_admin'):
        from strukturorg.models import SubBidang, Bidang  # Import di dalam fungsi untuk menghindari circular import
        profil_admin = request.user.profil_admin

        # Level 4: Kepala Instalasi
        if profil_admin.instalasi.exists() and profil_admin.is_pejabat:
            instalasi_pks = profil_admin.instalasi.values_list('pk', flat=True)
            layanan_cuti_admin = LayananCuti.objects.filter(
                status="pengajuan", 
                pegawai__riwayat_penempatan__penempatan_level4__in=instalasi_pks, 
                pegawai__riwayat_penempatan__status=True
            )
            layanan_diklat_admin = LayananUsulanDiklat.objects.filter(
                status="usulan", 
                riwayatdiklat__pegawai__riwayat_penempatan__penempatan_level4__in=instalasi_pks, 
                riwayatdiklat__pegawai__riwayat_penempatan__status=True
            ).distinct()

        # Level 3: Kepala Seksi/Sub-Bagian
        elif profil_admin.sub_bidang.exists() and profil_admin.is_pejabat:
            # Perbaikan typo: values_list & flat=True
            sub_bidang_pks = profil_admin.sub_bidang.values_list('pk', flat=True)
            layanan_cuti_admin = LayananCuti.objects.filter(
                status="pengajuan", 
                pegawai__riwayat_penempatan__penempatan_level3__in=sub_bidang_pks, 
                pegawai__riwayat_penempatan__status=True
            ).exclude(pegawai=request.user)
            
            layanan_diklat_admin = LayananUsulanDiklat.objects.filter(
                status="usulan", 
                riwayatdiklat__pegawai__riwayat_penempatan__penempatan_level3__in=sub_bidang_pks, 
                riwayatdiklat__pegawai__riwayat_penempatan__status=True
            ).distinct()

        # Level 2: Kepala Bidang (UPDATED)
        elif profil_admin.bidang.exists() and profil_admin.is_pejabat:
            # 1. Ambil semua PK bidang yang ditekuni admin ini
            bidang_pks = profil_admin.bidang.values_list('pk', flat=True)
            
            # 2. Cari semua SubBidang yang berada di bawah bidang-bidang tersebut
            sub_bidangs = SubBidang.objects.filter(bidang__in=bidang_pks)
            
            # 3. Ambil pimpinan_ids (Kepala Seksi/Sub-Bagian) dari sub-bidang terkait
            pimpinan_ids = list(sub_bidangs.values_list('nama_pimpinan_id', flat=True).distinct())

            # Filter Cuti: Bawahan di penempatan level 3 ATAU user pimpinan itu sendiri
            q_filter = Q(pegawai__riwayat_penempatan__penempatan_level3__in=sub_bidangs) | Q(pegawai_id__in=pimpinan_ids)
            layanan_cuti_admin = LayananCuti.objects.filter(
                q_filter, 
                status="pengajuan", 
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
        elif profil_admin.unor.exists() and profil_admin.is_pejabat:
            # 1. Ambil semua PK unor yang ditekuni admin ini
            unor_pks = profil_admin.unor.values_list('pk', flat=True)
            
            # 2. Cari semua Bidang yang berada di bawah unor-unor tersebut
            bidangs = Bidang.objects.filter(unor__in=unor_pks)
            
            # 3. Ambil pimpinan_ids (Kepala Bidang) dari bidang terkait
            pimpinan_ids = list(bidangs.values_list('nama_pimpinan_id', flat=True).distinct())

            # Filter Cuti: Bawahan di penempatan level 2 ATAU pimpinan bidang terkait
            q_filter = Q(pegawai__riwayat_penempatan__penempatan_level2__in=bidangs) | Q(pegawai__id__in=pimpinan_ids)
            layanan_cuti_admin = LayananCuti.objects.filter(
                q_filter, 
                status="pengajuan", 
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

    # Query notifikasi untuk pegawai (pribadi)
    layanan_cuti_pegawai = LayananCuti.objects.filter(pegawai=request.user, status="selesai", is_read=False)
    layanan_berkala = LayananGajiBerkala.objects.filter(pegawai=request.user, status="selesai", is_read=False)
    layanan_diklat = LayananUsulanDiklat.objects.filter(riwayatdiklat__pegawai=request.user, status="selesai", is_read=False)
    layanan_inovasi = LayananUsulanInovasi.objects.filter(pegawai=request.user, status="selesai", is_read=False)

    # Gabungkan semua notifikasi
    notifikasi = list(chain(layanan_cuti_admin, layanan_diklat_admin, layanan_cuti_pegawai, layanan_berkala, layanan_diklat, layanan_inovasi))

    return {
        'notifikasi_layanan': notifikasi,
        'notif_cuti': layanan_cuti_pegawai,
        'notif_berkala': layanan_berkala,
        'notif_diklat': layanan_diklat,
        'notif_inovasi': layanan_inovasi,
        'notif_cuti_admin': layanan_cuti_admin,
        'notif_diklat_admin': layanan_diklat_admin
    }
    

def runningtext(request):
    agama = None
    data = None
    if request.user and hasattr(request.user, 'profil_user'):
        agama = request.user.profil_user.agama
    if agama == 'Islam':
        data = NasehatdanHadist.objects.order_by("?").first()
    return {
        'agama':agama,
        'hadist':data
    }
    
    
