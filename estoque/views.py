from django.db.models import F, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from config.mixins import AcessoMixin, CrudMixin, ExclusaoMixin

from .forms import FornecedorForm, MaterialForm
from .models import Fornecedor, Material


class MaterialListView(AcessoMixin, ListView):
    permission_required = 'estoque.view_material'
    template_name = 'estoque/material_lista.html'
    paginate_by = 20

    def get_queryset(self):
        qs = Material.objects.select_related('fornecedor').order_by('nome')
        busca = self.request.GET.get('q', '').strip()
        if busca:
            qs = qs.filter(Q(codigo__icontains=busca) | Q(nome__icontains=busca))
        if tipo := self.request.GET.get('tipo'):
            qs = qs.filter(tipo=tipo)
        if self.request.GET.get('repor') == '1':
            qs = qs.filter(estoque_atual__lt=F('estoque_minimo'))
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['tipos'] = Material.Tipo.choices
        return contexto


class MaterialCreateView(CrudMixin, CreateView):
    permission_required = 'estoque.add_material'
    model = Material
    form_class = MaterialForm
    titulo = 'Novo material'
    success_url = reverse_lazy('estoque:material_lista')


class MaterialUpdateView(CrudMixin, UpdateView):
    permission_required = 'estoque.change_material'
    model = Material
    form_class = MaterialForm
    titulo = 'Editar material'
    success_url = reverse_lazy('estoque:material_lista')


class MaterialDeleteView(ExclusaoMixin, DeleteView):
    permission_required = 'estoque.delete_material'
    model = Material
    success_url = reverse_lazy('estoque:material_lista')


class FornecedorListView(AcessoMixin, ListView):
    permission_required = 'estoque.view_fornecedor'
    template_name = 'estoque/fornecedor_lista.html'
    paginate_by = 20

    def get_queryset(self):
        qs = Fornecedor.objects.order_by('nome')
        busca = self.request.GET.get('q', '').strip()
        if busca:
            qs = qs.filter(Q(nome__icontains=busca) | Q(cnpj__icontains=busca) | Q(cidade__icontains=busca))
        return qs


class FornecedorCreateView(CrudMixin, CreateView):
    permission_required = 'estoque.add_fornecedor'
    model = Fornecedor
    form_class = FornecedorForm
    titulo = 'Novo fornecedor'
    success_url = reverse_lazy('estoque:fornecedor_lista')


class FornecedorUpdateView(CrudMixin, UpdateView):
    permission_required = 'estoque.change_fornecedor'
    model = Fornecedor
    form_class = FornecedorForm
    titulo = 'Editar fornecedor'
    success_url = reverse_lazy('estoque:fornecedor_lista')


class FornecedorDeleteView(ExclusaoMixin, DeleteView):
    permission_required = 'estoque.delete_fornecedor'
    model = Fornecedor
    success_url = reverse_lazy('estoque:fornecedor_lista')
