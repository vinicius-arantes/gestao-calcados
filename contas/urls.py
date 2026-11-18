from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'contas'

urlpatterns = [
    path('entrar/', views.EntrarView.as_view(), name='login'),
    path('sair/', auth_views.LogoutView.as_view(), name='logout'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('perfil/', views.meu_perfil, name='perfil'),
]
