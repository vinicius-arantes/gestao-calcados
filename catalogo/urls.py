from django.urls import path

from . import views

app_name = 'catalogo'

urlpatterns = [
    path('modelos/', views.ModeloListView.as_view(), name='modelo_lista'),
    path('modelos/novo/', views.ModeloCreateView.as_view(), name='modelo_novo'),
    path('modelos/<int:pk>/', views.ModeloDetailView.as_view(), name='modelo_detalhe'),
    path('modelos/<int:pk>/editar/', views.ModeloUpdateView.as_view(), name='modelo_editar'),
    path('modelos/<int:pk>/excluir/', views.ModeloDeleteView.as_view(), name='modelo_excluir'),
    path('categorias/', views.CategoriaListView.as_view(), name='categoria_lista'),
    path('categorias/nova/', views.CategoriaCreateView.as_view(), name='categoria_nova'),
    path('categorias/<int:pk>/editar/', views.CategoriaUpdateView.as_view(), name='categoria_editar'),
    path('categorias/<int:pk>/excluir/', views.CategoriaDeleteView.as_view(), name='categoria_excluir'),
]
