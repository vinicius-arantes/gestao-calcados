from django.contrib import admin
from django.db.models import F, Sum
from django.utils.html import format_html

from .models import Categoria, Colecao, Cor, ItemFichaTecnica, Modelo, Tamanho, Variacao


class SituacaoEstoqueVariacaoFilter(admin.SimpleListFilter):
    title = 'situação do estoque'
    parameter_name = 'situacao'

    def lookups(self, request, model_admin):
        return [
            ('zerado', 'Sem estoque'),
            ('abaixo', 'Abaixo do mínimo'),
            ('ok', 'Estoque adequado'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'zerado':
            return queryset.filter(estoque_atual__lte=0)
        if self.value() == 'abaixo':
            return queryset.filter(estoque_atual__lt=F('estoque_minimo'))
        if self.value() == 'ok':
            return queryset.filter(estoque_atual__gte=F('estoque_minimo'), estoque_atual__gt=0)
        return queryset


class FichaTecnicaFilter(admin.SimpleListFilter):
    title = 'ficha técnica'
    parameter_name = 'ficha'

    def lookups(self, request, model_admin):
        return [('com', 'Com ficha técnica'), ('sem', 'Sem ficha técnica')]

    def queryset(self, request, queryset):
        if self.value() == 'com':
            return queryset.filter(ficha_tecnica__isnull=False).distinct()
        if self.value() == 'sem':
            return queryset.filter(ficha_tecnica__isnull=True)
        return queryset


class FaixaPrecoFilter(admin.SimpleListFilter):
    title = 'faixa de preço'
    parameter_name = 'preco'

    # valor: (mínimo, máximo) — None significa sem limite
    FAIXAS = {
        'ate150': (None, 150),
        '150a300': (150, 300),
        'acima300': (300, None),
    }

    def lookups(self, request, model_admin):
        return [('ate150', 'Até R$ 150'), ('150a300', 'R$ 150 a R$ 300'), ('acima300', 'Acima de R$ 300')]

    def queryset(self, request, queryset):
        if self.value() in self.FAIXAS:
            minimo, maximo = self.FAIXAS[self.value()]
            if minimo is not None:
                queryset = queryset.filter(preco_venda__gte=minimo)
            if maximo is not None:
                queryset = queryset.filter(preco_venda__lt=maximo)
        return queryset


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'qtd_modelos']
    search_fields = ['nome']

    @admin.display(description='modelos')
    def qtd_modelos(self, obj):
        return obj.modelos.count()


@admin.register(Colecao)
class ColecaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'estacao', 'ano', 'ativa']
    list_filter = ['estacao', 'ano', 'ativa']
    list_editable = ['ativa']
    search_fields = ['nome']


@admin.register(Cor)
class CorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'amostra', 'codigo_hex']
    search_fields = ['nome']

    @admin.display(description='amostra')
    def amostra(self, obj):
        return format_html(
            '<span style="display:inline-block;width:24px;height:24px;border-radius:50%;'
            'border:1px solid #888;background:{}"></span>', obj.codigo_hex,
        )


@admin.register(Tamanho)
class TamanhoAdmin(admin.ModelAdmin):
    list_display = ['numero']
    search_fields = ['numero']


class ItemFichaTecnicaInline(admin.TabularInline):
    model = ItemFichaTecnica
    extra = 1
    autocomplete_fields = ['material']
    readonly_fields = ['custo_item']

    @admin.display(description='custo (R$)')
    def custo_item(self, obj):
        return f'{obj.custo:.2f}' if obj.pk else '-'


class VariacaoInline(admin.TabularInline):
    model = Variacao
    extra = 0
    fields = ['cor', 'tamanho', 'sku', 'estoque_atual', 'estoque_minimo']
    readonly_fields = ['sku', 'estoque_atual']
    classes = ['collapse']


@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    list_display = [
        'referencia', 'nome', 'categoria', 'colecao', 'genero', 'preco_venda',
        'custo', 'margem_fmt', 'estoque', 'ativo',
    ]
    list_display_links = ['referencia', 'nome']
    list_filter = [
        'ativo', 'genero', 'categoria', 'colecao', FaixaPrecoFilter, FichaTecnicaFilter,
        ('criado_em', admin.DateFieldListFilter),
    ]
    list_editable = ['ativo']
    search_fields = ['referencia', 'nome', 'descricao']
    autocomplete_fields = ['categoria', 'colecao']
    date_hierarchy = 'criado_em'
    inlines = [ItemFichaTecnicaInline, VariacaoInline]
    readonly_fields = ['criado_em', 'atualizado_em']
    fieldsets = [
        ('Identificação', {'fields': ['referencia', 'nome', 'categoria', 'colecao', 'genero', 'ativo']}),
        ('Comercial e produção', {'fields': ['preco_venda', 'tempo_producao_min', 'descricao']}),
        ('Auditoria', {'fields': ['criado_em', 'atualizado_em'], 'classes': ['collapse']}),
    ]
    actions = ['ativar', 'desativar']

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('categoria', 'colecao')
            .annotate(_estoque=Sum('variacoes__estoque_atual'))
        )

    @admin.display(description='custo MP (R$)')
    def custo(self, obj):
        return f'{obj.custo_materiais:.2f}'

    @admin.display(description='margem')
    def margem_fmt(self, obj):
        margem = obj.margem
        if margem is None:
            return '-'
        cor = 'green' if margem >= 50 else 'orange' if margem >= 30 else 'red'
        return format_html('<b style="color:{}">{}%</b>', cor, f'{margem:.1f}')

    @admin.display(description='estoque (pares)', ordering='_estoque')
    def estoque(self, obj):
        return obj._estoque or 0

    @admin.action(description='Ativar modelos selecionados')
    def ativar(self, request, queryset):
        self.message_user(request, f'{queryset.update(ativo=True)} modelo(s) ativado(s).')

    @admin.action(description='Desativar modelos selecionados')
    def desativar(self, request, queryset):
        self.message_user(request, f'{queryset.update(ativo=False)} modelo(s) desativado(s).')


@admin.register(Variacao)
class VariacaoAdmin(admin.ModelAdmin):
    list_display = ['sku', 'modelo', 'cor', 'tamanho', 'estoque_atual', 'estoque_minimo', 'estoque_ok']
    list_filter = [
        SituacaoEstoqueVariacaoFilter, 'modelo__categoria', 'modelo__genero',
        ('cor', admin.RelatedOnlyFieldListFilter), 'tamanho',
    ]
    search_fields = ['sku', 'modelo__referencia', 'modelo__nome']
    autocomplete_fields = ['modelo']
    list_editable = ['estoque_minimo']
    readonly_fields = ['sku', 'estoque_atual']
    list_select_related = ['modelo', 'cor', 'tamanho']

    @admin.display(description='estoque ok?', boolean=True)
    def estoque_ok(self, obj):
        return not obj.abaixo_do_minimo
