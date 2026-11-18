from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from config.mixins import AcessoMixin, CrudMixin, ExclusaoMixin

from . import services
from .forms import ConcluirEtapaForm, GradeFormSet, OrdemProducaoForm
from .models import EtapaOrdem, OrdemProducao


class OrdemListView(AcessoMixin, ListView):
    permission_required = 'producao.view_ordemproducao'
    template_name = 'producao/ordem_lista.html'
    paginate_by = 15

    def get_queryset(self):
        qs = OrdemProducao.objects.select_related('modelo', 'cor', 'responsavel').prefetch_related(
            'itens', 'etapas',
        )
        busca = self.request.GET.get('q', '').strip()
        if busca:
            qs = qs.filter(
                Q(numero__icontains=busca) | Q(modelo__referencia__icontains=busca)
                | Q(modelo__nome__icontains=busca)
            )
        if status := self.request.GET.get('status'):
            qs = qs.filter(status=status)
        if self.request.GET.get('atrasadas') == '1':
            qs = qs.filter(
                status__in=[OrdemProducao.Status.PLANEJADA, OrdemProducao.Status.EM_PRODUCAO],
                data_prevista__lt=timezone.localdate(),
            )
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['status_choices'] = OrdemProducao.Status.choices
        return contexto


class OrdemDetailView(AcessoMixin, DetailView):
    permission_required = 'producao.view_ordemproducao'
    model = OrdemProducao
    template_name = 'producao/ordem_detalhe.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        ordem = self.object
        contexto['itens'] = ordem.itens.select_related('tamanho')
        contexto['etapas'] = ordem.etapas.select_related('setor', 'operador')
        contexto['etapa_atual'] = ordem.etapa_atual
        contexto['form_etapa'] = ConcluirEtapaForm()
        contexto['necessidade'] = [
            {'material': m, 'necessario': q, 'suficiente': m.estoque_atual >= q}
            for m, q in ordem.necessidade_materiais()
        ]
        return contexto


class OrdemFormMixin:
    """Salva a ordem junto com a grade de tamanhos (formset)."""

    model = OrdemProducao
    form_class = OrdemProducaoForm
    template_name = 'producao/ordem_form.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault('grade', GradeFormSet(instance=self.object))
        return contexto

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if 'pk' in kwargs else None
        form = self.get_form()
        grade = GradeFormSet(request.POST, instance=self.object)
        if form.is_valid() and grade.is_valid():
            with transaction.atomic():
                self.object = form.save()
                grade.instance = self.object
                grade.save()
            messages.success(request, self.mensagem_sucesso)
            return redirect(self.object)
        return self.render_to_response(self.get_context_data(form=form, grade=grade))

    def get_success_url(self):
        return self.object.get_absolute_url() if self.object else reverse_lazy('producao:ordem_lista')


class OrdemCreateView(OrdemFormMixin, CrudMixin, CreateView):
    permission_required = 'producao.add_ordemproducao'
    titulo = 'Nova ordem de produção'
    mensagem_sucesso = 'Ordem de produção criada.'

    def get_initial(self):
        return {'responsavel': self.request.user, 'modelo': self.request.GET.get('modelo')}


class OrdemUpdateView(OrdemFormMixin, CrudMixin, UpdateView):
    permission_required = 'producao.change_ordemproducao'
    titulo = 'Editar ordem de produção'
    mensagem_sucesso = 'Ordem de produção atualizada.'

    def get_queryset(self):
        # Depois de iniciada, a ordem já baixou materiais: modelo e grade não mudam mais
        return OrdemProducao.objects.filter(status=OrdemProducao.Status.PLANEJADA)


class OrdemDeleteView(ExclusaoMixin, DeleteView):
    permission_required = 'producao.delete_ordemproducao'
    success_url = reverse_lazy('producao:ordem_lista')

    def get_queryset(self):
        return OrdemProducao.objects.filter(
            status__in=[OrdemProducao.Status.PLANEJADA, OrdemProducao.Status.CANCELADA],
        )


def _executar(request, funcao, ordem, sucesso):
    try:
        funcao(ordem, request.user)
        messages.success(request, sucesso)
    except ValidationError as erro:
        messages.error(request, ' '.join(erro.messages))
    return redirect(ordem)


@require_POST
@login_required
@permission_required('producao.iniciar_ordemproducao', raise_exception=True)
def iniciar_ordem(request, pk):
    ordem = get_object_or_404(OrdemProducao, pk=pk)
    return _executar(request, services.iniciar_ordem, ordem,
                     'Produção iniciada. Os materiais foram baixados do estoque.')


@require_POST
@login_required
@permission_required('producao.concluir_ordemproducao', raise_exception=True)
def concluir_ordem(request, pk):
    ordem = get_object_or_404(OrdemProducao, pk=pk)
    return _executar(request, services.concluir_ordem, ordem,
                     'Ordem concluída. Os pares entraram no estoque de produto acabado.')


@require_POST
@login_required
@permission_required('producao.change_ordemproducao', raise_exception=True)
def cancelar_ordem(request, pk):
    ordem = get_object_or_404(OrdemProducao, pk=pk, status=OrdemProducao.Status.PLANEJADA)
    ordem.status = OrdemProducao.Status.CANCELADA
    ordem.save(update_fields=['status'])
    messages.info(request, 'Ordem cancelada.')
    return redirect(ordem)


@require_POST
@login_required
@permission_required('producao.change_etapaordem', raise_exception=True)
def avancar_etapa(request, pk):
    etapa = get_object_or_404(EtapaOrdem.objects.select_related('ordem', 'setor'), pk=pk)
    refugo, observacao = 0, ''
    if etapa.status == EtapaOrdem.Status.EM_ANDAMENTO:
        form = ConcluirEtapaForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Informe um número válido de pares com defeito.')
            return redirect(etapa.ordem)
        refugo = form.cleaned_data['pares_refugo']
        observacao = form.cleaned_data['observacao']
    try:
        services.avancar_etapa(etapa, request.user, refugo, observacao)
        messages.success(request, f'Etapa {etapa.setor}: {etapa.get_status_display().lower()}.')
    except ValidationError as erro:
        messages.error(request, ' '.join(erro.messages))

    # Volta para a página de origem (detalhe da ordem ou painel dos setores)
    destino = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect(etapa.ordem)
