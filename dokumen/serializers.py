from rest_framework import serializers

from .models import RiwayatPendidikan, RiwayatJabatan


class PendidikanSerializer(serializers.ModelSerializer):
    pegawai = serializers.IntegerField(source="pegawai_id")
    jenjang = serializers.CharField(source="level_pend")
    institusi = serializers.CharField(source="nama_sek")
    tahun_lulus = serializers.SerializerMethodField()
    nomor_ijazah = serializers.CharField(source="no_ijazah")

    class Meta:
        model = RiwayatPendidikan
        fields = (
            "pegawai",
            "jenjang",
            "institusi",
            "tahun_lulus",
            "nomor_ijazah",
        )

    def get_tahun_lulus(self, obj):
        return obj.tgl_lulus.year if obj.tgl_lulus else None


class JabatanSerializer(serializers.ModelSerializer):
    pegawai = serializers.IntegerField(source="pegawai_id")
    jenis_jabatan = serializers.CharField(source="jns_jabatan")
    nama_jabatan = serializers.SerializerMethodField()
    unit_kerja = serializers.SerializerMethodField()
    tanggal_mulai = serializers.DateField(source="tmt_jabatan")
    tanggal_selesai = serializers.DateField(source="tgl_srt_pemberhentian")
    is_struktural = serializers.SerializerMethodField()

    class Meta:
        model = RiwayatJabatan
        fields = (
            "pegawai",
            "jenis_jabatan",
            "nama_jabatan",
            "unit_kerja",
            "tanggal_mulai",
            "tanggal_selesai",
            "is_struktural",
        )

    def get_nama_jabatan(self, obj):
        if obj.detail_nama_jabatan:
            return obj.detail_nama_jabatan
        if obj.nama_jabatan:
            return obj.nama_jabatan.jenis_sdm
        return None

    def get_unit_kerja(self, obj):
        if obj.instalasi:
            return obj.instalasi.instalasi
        if obj.sub_bidang:
            return obj.sub_bidang.sub_bidang
        if obj.bidang:
            return obj.bidang.bidang
        if obj.unor:
            return obj.unor.unor
        return None

    def get_is_struktural(self, obj):
        return obj.jns_jabatan == "Struktural"