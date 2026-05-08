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