from django.db.models import Q
from django.utils import timezone
from django.views.generic import DetailView, ListView

from config.mixins import AcessoMixin

from .models import OrdemProducao


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
        contexto['necessidade'] = [
            {'material': m, 'necessario': q, 'suficiente': m.estoque_atual >= q}
            for m, q in ordem.necessidade_materiais()
        ]
        return contexto
