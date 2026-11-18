from django import forms

from config.forms import BootstrapFormMixin

from .models import Fornecedor, Material, MovimentacaoMaterial, MovimentacaoProduto


class FornecedorForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = ['nome', 'cnpj', 'email', 'telefone', 'cidade', 'uf', 'ativo']


class MaterialForm(BootstrapFormMixin, forms.ModelForm):
    # O saldo não aparece aqui: ele só muda por movimentações
    class Meta:
        model = Material
        fields = [
            'codigo', 'nome', 'tipo', 'unidade', 'fornecedor',
            'custo_unitario', 'estoque_minimo', 'ativo',
        ]


class MovimentacaoMaterialForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MovimentacaoMaterial
        fields = ['material', 'tipo', 'motivo', 'quantidade', 'custo_unitario', 'observacao']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # O consumo da produção é lançado automaticamente ao iniciar uma ordem
        self.fields['motivo'].choices = [
            c for c in self.fields['motivo'].choices if c[0] != MovimentacaoMaterial.Motivo.CONSUMO
        ]
        self.fields['material'].queryset = Material.objects.filter(ativo=True).order_by('nome')


class MovimentacaoProdutoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MovimentacaoProduto
        fields = ['variacao', 'tipo', 'motivo', 'quantidade', 'observacao']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A entrada da produção é lançada automaticamente ao concluir uma ordem
        self.fields['motivo'].choices = [
            c for c in self.fields['motivo'].choices if c[0] != MovimentacaoProduto.Motivo.PRODUCAO
        ]
        self.fields['variacao'].queryset = self.fields['variacao'].queryset.select_related(
            'modelo', 'cor', 'tamanho',
        )
