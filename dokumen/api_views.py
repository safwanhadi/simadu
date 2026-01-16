from django.core.cache import cache
from django.db.models import OuterRef, Subquery, F
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import RiwayatPendidikan, RiwayatJabatan
from .serializers import PendidikanSerializer, JabatanSerializer

class PendidikanAPIView(APIView):
    def get(self, request):
        nip = request.GET.get('nip')
        cache_key = f"pendidikan_api:{nip or 'all'}"
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
        if nip:
            queryset = queryset.filter(pegawai__profil_user__nip=nip)
        serializer = PendidikanSerializer(queryset, many=True)
        cache.set(cache_key, serializer.data, timeout=300)
        return Response(serializer.data)


class JabatanAPIView(APIView):
    def get(self, request):
        nip = request.GET.get('nip')
        cache_key = f"jabatan_api:{nip or 'all'}"
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
        if nip:
            queryset = queryset.filter(pegawai__profil_user__nip=nip)
        serializer = JabatanSerializer(queryset, many=True)
        cache.set(cache_key, serializer.data, timeout=300)
        return Response(serializer.data)