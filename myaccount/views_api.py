from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.authentication import SessionAuthentication

from django.core.cache import cache
from django.db.models import OuterRef, Subquery, F, Prefetch
from django.db.models.functions import Coalesce
from datetime import date
from django.utils import timezone

from .models import Users
from disiplinsdm.models import JenisSDMPerinstalasi
from .serializers import PegawaiSerializer, DokterSpesialisSerializer
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