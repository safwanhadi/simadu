from rest_framework import serializers
from django.utils import timezone
from .models import Users, ProfilSDM

class PegawaiSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    nip = serializers.SerializerMethodField()
    nik = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    nama = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    status_pegawai = serializers.SerializerMethodField()
    tanggal_masuk = serializers.SerializerMethodField()
    pendidikan_terakhir = serializers.SerializerMethodField()
    jabatan_terakhir = serializers.SerializerMethodField()
    penempatan_saat_ini = serializers.SerializerMethodField()
    jabatan = serializers.CharField(allow_null=True)
    pangkat_golongan = serializers.SerializerMethodField()
    is_dokter_spesialis = serializers.SerializerMethodField()
    #jam kerja
    selisih_jam_kerja = serializers.SerializerMethodField()
    aktual_jam_bulan = serializers.SerializerMethodField()
    standar_min_efektif = serializers.SerializerMethodField()
    standar_max_efektif = serializers.SerializerMethodField()
    #is_shift
    is_shift = serializers.SerializerMethodField()

    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.id if hasattr(obj, 'id') else None
    
    def get_profile(self, obj):
        return getattr(obj, "profil_user", None)

    def get_nip(self, obj):
        profile = self.get_profile(obj)
        return profile.nip if profile else None
    
    def get_nik(self, obj):
        profile = self.get_profile(obj)
        return profile.no_ktp if profile else None
    
    def get_first_name(self, obj):
        return obj.first_name

    def get_last_name(self, obj):
        return obj.last_name

    def get_nama(self, obj):
        return obj.full_name_2

    def get_jenis_kelamin(self, obj):
        profile = self.get_profile(obj)
        if not profile or not profile.gender:
            return None
        value = profile.gender.jenis_kelamin.strip().lower()
        if value.startswith("l"):
            return "L"
        if value.startswith("p"):
            return "P"
        return None

    def get_email(self, obj):
        return obj.email

    def get_status_pegawai(self, obj):
        return "AKTIF" if obj.is_active else "PENSIUN"

    def get_tanggal_masuk(self, obj):
        profile = self.get_profile(obj)
        if profile and profile.created_at:
            return profile.created_at.date()
        return None
    
    def get_pendidikan_terakhir(self, obj):
        if not obj.pendidikan_terakhir_jenjang and not obj.pendidikan_terakhir_institusi:
            return None
        tahun_lulus = obj.pendidikan_terakhir_tahun_lulus
        if hasattr(tahun_lulus, "year"):
            tahun_lulus = tahun_lulus.year
        return {
            "jenjang": obj.pendidikan_terakhir_jenjang,
            "institusi": obj.pendidikan_terakhir_institusi,
            "tahun_lulus": tahun_lulus,
            "nomor_ijazah": obj.pendidikan_terakhir_nomor_ijazah,
        }

    def get_jabatan_terakhir(self, obj):
        return obj.jabatan_terakhir

    def get_penempatan_saat_ini(self, obj):
        return obj.penempatan_saat_ini

    def get_pangkat_golongan(self, obj):
        if not obj.pangkat_golongan_pangkat and not obj.pangkat_golongan_golongan:
            return None
        ruang = obj.pangkat_golongan_ruang
        golongan = obj.pangkat_golongan_golongan
        if ruang and ruang != "-":
            return f"{obj.pangkat_golongan_pangkat} ({golongan}/{ruang})"
        return f"{obj.pangkat_golongan_pangkat} ({golongan})"
    
    def get_is_dokter_spesialis(self, obj):
        profile = self.get_profile(obj)
        return profile.is_dokter_spesialis if profile else False

    #method jam kerja
    def _get_jsdm_bulan_ini(self, obj):
        # hasil Prefetch(to_attr='jsdm_bulan_ini') berupa list
        jsdm_list = getattr(obj, "jsdm_bulan_ini", None) or []
        return jsdm_list[0] if jsdm_list else None

    def get_selisih_jam_kerja(self, obj):
        jsdm = self._get_jsdm_bulan_ini(obj)
        return jsdm.selisih_jam_kerja if jsdm else None

    def get_aktual_jam_bulan(self, obj):
        jsdm = self._get_jsdm_bulan_ini(obj)
        return jsdm.kurang_lebih_jam_kerja if jsdm else None

    def get_standar_min_efektif(self, obj):
        jsdm = self._get_jsdm_bulan_ini(obj)
        return jsdm.standar_min_efektif if jsdm else None

    def get_standar_max_efektif(self, obj):
        jsdm = self._get_jsdm_bulan_ini(obj)
        return jsdm.standar_max_efektif if jsdm else None
    
    def _get_jsdm_bulan_ini(self, obj):
        jsdm_list = getattr(obj, "jsdm_bulan_ini", None) or []
        return jsdm_list[0] if jsdm_list else None

    def _iter_jadwal(self, obj):
        jsdm = self._get_jsdm_bulan_ini(obj)
        if not jsdm:
            return []
        # jadwaldinassdm_set sudah diprefetch di view
        return list(getattr(jsdm, "jadwaldinassdm_set", []).all())
    
    def get_is_shift(self, obj):
        SHIFT_NAMES = {'Malam'}
        for jd in self._iter_jadwal(obj):
            kj = getattr(jd, "kategori_jadwal", None)
            nama_shift = getattr(kj, "kategori_jadwal", None)
            if nama_shift in SHIFT_NAMES:
                return True
        return False
    
    def _safe_aware_dt(self, dt):
        if not dt:
            return None
        # jika dt sudah aware: aman
        if timezone.is_aware(dt):
            return dt
        # jika dt naive: anggap itu waktu lokal server / TIME_ZONE project
        return timezone.make_aware(dt, timezone.get_current_timezone())

    def get_created_at(self, obj):
        profile = getattr(obj, "profil_user", None)
        return self._safe_aware_dt(getattr(profile, "created_at", None))

    def get_updated_at(self, obj):
        profile = getattr(obj, "profil_user", None)
        return self._safe_aware_dt(getattr(profile, "updated_at", None))
    
    
class DokterSpesialisSerializer(serializers.ModelSerializer):
    # Menggunakan properti full_name dari Custom User model
    # Karena ini properti (bukan field DB), kita gunakan read_only=True
    nama_user = serializers.ReadOnlyField(source='full_name_2')
    
    # Mengambil field dari relasi OneToOne 'profil'
    is_spesialis = serializers.BooleanField(source='profil_user.is_dokter_spesialis', read_only=True)
    nik_user = serializers.CharField(source='profil_user.no_ktp', read_only=True)

    class Meta:
        model = Users
        # Daftarkan field yang Anda butuhkan
        fields = ['id', 'nama_user', 'is_spesialis', 'nik_user']