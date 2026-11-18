from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from config.mixins import AcessoMixin, CrudMixin, ExclusaoMixin

from .forms import CategoriaForm, FichaTecnicaFormSet, ModeloForm
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


class ModeloFormMixin:
    """Salva o modelo junto com a ficha técnica (formset)."""

    model = Modelo
    form_class = ModeloForm
    template_name = 'catalogo/modelo_form.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault('ficha', FichaTecnicaFormSet(instance=self.object))
        return contexto

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if 'pk' in kwargs else None
        form = self.get_form()
        ficha = FichaTecnicaFormSet(request.POST, instance=self.object)
        if form.is_valid() and ficha.is_valid():
            with transaction.atomic():
                self.object = form.save()
                ficha.instance = self.object
                ficha.save()
            messages.success(request, self.mensagem_sucesso)
            return redirect(self.object)
        return self.render_to_response(self.get_context_data(form=form, ficha=ficha))

    def get_success_url(self):
        return self.object.get_absolute_url() if self.object else reverse_lazy('catalogo:modelo_lista')


class ModeloCreateView(ModeloFormMixin, CrudMixin, CreateView):
    permission_required = 'catalogo.add_modelo'
    titulo = 'Novo modelo'
    mensagem_sucesso = 'Modelo cadastrado.'


class ModeloUpdateView(ModeloFormMixin, CrudMixin, UpdateView):
    permission_required = 'catalogo.change_modelo'
    titulo = 'Editar modelo'
    mensagem_sucesso = 'Modelo atualizado.'


class ModeloDeleteView(ExclusaoMixin, DeleteView):
    permission_required = 'catalogo.delete_modelo'
    model = Modelo
    success_url = reverse_lazy('catalogo:modelo_lista')
    mensagem_sucesso = 'Modelo excluído.'


class CategoriaListView(AcessoMixin, ListView):
    permission_required = 'catalogo.view_categoria'
    template_name = 'catalogo/categoria_lista.html'
    queryset = Categoria.objects.annotate(qtd_modelos=Count('modelos')).order_by('nome')


class CategoriaCreateView(CrudMixin, CreateView):
    permission_required = 'catalogo.add_categoria'
    model = Categoria
    form_class = CategoriaForm
    titulo = 'Nova categoria'
    success_url = reverse_lazy('catalogo:categoria_lista')


class CategoriaUpdateView(CrudMixin, UpdateView):
    permission_required = 'catalogo.change_categoria'
    model = Categoria
    form_class = CategoriaForm
    titulo = 'Editar categoria'
    success_url = reverse_lazy('catalogo:categoria_lista')


class CategoriaDeleteView(ExclusaoMixin, DeleteView):
    permission_required = 'catalogo.delete_categoria'
    model = Categoria
    success_url = reverse_lazy('catalogo:categoria_lista')
