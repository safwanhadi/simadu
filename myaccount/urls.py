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
    sso_go
)
from .views_api import api_me, PegawaiAPIView


urlpatterns=[
    path('login/', SimaduLoginView.as_view(), name='login_view'),
    path('logout/', logout_view, name='logout_view'),
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
    path('sso/', sso_portal, name='sso_portal'),
    path('sso/<str:client_key>/', sso_go, name='sso_go'),
]