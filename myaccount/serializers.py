from rest_framework import serializers

class PegawaiSerializer(serializers.Serializer):
    nip = serializers.SerializerMethodField()
    nama = serializers.SerializerMethodField()
    jenis_kelamin = serializers.SerializerMethodField()
    tempat_lahir = serializers.SerializerMethodField()
    tanggal_lahir = serializers.SerializerMethodField()
    alamat = serializers.SerializerMethodField()
    no_telepon = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    status_pegawai = serializers.SerializerMethodField()
    tanggal_masuk = serializers.SerializerMethodField()
    user = serializers.IntegerField(source="id")
    pendidikan_terakhir = serializers.SerializerMethodField()
    jabatan_terakhir = serializers.SerializerMethodField()
    penempatan_saat_ini = serializers.SerializerMethodField()
    jabatan = serializers.CharField(allow_null=True)
    pangkat_golongan = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    def get_profile(self, obj):
        return getattr(obj, "profil_user", None)

    def get_nip(self, obj):
        profile = self.get_profile(obj)
        return profile.nip if profile else None

    def get_nama(self, obj):
        return obj.full_name

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

    def get_tempat_lahir(self, obj):
        profile = self.get_profile(obj)
        return profile.tmp_lahir if profile else None

    def get_tanggal_lahir(self, obj):
        profile = self.get_profile(obj)
        return profile.tgl_lahir if profile else None

    def get_alamat(self, obj):
        profile = self.get_profile(obj)
        return profile.alamat if profile else None

    def get_no_telepon(self, obj):
        profile = self.get_profile(obj)
        return profile.no_hp if profile else None

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

    def get_created_at(self, obj):
        profile = self.get_profile(obj)
        return profile.created_at if profile else None

    def get_updated_at(self, obj):
        profile = self.get_profile(obj)
        return profile.updated_at if profile else None