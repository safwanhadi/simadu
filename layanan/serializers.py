from rest_framework import serializers

from .models import LayananGajiBerkala


class LayananGajiBerkalaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayananGajiBerkala
        fields = ('pegawai', 'layanan', 'riwayat', 'status')