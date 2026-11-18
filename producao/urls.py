from django.urls import path

from . import views

app_name = 'producao'

urlpatterns = [
    path('ordens/', views.OrdemListView.as_view(), name='ordem_lista'),
    path('ordens/nova/', views.OrdemCreateView.as_view(), name='ordem_nova'),
    path('ordens/<int:pk>/', views.OrdemDetailView.as_view(), name='ordem_detalhe'),
    path('ordens/<int:pk>/editar/', views.OrdemUpdateView.as_view(), name='ordem_editar'),
    path('ordens/<int:pk>/excluir/', views.OrdemDeleteView.as_view(), name='ordem_excluir'),
    path('ordens/<int:pk>/iniciar/', views.iniciar_ordem, name='ordem_iniciar'),
    path('ordens/<int:pk>/concluir/', views.concluir_ordem, name='ordem_concluir'),
    path('ordens/<int:pk>/cancelar/', views.cancelar_ordem, name='ordem_cancelar'),
    path('etapas/<int:pk>/avancar/', views.avancar_etapa, name='etapa_avancar'),
]
