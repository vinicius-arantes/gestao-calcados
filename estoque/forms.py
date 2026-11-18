from django import forms

from config.forms import BootstrapFormMixin

from .models import Fornecedor, Material


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
