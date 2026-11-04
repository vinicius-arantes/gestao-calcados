from datetime import timedelta

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.html import format_html

from . import services
from .models import EtapaOrdem, ItemOrdemProducao, OrdemProducao, Setor


class PrazoFilter(admin.SimpleListFilter):
    title = 'prazo'
    parameter_name = 'prazo'

    def lookups(self, request, model_admin):
        return [
            ('atrasada', 'Atrasadas'),
            ('semana', 'Vencem em até 7 dias'),
            ('no_prazo', 'No prazo'),
        ]

    def queryset(self, request, queryset):
        hoje = timezone.localdate()
        abertas = queryset.filter(
            status__in=[OrdemProducao.Status.PLANEJADA, OrdemProducao.Status.EM_PRODUCAO],
        )
        if self.value() == 'atrasada':
            return abertas.filter(data_prevista__lt=hoje)
        if self.value() == 'semana':
            return abertas.filter(data_prevista__range=(hoje, hoje + timedelta(days=7)))
        if self.value() == 'no_prazo':
            return abertas.filter(data_prevista__gte=hoje)
        return queryset


class SetorAtualFilter(admin.SimpleListFilter):
    """Ordens em produção cuja etapa em andamento está no setor escolhido."""

    title = 'setor atual'
    parameter_name = 'setor_atual'

    def lookups(self, request, model_admin):
        return [(s.pk, s.nome) for s in Setor.objects.filter(ativo=True)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                status=OrdemProducao.Status.EM_PRODUCAO,
                etapas__setor_id=self.value(),
                etapas__status=EtapaOrdem.Status.EM_ANDAMENTO,
            )
        return queryset


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ['sequencia', 'nome', 'ativo']
    list_display_links = ['nome']
    list_editable = ['ativo']
    search_fields = ['nome']


class ItemOrdemInline(admin.TabularInline):
    model = ItemOrdemProducao
    extra = 3


class EtapaOrdemInline(admin.TabularInline):
    model = EtapaOrdem
    extra = 0
    fields = ['setor', 'status', 'operador', 'inicio', 'fim', 'pares_refugo', 'observacao']
    readonly_fields = ['setor']
    can_delete = False


@admin.register(OrdemProducao)
class OrdemProducaoAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'modelo', 'cor', 'status_badge', 'prioridade', 'pares',
        'data_emissao', 'data_prevista', 'no_prazo', 'barra_progresso', 'responsavel',
    ]
    list_filter = [
        'status', PrazoFilter, 'prioridade', SetorAtualFilter, 'modelo__categoria',
        ('responsavel', admin.RelatedOnlyFieldListFilter),
        ('data_emissao', admin.DateFieldListFilter),
    ]
    search_fields = ['numero', 'modelo__referencia', 'modelo__nome', 'observacoes']
    autocomplete_fields = ['modelo', 'cor', 'responsavel']
    date_hierarchy = 'data_prevista'
    readonly_fields = ['numero', 'data_inicio', 'data_conclusao']
    list_select_related = ['modelo', 'cor', 'responsavel']
    actions = ['iniciar', 'concluir', 'cancelar']
    fieldsets = [
        ('Ordem', {'fields': ['numero', 'modelo', 'cor', 'prioridade', 'responsavel', 'status']}),
        ('Datas', {'fields': ['data_emissao', 'data_prevista', 'data_inicio', 'data_conclusao']}),
        ('Observações', {'fields': ['observacoes']}),
    ]

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            # Na criação, número e datas de execução ainda não existem
            return [
                ('Ordem', {'fields': ['modelo', 'cor', 'prioridade', 'responsavel']}),
                ('Datas', {'fields': ['data_emissao', 'data_prevista']}),
                ('Observações', {'fields': ['observacoes']}),
            ]
        return self.fieldsets

    def get_readonly_fields(self, request, obj=None):
        # Depois de criada, o status só muda pelas ações (que movimentam o estoque)
        campos = list(self.readonly_fields)
        if obj:
            campos.append('status')
        return campos

    def get_inlines(self, request, obj):
        # As etapas são criadas automaticamente ao salvar a ordem
        return [ItemOrdemInline, EtapaOrdemInline] if obj else [ItemOrdemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('itens', 'etapas')

    @admin.display(description='status', ordering='status')
    def status_badge(self, obj):
        return format_html(
            '<span class="badge bg-{}">{}</span>', obj.cor_status, obj.get_status_display(),
        )

    @admin.display(description='pares')
    def pares(self, obj):
        return sum(item.quantidade for item in obj.itens.all())

    @admin.display(description='no prazo?', boolean=True)
    def no_prazo(self, obj):
        return not obj.atrasada

    @admin.display(description='progresso')
    def barra_progresso(self, obj):
        return format_html(
            '<div class="progress" style="min-width:90px;height:16px">'
            '<div class="progress-bar bg-success" style="width:{}%">{}%</div></div>',
            obj.progresso, obj.progresso,
        )

    def _executar(self, request, queryset, funcao, sucesso):
        """Aplica um serviço a cada ordem selecionada, reportando os erros individualmente."""
        feitas = 0
        for ordem in queryset:
            try:
                funcao(ordem, request.user)
                feitas += 1
            except ValidationError as erro:
                self.message_user(request, f'{ordem.numero}: {" ".join(erro.messages)}', messages.ERROR)
        if feitas:
            self.message_user(request, f'{feitas} ordem(ns) {sucesso}.', messages.SUCCESS)

    @admin.action(description='Iniciar produção (baixa os materiais)', permissions=['iniciar'])
    def iniciar(self, request, queryset):
        self._executar(request, queryset, services.iniciar_ordem, 'iniciada(s)')

    @admin.action(description='Concluir produção (entrada no estoque)', permissions=['concluir'])
    def concluir(self, request, queryset):
        self._executar(request, queryset, services.concluir_ordem, 'concluída(s)')

    @admin.action(description='Cancelar ordens planejadas', permissions=['change'])
    def cancelar(self, request, queryset):
        total = queryset.filter(status=OrdemProducao.Status.PLANEJADA).update(
            status=OrdemProducao.Status.CANCELADA,
        )
        self.message_user(request, f'{total} ordem(ns) cancelada(s).')

    def has_iniciar_permission(self, request):
        return request.user.has_perm('producao.iniciar_ordemproducao')

    def has_concluir_permission(self, request):
        return request.user.has_perm('producao.concluir_ordemproducao')


@admin.register(EtapaOrdem)
class EtapaOrdemAdmin(admin.ModelAdmin):
    list_display = ['ordem', 'setor', 'status', 'operador', 'inicio', 'fim', 'pares_refugo']
    list_filter = [
        'status', 'setor',
        ('operador', admin.RelatedOnlyFieldListFilter),
        ('inicio', admin.DateFieldListFilter),
    ]
    search_fields = ['ordem__numero', 'ordem__modelo__nome']
    autocomplete_fields = ['ordem', 'operador']
    list_select_related = ['ordem__modelo', 'ordem__cor', 'setor', 'operador']
