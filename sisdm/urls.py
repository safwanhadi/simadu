"""
URL configuration for sisdm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include(('myaccount.urls', 'myaccount_urls'), namespace='myaccount_urls')),
    path('riwayat/', include(('dokumen.urls', 'riwayat_urls'), namespace='riwayat_urls')),
    path('layanan/', include(('layanan.urls', 'layanan_urls'), namespace='layanan_urls')),
    path('struktur/', include(('strukturorg.urls', 'struktur_urls'), namespace='struktur_urls')),
    path('sdm/', include(('jenissdm.urls', 'sdm_urls'), namespace='sdm_urls')),
    path('file/', include(('file_dokumen.urls', 'file_urls'), namespace='file_urls')),
    path('', include(('dashboard.urls', 'dashboard_urls'), namespace='dashboard_urls')),
    path('informasi/', include(('informasi.urls', 'informasi_urls'), namespace='informasi_urls')),
    path('disiplin/', include(('disiplinsdm.urls', 'disiplinsdm_urls'), namespace='disiplinsdm_urls')),
    path('laporan/', include(('lapor.urls', 'laporan_urls'), namespace='laporan_urls'))
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
