from django.urls import path

from . import views

app_name = 'estoque'

urlpatterns = [
    path('materiais/', views.MaterialListView.as_view(), name='material_lista'),
    path('materiais/novo/', views.MaterialCreateView.as_view(), name='material_novo'),
    path('materiais/<int:pk>/editar/', views.MaterialUpdateView.as_view(), name='material_editar'),
    path('materiais/<int:pk>/excluir/', views.MaterialDeleteView.as_view(), name='material_excluir'),
    path('fornecedores/', views.FornecedorListView.as_view(), name='fornecedor_lista'),
    path('fornecedores/novo/', views.FornecedorCreateView.as_view(), name='fornecedor_novo'),
    path('fornecedores/<int:pk>/editar/', views.FornecedorUpdateView.as_view(), name='fornecedor_editar'),
    path('fornecedores/<int:pk>/excluir/', views.FornecedorDeleteView.as_view(), name='fornecedor_excluir'),
]
