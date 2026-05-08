from django.urls import path
from .views_api import UnitInstalasiAPIView, SubBidangAPIView


urlpatterns=[
    path('api/subbidang/', SubBidangAPIView.as_view(), name='subbidang-list'),
    path('api/unitinstalasi/', UnitInstalasiAPIView.as_view(), name='unitinstalasi-list'),
]