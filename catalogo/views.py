from django.db.models import Q, Sum
from django.views.generic import DetailView, ListView

from config.mixins import AcessoMixin

from .models import Categoria, Modelo


class ModeloListView(AcessoMixin, ListView):
    permission_required = 'catalogo.view_modelo'
    template_name = 'catalogo/modelo_lista.html'
    paginate_by = 12

    def get_queryset(self):
        qs = (
            Modelo.objects.select_related('categoria', 'colecao')
            .annotate(estoque=Sum('variacoes__estoque_atual'))
            .order_by('referencia')
        )
        busca = self.request.GET.get('q', '').strip()
        if busca:
            qs = qs.filter(Q(referencia__icontains=busca) | Q(nome__icontains=busca))
        if categoria := self.request.GET.get('categoria'):
            qs = qs.filter(categoria_id=categoria)
        if genero := self.request.GET.get('genero'):
            qs = qs.filter(genero=genero)
        if self.request.GET.get('inativos') != '1':
            qs = qs.filter(ativo=True)
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['categorias'] = Categoria.objects.all()
        contexto['generos'] = Modelo.Genero.choices
        return contexto


class ModeloDetailView(AcessoMixin, DetailView):
    permission_required = 'catalogo.view_modelo'
    model = Modelo
    template_name = 'catalogo/modelo_detalhe.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['ficha'] = self.object.ficha_tecnica.select_related('material')
        contexto['variacoes'] = self.object.variacoes.select_related('cor', 'tamanho')
        contexto['ordens'] = self.object.ordens.select_related('cor')[:10]
        return contexto
