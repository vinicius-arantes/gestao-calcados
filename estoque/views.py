from django.db.models import F, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from catalogo.models import Variacao
from config.mixins import AcessoMixin, CrudMixin, ExclusaoMixin

from .forms import FornecedorForm, MaterialForm, MovimentacaoMaterialForm, MovimentacaoProdutoForm
from .models import Fornecedor, Material, MovimentacaoMaterial, MovimentacaoProduto


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


class ProdutoListView(AcessoMixin, ListView):
    """Estoque de produto acabado, por SKU."""

    permission_required = 'catalogo.view_variacao'
    template_name = 'estoque/produto_lista.html'
    paginate_by = 25

    def get_queryset(self):
        qs = Variacao.objects.select_related('modelo', 'cor', 'tamanho')
        busca = self.request.GET.get('q', '').strip()
        if busca:
            qs = qs.filter(
                Q(sku__icontains=busca) | Q(modelo__nome__icontains=busca)
                | Q(modelo__referencia__icontains=busca)
            )
        if self.request.GET.get('repor') == '1':
            qs = qs.filter(estoque_atual__lt=F('estoque_minimo'))
        return qs


class MovimentacaoListView(AcessoMixin, ListView):
    """Histórico de movimentações de materiais ou, com ?de=produto, de produto acabado."""

    template_name = 'estoque/movimentacao_lista.html'
    paginate_by = 25

    def de_produto(self):
        return self.request.GET.get('de') == 'produto'

    def get_permission_required(self):
        if self.de_produto():
            return ['estoque.view_movimentacaoproduto']
        return ['estoque.view_movimentacaomaterial']

    def get_queryset(self):
        if self.de_produto():
            qs = MovimentacaoProduto.objects.select_related(
                'variacao__modelo', 'variacao__cor', 'variacao__tamanho', 'usuario', 'ordem_producao',
            )
        else:
            qs = MovimentacaoMaterial.objects.select_related('material', 'usuario', 'ordem_producao')
        if tipo := self.request.GET.get('tipo'):
            qs = qs.filter(tipo=tipo)
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['de_produto'] = self.de_produto()
        return contexto


class MovimentacaoCreateMixin(CrudMixin):
    mensagem_sucesso = 'Movimentação registrada e saldo atualizado.'

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class MovimentacaoMaterialCreateView(MovimentacaoCreateMixin, CreateView):
    permission_required = 'estoque.add_movimentacaomaterial'
    model = MovimentacaoMaterial
    form_class = MovimentacaoMaterialForm
    titulo = 'Movimentar material'
    success_url = reverse_lazy('estoque:movimentacao_lista')

    def get_initial(self):
        return {'material': self.request.GET.get('material')}


class MovimentacaoProdutoCreateView(MovimentacaoCreateMixin, CreateView):
    permission_required = 'estoque.add_movimentacaoproduto'
    model = MovimentacaoProduto
    form_class = MovimentacaoProdutoForm
    titulo = 'Movimentar produto acabado'
    success_url = reverse_lazy('estoque:produto_lista')

    def get_initial(self):
        return {'variacao': self.request.GET.get('variacao')}
