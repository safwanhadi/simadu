from rest_framework import serializers
from .models import SubBidang, UnitInstalasi

class SubBidangSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubBidang
        fields = '__all__'

class UnitInstalasiSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitInstalasi
        fields = '__all__'
        
class PenempatanSerializer(serializers.ModelSerializer):
    # Menembus relasi object yang sudah ditarik oleh select_related
    unor = serializers.ReadOnlyField(source='sub_bidang.bidang.unor.unor')
    bidang = serializers.ReadOnlyField(source='sub_bidang.bidang.bidang')
    sub_bidang_nama = serializers.ReadOnlyField(source='sub_bidang.sub_bidang')
    unitinstalasi = serializers.ReadOnlyField(source='instalasi')
    instalasi_slug = serializers.ReadOnlyField(source='slug')

    class Meta:
        model = UnitInstalasi
        fields = ['id', 'unor', 'bidang', 'sub_bidang_nama', 'unitinstalasi', 'instalasi_slug']