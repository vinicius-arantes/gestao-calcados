from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect


class AcessoMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Exige login; quem está logado mas não tem a permissão do perfil recebe 403."""

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            self.raise_exception = True
        return super().handle_no_permission()


class CrudMixin(AcessoMixin):
    """Configuração comum das telas de cadastro e edição."""

    template_name = 'form.html'
    titulo = ''
    mensagem_sucesso = 'Registro salvo com sucesso.'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = self.titulo
        contexto['url_cancelar'] = self.get_success_url()
        return contexto

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, self.mensagem_sucesso)
        return resposta


class ExclusaoMixin(CrudMixin):
    template_name = 'confirmar_exclusao.html'
    mensagem_sucesso = 'Registro excluído com sucesso.'

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'Não é possível excluir: existem registros vinculados a este.')
            return redirect(self.get_success_url())
