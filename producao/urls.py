from django.urls import path

from . import views

app_name = 'producao'

urlpatterns = [
    path('ordens/', views.OrdemListView.as_view(), name='ordem_lista'),
    path('ordens/<int:pk>/', views.OrdemDetailView.as_view(), name='ordem_detalhe'),
]
