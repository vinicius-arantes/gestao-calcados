from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import CadastroForm, LoginForm, PerfilForm, UsuarioForm
from .models import GRUPO_OPERADOR


class EntrarView(LoginView):
    template_name = 'contas/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


def cadastro(request):
    """Cadastro público: a conta nova recebe o perfil de menor privilégio (Operador)."""
    if request.user.is_authenticated:
        return redirect('inicio')
    form = CadastroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            usuario = form.save()
            usuario.perfil.matricula = form.cleaned_data['matricula']
            usuario.perfil.save()
            grupo, _ = Group.objects.get_or_create(name=GRUPO_OPERADOR)
            usuario.groups.add(grupo)
        login(request, usuario)
        messages.success(request, f'Bem-vindo(a), {usuario.first_name}! Sua conta foi criada.')
        return redirect('inicio')
    return render(request, 'contas/cadastro.html', {'form': form})


@login_required
def meu_perfil(request):
    form_usuario = UsuarioForm(request.POST or None, instance=request.user)
    form_perfil = PerfilForm(request.POST or None, instance=request.user.perfil)
    if request.method == 'POST' and form_usuario.is_valid() and form_perfil.is_valid():
        form_usuario.save()
        form_perfil.save()
        messages.success(request, 'Perfil atualizado.')
        return redirect('contas:perfil')
    return render(request, 'contas/perfil.html', {
        'form_usuario': form_usuario, 'form_perfil': form_perfil,
    })
