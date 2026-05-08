from rest_framework.generics import ListAPIView 
from rest_framework.response import Response

from .serializers import SubBidangSerializer, UnitInstalasiSerializer
from .models import SubBidang, UnitInstalasi

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
    
    