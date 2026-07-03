from django.urls import path
from .views_api import PenempatanAPIView, UnitInstalasiAPIView, SubBidangAPIView


urlpatterns=[
    path('api/subbidang/', SubBidangAPIView.as_view(), name='subbidang-list'),
    path('api/unitinstalasi/', UnitInstalasiAPIView.as_view(), name='unitinstalasi-list'),
    path('api/penempatan/', PenempatanAPIView.as_view(), name='penempatan-list'),
]