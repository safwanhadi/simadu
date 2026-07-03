from rest_framework.generics import ListAPIView 
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.authentication import SessionAuthentication
from django.db.models import F

from .serializers import PenempatanSerializer, SubBidangSerializer, UnitInstalasiSerializer
from .models import Bidang, SubBidang, UnitInstalasi, UnitOrganisasi

class SubBidangAPIView(ListAPIView):
    queryset = SubBidang.objects.all()
    serializer_class = SubBidangSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    
class UnitInstalasiAPIView(ListAPIView):
    queryset = UnitInstalasi.objects.all()
    serializer_class = UnitInstalasiSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class PenempatanAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [OAuth2Authentication, SessionAuthentication]

    def get(self, request, *args, **kwargs):
        penempatan_data = UnitInstalasi.objects.select_related('sub_bidang', 'sub_bidang__bidang', 'sub_bidang__bidang__unor').annotate(
            nama_unor=F('sub_bidang__bidang__unor__unor'),
            nama_bidang=F('sub_bidang__bidang__bidang'),
            nama_sub_bidang=F('sub_bidang__sub_bidang'),
            nama_unit_instalasi=F('instalasi'),
            instalasi_slug=F('slug')
        )
        serializer = PenempatanSerializer(penempatan_data, many=True)
        return Response(serializer.data)