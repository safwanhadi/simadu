from django.urls import path
from .views import LaporanView, UpdateLaporanView, SaranView, UpdateSaranView


urlpatterns = [
    path('', LaporanView.as_view(), name='laporan_view'),
    path('<int:id>/', UpdateLaporanView.as_view(), name='laporan_update_view'),
    path('saran/', SaranView.as_view(), name='saran_view'),
    path('saran/<int:id>/', UpdateSaranView.as_view(), name='saran_update_view'),
]