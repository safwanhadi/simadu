from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, get_object_or_404
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.authentication import SessionAuthentication
from datetime import date
from django.db.models import F, OuterRef, Subquery, Prefetch, Value, Case, When, BooleanField
from django.db.models.functions import Coalesce
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

# Pastikan import model Anda sudah benar sesuai struktur aplikasi

from .models import Users, ProfilSDM
from strukturorg.models import UnitOrganisasi, Bidang, SubBidang
from disiplinsdm.models import JenisSDMPerinstalasi
from .serializers import DataMinimalPegawaiSerializer, PegawaiSerializer, DokterSpesialisSerializer
from dokumen.models import RiwayatPanggol, RiwayatPendidikan, RiwayatPenempatan, RiwayatJabatan


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_me(request):
    """
    Endpoint userinfo untuk OAuth2 client (REMUN, dll).
    Hanya mengembalikan identitas dasar.
    """
    user = request.user  # ini instance Users (custom Anda)
    profil = getattr(user, "profil_user", None)

    return Response({
        "id": user.pk,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name_2,
        "nip": getattr(profil, "nip", None),
        "is_active": user.is_active,
        "is_staff": user.is_staff,
    })
    

class DetailMeAPIView(APIView):
    """
    Menu ini mengembalikan data pegawai yang sedang login dengan informasi yang lebih lengkap dibanding api_me.
    bisa digunakan sebagai bahan untuk menentukan role pegawai.
    """
    authentication_classes = [OAuth2Authentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    # Matikan filter backend otomatis jika ada global setting
    filter_backends = [] 

    def get_queryset(self):
        now = date.today()
        try:
            bulan = int(self.request.GET.get("bulan") or now.month)
            tahun = int(self.request.GET.get("tahun") or now.year)
        except ValueError:
            bulan = now.month
            tahun = now.year

        # 1. Subquery untuk mencari jabatan terakhir pegawai
        latest_jabatan = RiwayatJabatan.objects.filter(
            pegawai=OuterRef('pk')
        ).order_by(
            F('tmt_jabatan').desc(nulls_last=True),
            '-created_at',
            '-id',
        )
        
        # 2. Subquery untuk mencari penempatan aktif terakhir pegawai
        latest_penempatan = RiwayatPenempatan.objects.filter(
            pegawai=OuterRef('pk'),
            status=True,
        ).order_by(
            F('tgl_sk').desc(nulls_last=True),
            '-created_at',
            '-id',
        )
        
        # 3. Subquery evaluasi struktural pimpinan jika pegawai merupakan pejabat
        direktur = UnitOrganisasi.objects.filter(nama_pimpinan=OuterRef('pk'))
        bidang = Bidang.objects.filter(nama_pimpinan=OuterRef('pk'))
        sub_bidang = SubBidang.objects.filter(nama_pimpinan=OuterRef('pk'))

        # 4. Prefetch kustom
        jsdm_qs = (
            JenisSDMPerinstalasi.objects
            .filter(bulan=bulan, tahun=tahun)
            .prefetch_related('jadwaldinassdm_set__kategori_jadwal')
            .order_by('-updated_at', '-id')
        )

        # 5. Query Utama
        qs = (
            Users.objects
            .select_related('profil_user', 'profil_user__gender')
            .prefetch_related(
                'unitorganisasi_set', 
                'bidang_set', 
                'subbidang_set',
                Prefetch(
                    'jenissdmperinstalasi_set',
                    queryset=jsdm_qs,
                    to_attr='jsdm_bulan_ini'
                )
            )
            .annotate(
                data_pejabat=Coalesce(
                    Subquery(direktur.values('unor')[:1]),
                    Subquery(bidang.values('bidang')[:1]),
                    Subquery(sub_bidang.values('sub_bidang')[:1]),
                    default=None
                ),
                jabatan_terakhir=Coalesce(
                    Subquery(latest_jabatan.values('nama_jabatan__jenis_sdm')[:1]),
                    Subquery(latest_jabatan.values('detail_nama_jabatan')[:1]),
                ),
                penempatan_saat_ini=Coalesce(
                    Subquery(latest_penempatan.values('penempatan_level4__instalasi')[:1]),
                    Subquery(latest_penempatan.values('penempatan_level3__sub_bidang')[:1]),
                    Subquery(latest_penempatan.values('penempatan_level2__bidang')[:1]),
                    Subquery(latest_penempatan.values('penempatan_level1__unor')[:1]),
                    Subquery(latest_penempatan.values('unit_sebelumnya')[:1]),
                    Subquery(latest_penempatan.values('seksi_sebelumnya')[:1]),
                    Subquery(latest_penempatan.values('bidang_sebelumnya')[:1]),
                    Subquery(latest_penempatan.values('instansi_sebelumnya')[:1]),
                ),
            ).annotate(
                pejabat=Case(
                    When(data_pejabat__isnull=False, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                )
            )
        )
        return qs

    # --- UBAH METHOD MENJADI 'get' ---
    def get(self, request, *args, **kwargs):
        """
        Mengambil data pegawai berdasarkan user yang sedang login
        """
        logged_in_user = request.user
        queryset = self.get_queryset()
        instance = get_object_or_404(queryset, pk=logged_in_user.id)
        serializer = DataMinimalPegawaiSerializer(
            instance, context={"request": request}
        )
        return Response(serializer.data)
    

class PegawaiAPIView(ListAPIView):
    authentication_classes = [OAuth2Authentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = PegawaiSerializer

    def get_queryset(self):
        nip = self.request.GET.get("nip")

        # bulan/tahun untuk ambil JenisSDMPerinstalasi
        now = date.today()
        bulan = int(self.request.GET.get("bulan") or now.month)
        tahun = int(self.request.GET.get("tahun") or now.year)

        latest_pendidikan = RiwayatPendidikan.objects.filter(
            pegawai=OuterRef('pk')
        ).order_by(
            F('tgl_lulus').desc(nulls_last=True),
            '-created_at',
            '-id',
        )
        latest_jabatan = RiwayatJabatan.objects.filter(
            pegawai=OuterRef('pk')
        ).order_by(
            F('tmt_jabatan').desc(nulls_last=True),
            '-created_at',
            '-id',
        )
        latest_penempatan = RiwayatPenempatan.objects.filter(
            pegawai=OuterRef('pk'),
            status=True,
        ).order_by(
            F('tgl_sk').desc(nulls_last=True),
            '-created_at',
            '-id',
        )
        latest_panggol = RiwayatPanggol.objects.filter(
            pegawai=OuterRef('pk')
        ).order_by(
            F('tmt_gol').desc(nulls_last=True),
            '-created_at',
            '-id',
        )

        # Prefetch JenisSDMPerinstalasi untuk bulan/tahun tsb + jadwal & kategori_jadwal
        jsdm_qs = (
            JenisSDMPerinstalasi.objects
            .filter(bulan=bulan, tahun=tahun)
            .prefetch_related('jadwaldinassdm_set__kategori_jadwal')
            .order_by('-updated_at', '-id')
        )

        qs = (
            Users.objects
            .select_related('profil_user', 'profil_user__gender')
            .prefetch_related(
                Prefetch(
                    'jenissdmperinstalasi_set',  # default related_name
                    queryset=jsdm_qs,
                    to_attr='jsdm_bulan_ini'      # nanti jadi attribute list di obj Users
                )
            )
            .annotate(
                pendidikan_terakhir_jenjang=Subquery(latest_pendidikan.values('level_pend')[:1]),
                pendidikan_terakhir_institusi=Subquery(latest_pendidikan.values('nama_sek')[:1]),
                pendidikan_terakhir_tahun_lulus=Subquery(latest_pendidikan.values('tgl_lulus')[:1]),
                pendidikan_terakhir_nomor_ijazah=Subquery(latest_pendidikan.values('no_ijazah')[:1]),
                jabatan_terakhir=Coalesce(
                    Subquery(latest_jabatan.values('nama_jabatan__jenis_sdm')[:1]),
                    Subquery(latest_jabatan.values('detail_nama_jabatan')[:1]),
                ),
                jabatan=Subquery(latest_jabatan.values('jns_jabatan')[:1]),
                penempatan_saat_ini=Coalesce(
                    Subquery(latest_penempatan.values('penempatan_level4__instalasi')[:1]),
                    Subquery(latest_penempatan.values('penempatan_level3__sub_bidang')[:1]),
                    Subquery(latest_penempatan.values('penempatan_level2__bidang')[:1]),
                    Subquery(latest_penempatan.values('penempatan_level1__unor')[:1]),
                    Subquery(latest_penempatan.values('unit_sebelumnya')[:1]),
                    Subquery(latest_penempatan.values('seksi_sebelumnya')[:1]),
                    Subquery(latest_penempatan.values('bidang_sebelumnya')[:1]),
                    Subquery(latest_penempatan.values('instansi_sebelumnya')[:1]),
                ),
                pangkat_golongan_pangkat=Subquery(latest_panggol.values('panggol__pangkat')[:1]),
                pangkat_golongan_golongan=Subquery(latest_panggol.values('panggol__golongan')[:1]),
                pangkat_golongan_ruang=Subquery(latest_panggol.values('panggol__ruang')[:1]),
            )
        )

        if nip:
            qs = qs.filter(profil_user__nip=nip)

        return qs

    def list(self, request, *args, **kwargs):
        nip = request.GET.get("nip") or "all"
        page = request.GET.get("page") or "1"
        page_size = request.GET.get("page_size") or ""
        bulan = request.GET.get("bulan") or ""
        tahun = request.GET.get("tahun") or ""

        cache_key = f"pegawai_api:{nip}:bulan={bulan}:tahun={tahun}:page={page}:ps={page_size}"

        # cached = cache.get(cache_key)
        # if cached is not None:
        #     return Response(cached)

        response = super().list(request, *args, **kwargs)
        # cache.set(cache_key, response.data, timeout=300)
        return response


class DokterSpesialisAPIView(ListAPIView):
    authentication_classes = [OAuth2Authentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = DokterSpesialisSerializer

    def get_queryset(self):
        qs = Users.objects.select_related('profil_user').filter(
            profil_user__is_dokter_spesialis=True)
        return qs