from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from config.mixins import AcessoMixin, CrudMixin, ExclusaoMixin

from .forms import GradeFormSet, OrdemProducaoForm
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
