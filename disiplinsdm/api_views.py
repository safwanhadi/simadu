from datetime import date

from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from oauth2_provider.contrib.rest_framework.permissions import IsAuthenticatedOrTokenHasScope

from .models import ApprovedJadwalDinasSDM


class JadwalDokterSerializer(ModelSerializer):
    """Data jadwal dokter yang dapat dipakai sebagai nilai awal di Mandacare."""

    dokter_id = SerializerMethodField()
    nama_dokter = SerializerMethodField()
    nama_lengkap_dokter = SerializerMethodField()
    nik = SerializerMethodField()
    nip = SerializerMethodField()
    identitas_valid = SerializerMethodField()
    instalasi = SerializerMethodField()
    kategori_jadwal = SerializerMethodField()
    waktu_mulai = SerializerMethodField()
    waktu_selesai = SerializerMethodField()

    class Meta:
        model = ApprovedJadwalDinasSDM
        fields = (
            'id', 'tanggal', 'dokter_id', 'nama_dokter',
            'nama_lengkap_dokter', 'nik', 'nip', 'identitas_valid',
            'instalasi', 'kategori_jadwal', 'waktu_mulai',
            'waktu_selesai', 'catatan',
        )

    @staticmethod
    def _dokter(obj):
        return obj.pegawai.pegawai

    def get_dokter_id(self, obj):
        return self._dokter(obj).pk

    def get_nama_dokter(self, obj):
        return self._dokter(obj).full_name_2

    def get_nama_lengkap_dokter(self, obj):
        return self._dokter(obj).full_name_2

    def get_nik(self, obj):
        profil = getattr(self._dokter(obj), 'profil_user', None)
        return profil.no_ktp or None if profil else None

    def get_nip(self, obj):
        profil = getattr(self._dokter(obj), 'profil_user', None)
        return profil.nip or None if profil else None

    def get_identitas_valid(self, obj):
        """True hanya bila NIK dan NIP tersedia untuk pencocokan sistem tujuan."""
        return bool(self.get_nik(obj) and self.get_nip(obj))

    def get_instalasi(self, obj):
        instalasi = obj.pegawai.instalasi
        return instalasi.instalasi if instalasi else None

    def get_kategori_jadwal(self, obj):
        return obj.kategori_jadwal.kategori_jadwal if obj.kategori_jadwal else None

    def get_waktu_mulai(self, obj):
        return obj.kategori_jadwal.waktu_datang if obj.kategori_jadwal else None

    def get_waktu_selesai(self, obj):
        return obj.kategori_jadwal.waktu_pulang if obj.kategori_jadwal else None


class JadwalDokterAPIView(ListAPIView):
    """Menyediakan jadwal dokter berstatus disetujui untuk integrasi Mandacare.

    Tanpa parameter, endpoint mengembalikan jadwal hari ini. Gunakan ``tanggal``
    atau pasangan ``mulai`` dan ``sampai`` (format YYYY-MM-DD) untuk jadwal pada
    tanggal atau rentang tertentu. Hasil dapat disaring lagi menggunakan
    ``dokter_id``, ``nik``, ``nip``, dan ``instalasi``.
    """

    authentication_classes = [OAuth2Authentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ['read:listpegawai']
    serializer_class = JadwalDokterSerializer
    pagination_class = None

    def _tanggal_parameter(self, nama):
        nilai = self.request.query_params.get(nama)
        if not nilai:
            return None
        tanggal = parse_date(nilai)
        if not tanggal:
            raise ValidationError({nama: 'Gunakan format tanggal YYYY-MM-DD.'})
        return tanggal

    def _filter_teks(self, queryset, parameter, lookup):
        nilai = self.request.query_params.get(parameter)
        if nilai and nilai.strip():
            return queryset.filter(**{lookup: nilai.strip()})
        return queryset

    def get_queryset(self):
        tanggal = self._tanggal_parameter('tanggal')
        mulai = self._tanggal_parameter('mulai')
        sampai = self._tanggal_parameter('sampai')

        if tanggal and (mulai or sampai):
            raise ValidationError(
                'Parameter tanggal tidak dapat digunakan bersama mulai atau sampai.'
            )
        if mulai and sampai and mulai > sampai:
            raise ValidationError({'sampai': 'Tanggal selesai harus sama atau setelah tanggal mulai.'})

        queryset = (
            ApprovedJadwalDinasSDM.objects
            .filter(
                is_approved=True,
                pegawai__status='disetujui',
            )
            .filter(
                Q(pegawai__jenis_sdm__jenis_sdm__icontains='dokter')
                | Q(pegawai__jenis_sdm__profesi__profesi__icontains='dokter')
            )
            .select_related(
                'pegawai__pegawai__profil_user',
                'pegawai__instalasi',
                'kategori_jadwal',
            )
            .order_by('tanggal', 'kategori_jadwal__waktu_datang', 'pk')
        )

        if tanggal:
            queryset = queryset.filter(tanggal=tanggal)
        elif mulai:
            queryset = queryset.filter(tanggal__gte=mulai)
        if sampai:
            queryset = queryset.filter(tanggal__lte=sampai)
        if not tanggal and not mulai and not sampai:
            queryset = queryset.filter(tanggal=date.today())

        dokter_id = self.request.query_params.get('dokter_id')
        if dokter_id:
            if not dokter_id.isdigit():
                raise ValidationError({'dokter_id': 'Gunakan ID dokter berupa angka.'})
            queryset = queryset.filter(pegawai__pegawai_id=dokter_id)

        queryset = self._filter_teks(
            queryset, 'nik', 'pegawai__pegawai__profil_user__no_ktp'
        )
        queryset = self._filter_teks(
            queryset, 'nip', 'pegawai__pegawai__profil_user__nip'
        )
        queryset = self._filter_teks(
            queryset, 'instalasi', 'pegawai__instalasi__instalasi__iexact'
        )
        return queryset
