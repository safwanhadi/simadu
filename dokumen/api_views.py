from django.core.cache import cache
from django.db.models import Count, F, Max, OuterRef, Subquery
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import RiwayatPendidikan, RiwayatJabatan
from .serializers import PendidikanSerializer, JabatanSerializer


def _cache_revision(model):
    """Buat versi cache yang berubah saat data model ditambah/diubah/dihapus."""
    revision = model.objects.aggregate(
        total=Count('pk'),
        last_id=Max('pk'),
        last_update=Max('updated_at'),
    )
    last_update = revision['last_update']
    timestamp = last_update.timestamp() if last_update else 0
    return f"{revision['total']}:{revision['last_id'] or 0}:{timestamp}"

class PendidikanAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_admin = request.user.is_dokumen_admin
        nip = (request.GET.get('nip') or '').strip() if is_admin else None
        scope_key = f"admin:{nip or 'all'}" if is_admin else f"user:{request.user.pk}"
        cache_key = (
            f"pendidikan_api:{_cache_revision(RiwayatPendidikan)}:{scope_key}"
        )
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        latest_pendidikan = RiwayatPendidikan.objects.filter(
            pegawai=OuterRef('pegawai')
        ).order_by(
            F('tgl_lulus').desc(nulls_last=True),
            '-created_at',
            '-id',
        ).values('id')[:1]
        queryset = RiwayatPendidikan.objects.select_related(
            'pegawai',
            'pegawai__profil_user',
        ).filter(
            id=Subquery(latest_pendidikan)
        )
        if is_admin and nip:
            queryset = queryset.filter(pegawai__profil_user__nip=nip)
        elif not is_admin:
            queryset = queryset.filter(pegawai=request.user)
        serializer = PendidikanSerializer(queryset, many=True)
        cache.set(cache_key, serializer.data, timeout=300)
        return Response(serializer.data)


class JabatanAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_admin = request.user.is_dokumen_admin
        nip = (request.GET.get('nip') or '').strip() if is_admin else None
        scope_key = f"admin:{nip or 'all'}" if is_admin else f"user:{request.user.pk}"
        cache_key = f"jabatan_api:{_cache_revision(RiwayatJabatan)}:{scope_key}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        latest_jabatan = RiwayatJabatan.objects.filter(
            pegawai=OuterRef('pegawai')
        ).order_by(
            F('tmt_jabatan').desc(nulls_last=True),
            '-created_at',
            '-id',
        ).values('id')[:1]
        queryset = RiwayatJabatan.objects.select_related(
            'pegawai',
            'pegawai__profil_user',
            'nama_jabatan',
            'unor',
            'bidang',
            'sub_bidang',
            'instalasi',
        ).filter(
            id=Subquery(latest_jabatan)
        )
        if is_admin and nip:
            queryset = queryset.filter(pegawai__profil_user__nip=nip)
        elif not is_admin:
            queryset = queryset.filter(pegawai=request.user)
        serializer = JabatanSerializer(queryset, many=True)
        cache.set(cache_key, serializer.data, timeout=300)
        return Response(serializer.data)
