from django.urls import path

from .views import (
    logout_view, 
    SimaduLoginView, 
    ChangePassword, 
    ChangePasswordDone, 
    ProfilListView, 
    ProfilDetailView, 
    ProfilUpdateView, 
    ProfilCreateView,
    UlangTahunSebulanTerakhirListView,
    PegawaiAutocompleteView,
    sso_portal,
    sso_go,
    access_denied_view,
    cek_jaringan_lokal,
    app_gateway,
    back_view
)
from .views_api import api_me, PegawaiAPIView, DokterSpesialisAPIView, DetailMeAPIView


urlpatterns=[
    path('login/', SimaduLoginView.as_view(), name='login_view'),
    path('logout/', logout_view, name='logout_view'),
    path('to-sso/', back_view, name='back_view'),
    path('ganti-password/', ChangePassword.as_view(), name='ganti_password_view'),
    path('ganti-password/done/', ChangePasswordDone.as_view(), name='ganti_password_done_view'),
    path('profil/', ProfilListView.as_view(), name='profil_view'),
    path('profil/add/', ProfilCreateView.as_view(), name='profil_create_view'),
    path('profil/detail/<int:pk>/', ProfilDetailView.as_view(), name='profil_detail_view'),
    path('profil/<int:pk>/update/', ProfilUpdateView.as_view(), name='profil_update_view'),
    path('pegawai-ultah/', UlangTahunSebulanTerakhirListView.as_view(), name='pegawai_ultah_sebulan'),
    path('ajax-pegawai-autocomplete/', PegawaiAutocompleteView.as_view(), name='ajax_pegawai_autocomplete'),
    
    path('api/me/', api_me, name='api_me'),
    path('api/pegawai/', PegawaiAPIView.as_view(), name='pegawai_api_view'),
    path('api/dokter-spesialis/', DokterSpesialisAPIView.as_view(), name='dokter_spesialis_api_view'),
    path('api/pegawai/me/', DetailMeAPIView.as_view(), name='detail_me_api_view'),
    path('sso/', sso_portal, name='sso_portal'),
    path('sso/<str:client_key>/', sso_go, name='sso_go'),
    path('access-denied/', access_denied_view, name='local_only_blocked'),
    path('cek-jaringan-lokal/', cek_jaringan_lokal, name='cek_jaringan_lokal'),
    path('app-gateway/', app_gateway, name='app_gateway'),
]