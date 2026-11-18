from django import forms

from config.forms import BootstrapFormMixin

from .models import Categoria, ItemFichaTecnica, Modelo


class ModeloForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Modelo
        fields = [
            'referencia', 'nome', 'categoria', 'colecao', 'genero',
            'preco_venda', 'tempo_producao_min', 'descricao', 'ativo',
        ]
        widgets = {'descricao': forms.Textarea(attrs={'rows': 3})}


class ItemFichaTecnicaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ItemFichaTecnica
        fields = ['material', 'quantidade_por_par']


FichaTecnicaFormSet = forms.inlineformset_factory(
    Modelo, ItemFichaTecnica, form=ItemFichaTecnicaForm, extra=3, can_delete=True,
)
