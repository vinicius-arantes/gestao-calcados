from django.contrib import admin
from django.db.models import F

from .models import Fornecedor, Material, MovimentacaoMaterial, MovimentacaoProduto


class SituacaoEstoqueMaterialFilter(admin.SimpleListFilter):
    title = 'situação do estoque'
    parameter_name = 'situacao'

    def lookups(self, request, model_admin):
        return [('abaixo', 'Abaixo do mínimo (repor)'), ('ok', 'Estoque adequado')]

    def queryset(self, request, queryset):
        if self.value() == 'abaixo':
            return queryset.filter(estoque_atual__lt=F('estoque_minimo'))
        if self.value() == 'ok':
            return queryset.filter(estoque_atual__gte=F('estoque_minimo'))
        return queryset


class OrigemMovimentacaoFilter(admin.SimpleListFilter):
    title = 'origem'
    parameter_name = 'origem'

    def lookups(self, request, model_admin):
        return [('op', 'Gerada por ordem de produção'), ('manual', 'Lançamento manual')]

    def queryset(self, request, queryset):
        if self.value() == 'op':
            return queryset.filter(ordem_producao__isnull=False)
        if self.value() == 'manual':
            return queryset.filter(ordem_producao__isnull=True)
        return queryset


class MaterialInline(admin.TabularInline):
    model = Material
    extra = 0
    fields = ['codigo', 'nome', 'tipo', 'custo_unitario']
    show_change_link = True


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cnpj', 'cidade', 'uf', 'telefone', 'email', 'ativo']
    list_filter = ['ativo', 'uf', 'cidade']
    list_editable = ['ativo']
    search_fields = ['nome', 'cnpj', 'cidade']
    inlines = [MaterialInline]


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nome', 'tipo', 'unidade', 'fornecedor', 'custo_unitario',
        'estoque_atual', 'estoque_minimo', 'estoque_ok',
    ]
    list_display_links = ['codigo', 'nome']
    list_filter = [
        SituacaoEstoqueMaterialFilter, 'tipo', 'unidade', 'ativo',
        ('fornecedor', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = ['codigo', 'nome', 'fornecedor__nome']
    autocomplete_fields = ['fornecedor']
    # O saldo só muda por movimentações
    readonly_fields = ['estoque_atual']
    list_select_related = ['fornecedor']

    @admin.display(description='estoque ok?', boolean=True)
    def estoque_ok(self, obj):
        return not obj.abaixo_do_minimo


class MovimentacaoAdminBase(admin.ModelAdmin):
    list_filter = [
        'tipo', 'motivo', OrigemMovimentacaoFilter,
        ('data', admin.DateFieldListFilter),
        ('usuario', admin.RelatedOnlyFieldListFilter),
    ]
    date_hierarchy = 'data'
    readonly_fields = ['data', 'usuario', 'ordem_producao']

    def save_model(self, request, obj, form, change):
        if not obj.usuario_id:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)


@admin.register(MovimentacaoMaterial)
class MovimentacaoMaterialAdmin(MovimentacaoAdminBase):
    list_display = ['data', 'tipo', 'motivo', 'material', 'quantidade', 'ordem_producao', 'usuario']
    list_filter = MovimentacaoAdminBase.list_filter + ['material__tipo']
    search_fields = ['material__nome', 'material__codigo', 'observacao', 'ordem_producao__numero']
    autocomplete_fields = ['material']
    list_select_related = ['material', 'ordem_producao', 'usuario']


@admin.register(MovimentacaoProduto)
class MovimentacaoProdutoAdmin(MovimentacaoAdminBase):
    list_display = ['data', 'tipo', 'motivo', 'variacao', 'quantidade', 'ordem_producao', 'usuario']
    list_filter = MovimentacaoAdminBase.list_filter + ['variacao__modelo__categoria']
    search_fields = ['variacao__sku', 'variacao__modelo__nome', 'observacao', 'ordem_producao__numero']
    autocomplete_fields = ['variacao']
    list_select_related = [
        'variacao__modelo', 'variacao__cor', 'variacao__tamanho', 'ordem_producao', 'usuario',
    ]
