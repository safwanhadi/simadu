from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.cache import cache
from django.db.models import OuterRef, Subquery, F
from django.db.models.functions import Coalesce

from .models import Users
from .serializers import PegawaiSerializer
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


    
class PegawaiAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        nip = request.GET.get('nip')
        cache_key = f"pegawai_api:{nip or 'all'}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
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
        queryset = Users.objects.select_related('profil_user', 'profil_user__gender').annotate(
            pendidikan_terakhir_jenjang=Subquery(latest_pendidikan.values('level_pend')[:1]),
            pendidikan_terakhir_institusi=Subquery(latest_pendidikan.values('nama_sek')[:1]),
            pendidikan_terakhir_tahun_lulus=Subquery(latest_pendidikan.values('tgl_lulus')[:1]),
            pendidikan_terakhir_nomor_ijazah=Subquery(latest_pendidikan.values('no_ijazah')[:1]),
            jabatan_terakhir=Coalesce(
                Subquery(latest_jabatan.values('detail_nama_jabatan')[:1]),
                Subquery(latest_jabatan.values('nama_jabatan__jenis_sdm')[:1]),
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
        if nip:
            queryset = queryset.filter(profil_user__nip=nip)
        serializer = PegawaiSerializer(queryset, many=True)
        cache.set(cache_key, serializer.data, timeout=300)
        return Response(serializer.data)