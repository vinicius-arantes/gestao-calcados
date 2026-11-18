from django import forms

from config.forms import BootstrapFormMixin

from .models import ItemOrdemProducao, OrdemProducao


class OrdemProducaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = OrdemProducao
        fields = ['modelo', 'cor', 'prioridade', 'responsavel', 'data_prevista', 'observacoes']
        widgets = {
            'data_prevista': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modelo'].queryset = self.fields['modelo'].queryset.filter(ativo=True)


class ItemOrdemForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ItemOrdemProducao
        fields = ['tamanho', 'quantidade']


GradeFormSet = forms.inlineformset_factory(
    OrdemProducao, ItemOrdemProducao, form=ItemOrdemForm,
    extra=4, can_delete=True, min_num=1, validate_min=True,
)
