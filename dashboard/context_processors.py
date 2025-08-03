from dokumen.models import DokumenSDM
from layanan.models import JenisLayanan, LayananCuti, LayananGajiBerkala, LayananUsulanInovasi, LayananUsulanDiklat
from informasi.models import NasehatdanHadist
from itertools import chain


def menu_riwayat_sdm(request):
    data_dokumen = DokumenSDM.objects.all().order_by('id')
    return {'data_dokumen': data_dokumen}

def menu_layanan_sdm(request):
    data_layanan = JenisLayanan.objects.filter(status=True).order_by('id')
    status_cuti = ['riwayat', 'baru', 'tunda', 'ambil-tunda']
    return {'data_layanan': data_layanan, 'status_cuti':status_cuti}


def notifikasi_layanan(request):
    if request.user.is_superuser:
        layanan_cuti = LayananCuti.objects.filter(status="pengajuan").values('id', 'pegawai__first_name', 'pegawai__last_name', 'pegawai__profil_user__nip', 'layanan__url', 'status', 'verifikasicuti__persetujuan3', 'created_at').order_by('-created_at')
        layanan_berkala = LayananGajiBerkala.objects.filter(status="pengajuan").values('id', 'pegawai__first_name', 'pegawai__last_name', 'pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')
        layanan_diklat = LayananUsulanDiklat.objects.filter(status="usulan").values('id', 'riwayatdiklat__nama_diklat', 'riwayatdiklat__pegawai__first_name', 'riwayatdiklat__pegawai__last_name', 'riwayatdiklat__pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')
        layanan_inovasi = LayananUsulanInovasi.objects.filter(status="usulan").values('id', 'pegawai__first_name', 'pegawai__last_name', 'pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')
        notifikasi = list(chain(layanan_cuti, layanan_berkala, layanan_diklat, layanan_inovasi))
        return {
            'notifikasi_layanan':notifikasi, 
            'notif_cuti':layanan_cuti,
            'notif_berkala':layanan_berkala,
            'notif_diklat':layanan_diklat,
            'notif_inovasi':layanan_inovasi,
            'notif_cuti_admin': [], 
            'notif_diklat_admin':[]
            }
    elif request.user.is_authenticated:
        layanan_cuti_admin = []
        layanan_diklat_admin = []
        if request.user.is_staff:
            if request.user.profil_admin.instalasi.exists():
                layanan_cuti_admin = LayananCuti.objects.filter(status="pengajuan", pegawai__riwayatpenempatan__penempatan_level4__in=request.user.profil_admin.instalasi.values_list('pk', flat=True), pegawai__riwayatpenempatan__status=True).values('id', 'pegawai__first_name', 'pegawai__last_name', 'layanan__url', 'status', 'verifikasicuti__persetujuan3', 'created_at').order_by('-created_at')
                layanan_diklat_admin = LayananUsulanDiklat.objects.filter(status="usulan", riwayatdiklat__pegawai__riwayatpenempatan__penempatan_level4__in=request.user.profil_admin.instalasi.values_list('pk', flat=True), riwayatdiklat__pegawai__riwayatpenempatan__status=True).distinct().values('id', 'riwayatdiklat__nama_diklat', 'riwayatdiklat__pegawai__first_name', 'riwayatdiklat__pegawai__last_name', 'riwayatdiklat__pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')
            elif request.user.profil_admin.sub_bidang:
                layanan_cuti_admin = LayananCuti.objects.filter(status="pengajuan", pegawai__riwayatpenempatan__penempatan_level3=request.user.profil_admin.sub_bidang, pegawai__riwayatpenempatan__status=True).values('id', 'pegawai__first_name', 'pegawai__last_name', 'layanan__url', 'status', 'verifikasicuti__persetujuan3', 'created_at').order_by('-created_at')
                layanan_diklat_admin = LayananUsulanDiklat.objects.filter(status="usulan", riwayatdiklat__pegawai__riwayatpenempatan__penempatan_level3=request.user.profil_admin.sub_bidang, riwayatdiklat__pegawai__riwayatpenempatan__status=True).values('id', 'riwayatdiklat__nama_diklat', 'riwayatdiklat__pegawai__first_name', 'riwayatdiklat__pegawai__last_name', 'riwayatdiklat__pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')
            elif request.user.profil_admin.bidang:
                layanan_cuti_admin = LayananCuti.objects.filter(status="pengajuan", pegawai__riwayatpenempatan__penempatan_level2=request.user.profil_admin.bidang, pegawai__riwayatpenempatan__status=True, verifikasicuti__persetujuan1=True).values('id', 'pegawai__first_name', 'pegawai__last_name', 'layanan__url', 'status', 'verifikasicuti__persetujuan3', 'created_at').order_by('-created_at')
                layanan_diklat_admin = LayananUsulanDiklat.objects.filter(status="usulan", riwayatdiklat__pegawai__riwayatpenempatan__penempatan_level2=request.user.profil_admin.bidang, riwayatdiklat__pegawai__riwayatpenempatan__status=True).values('id', 'riwayatdiklat__nama_diklat', 'riwayatdiklat__pegawai__first_name', 'riwayatdiklat__pegawai__last_name', 'riwayatdiklat__pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')
            elif request.user.profil_admin.unor:
                layanan_cuti_admin = LayananCuti.objects.filter(status="pengajuan", pegawai__riwayatpenempatan__penempatan_level1=request.user.profil_admin.unor, pegawai__riwayatpenempatan__status=True, verifikasicuti__persetujuan2=True).values('id', 'pegawai__first_name', 'pegawai__last_name', 'layanan__url', 'status', 'verifikasicuti__persetujuan3', 'created_at').order_by('-created_at')
                layanan_diklat_admin = LayananUsulanDiklat.objects.filter(status="usulan", riwayatdiklat__pegawai__riwayatpenempatan__penempatan_level1=request.user.profil_admin.unor, riwayatdiklat__pegawai__riwayatpenempatan__status=True).values('id', 'riwayatdiklat__nama_diklat', 'riwayatdiklat__pegawai__first_name', 'riwayatdiklat__pegawai__last_name', 'riwayatdiklat__pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')        
        layanan_cuti_pegawai = LayananCuti.objects.filter(status="selesai", pegawai=request.user, is_read=False).values('id', 'pegawai__first_name', 'pegawai__last_name', 'pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')
        layanan_berkala = LayananGajiBerkala.objects.filter(status="selesai", pegawai=request.user, is_read=False).values('id', 'pegawai__first_name', 'pegawai__last_name', 'pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')
        layanan_diklat = LayananUsulanDiklat.objects.filter(status="selesai", riwayatdiklat__pegawai=request.user, is_read=False).values('id', 'riwayatdiklat__nama_diklat', 'riwayatdiklat__pegawai__first_name', 'riwayatdiklat__pegawai__last_name', 'riwayatdiklat__pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')
        layanan_inovasi = LayananUsulanInovasi.objects.filter(status="selesai", pegawai=request.user, is_read=False).values('id', 'pegawai__first_name', 'pegawai__last_name', 'pegawai__profil_user__nip', 'layanan__url', 'status', 'created_at')
        notifikasi = list(chain(layanan_cuti_admin, layanan_cuti_pegawai, layanan_berkala, layanan_diklat_admin, layanan_diklat, layanan_inovasi))
        return {
            'notifikasi_layanan':notifikasi, 
            'notif_cuti':layanan_cuti_pegawai, 
            'notif_berkala':layanan_berkala,
            'notif_diklat':layanan_diklat,
            'notif_inovasi':layanan_inovasi,
            'notif_cuti_admin': layanan_cuti_admin,
            'notif_diklat_admin':layanan_diklat_admin
            }
    else:
        return {
            'notifikasi_layanan':[], 
            'notif_cuti':[], 
            'notif_cuti_admin':[],
            'notif_berkala':[],
            'notif_diklat':[],
            'notif_inovasi':[]
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