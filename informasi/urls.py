from django.urls import path
from .views import InformasiSDMView, VideoTutorialView, pdf_view, pdf_list, pdf_viewer, InformasiListView, InformasiDetailView, DeleteInformasiView


urlpatterns = [
    path('', InformasiListView.as_view(), name='informasi_view'),
    path('add/', InformasiSDMView.as_view(), name='add_informasi_view'),
    path('<str:slug>/', InformasiDetailView.as_view(), name='informasi_view'),
    path('<int:pk>/delete/', DeleteInformasiView.as_view(), name='delete_informasi_view'),
    path('add/<int:id>/', InformasiSDMView.as_view(), name='informasi_update_view'),
    path('pdfs/', pdf_list, name='pdf_list'),
    path('pdf/<int:id>/', pdf_view, name='pdf_view'),#get pdf from file saved and view pdf to template
    path('pdf-viewer/', pdf_viewer, name='pdf_viewer'),#generate instance pdf and view pdf to template
    path('video/', VideoTutorialView.as_view(), name='tutorial_view'),
    path('video/<int:id>/', VideoTutorialView.as_view(), name='tutorial_view'), 
]