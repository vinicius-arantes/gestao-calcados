from django.urls import path

from . import views

app_name = 'catalogo'

urlpatterns = [
    path('modelos/', views.ModeloListView.as_view(), name='modelo_lista'),
    path('modelos/<int:pk>/', views.ModeloDetailView.as_view(), name='modelo_detalhe'),
]
