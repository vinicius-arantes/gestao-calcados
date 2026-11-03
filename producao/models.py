from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Setor(models.Model):
    """Setor da fábrica por onde a ordem de produção passa (corte, pesponto...)."""

    nome = models.CharField('nome', max_length=60, unique=True)
    sequencia = models.PositiveSmallIntegerField('sequência no fluxo', unique=True)
    descricao = models.TextField('descrição', blank=True)
    ativo = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'setor'
        verbose_name_plural = 'setores'
        ordering = ['sequencia']

    def __str__(self):
        return self.nome


class OrdemProducao(models.Model):
    class Status(models.TextChoices):
        PLANEJADA = 'PLANEJADA', 'Planejada'
        EM_PRODUCAO = 'EM_PRODUCAO', 'Em produção'
        CONCLUIDA = 'CONCLUIDA', 'Concluída'
        CANCELADA = 'CANCELADA', 'Cancelada'

    class Prioridade(models.IntegerChoices):
        BAIXA = 1, 'Baixa'
        NORMAL = 2, 'Normal'
        ALTA = 3, 'Alta'
        URGENTE = 4, 'Urgente'

    numero = models.CharField('número', max_length=12, unique=True, editable=False)
    modelo = models.ForeignKey(
        'catalogo.Modelo', verbose_name='modelo', on_delete=models.PROTECT, related_name='ordens',
    )
    cor = models.ForeignKey('catalogo.Cor', verbose_name='cor', on_delete=models.PROTECT)
    status = models.CharField('status', max_length=12, choices=Status.choices, default=Status.PLANEJADA)
    prioridade = models.PositiveSmallIntegerField(
        'prioridade', choices=Prioridade.choices, default=Prioridade.NORMAL,
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='responsável', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ordens_responsavel',
    )
    data_emissao = models.DateField('data de emissão', default=timezone.localdate)
    data_prevista = models.DateField('data prevista de entrega')
    data_inicio = models.DateTimeField('início da produção', null=True, blank=True)
    data_conclusao = models.DateTimeField('conclusão', null=True, blank=True)
    observacoes = models.TextField('observações', blank=True)

    class Meta:
        verbose_name = 'ordem de produção'
        verbose_name_plural = 'ordens de produção'
        ordering = ['-data_emissao', '-numero']
        permissions = [
            ('iniciar_ordemproducao', 'Pode iniciar ordem de produção'),
            ('concluir_ordemproducao', 'Pode concluir ordem de produção'),
        ]

    def __str__(self):
        return f'{self.numero} — {self.modelo.referencia} {self.cor}'

    def save(self, *args, **kwargs):
        criando = self.pk is None
        if not self.numero:
            ultimo = OrdemProducao.objects.order_by('-id').values_list('id', flat=True).first() or 0
            self.numero = f'OP-{ultimo + 1:05d}'
        super().save(*args, **kwargs)
        if criando:
            # Cria automaticamente uma etapa para cada setor ativo do fluxo
            EtapaOrdem.objects.bulk_create(
                EtapaOrdem(ordem=self, setor=setor) for setor in Setor.objects.filter(ativo=True)
            )

    @property
    def cor_status(self):
        """Classe de cor do Bootstrap usada nos badges de status."""
        return {
            'PLANEJADA': 'secondary', 'EM_PRODUCAO': 'primary',
            'CONCLUIDA': 'success', 'CANCELADA': 'danger',
        }[self.status]

    @property
    def total_pares(self):
        return self.itens.aggregate(total=Sum('quantidade'))['total'] or 0

    @property
    def atrasada(self):
        aberta = self.status in (self.Status.PLANEJADA, self.Status.EM_PRODUCAO)
        return aberta and self.data_prevista < timezone.localdate()

    @property
    def progresso(self):
        """Percentual de etapas concluídas."""
        etapas = list(self.etapas.all())
        if not etapas:
            return 0
        concluidas = sum(1 for e in etapas if e.status == EtapaOrdem.Status.CONCLUIDA)
        return round(concluidas * 100 / len(etapas))

    @property
    def etapa_atual(self):
        return self.etapas.exclude(status=EtapaOrdem.Status.CONCLUIDA).first()

    def necessidade_materiais(self):
        """Lista (material, quantidade necessária) para produzir todos os pares da OP."""
        pares = self.total_pares
        return [
            (item.material, item.quantidade_por_par * pares)
            for item in self.modelo.ficha_tecnica.select_related('material')
        ]


class ItemOrdemProducao(models.Model):
    """Grade da OP: quantos pares de cada numeração serão produzidos."""

    ordem = models.ForeignKey(
        OrdemProducao, verbose_name='ordem', on_delete=models.CASCADE, related_name='itens',
    )
    tamanho = models.ForeignKey('catalogo.Tamanho', verbose_name='tamanho', on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField('pares', validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'item da grade'
        verbose_name_plural = 'grade de tamanhos'
        ordering = ['tamanho__numero']
        constraints = [
            models.UniqueConstraint(fields=['ordem', 'tamanho'], name='tamanho_unico_na_ordem'),
        ]

    def __str__(self):
        return f'{self.tamanho}: {self.quantidade} pares'


class EtapaOrdem(models.Model):
    """Acompanhamento da OP em cada setor da fábrica."""

    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em andamento'
        CONCLUIDA = 'CONCLUIDA', 'Concluída'

    ordem = models.ForeignKey(
        OrdemProducao, verbose_name='ordem', on_delete=models.CASCADE, related_name='etapas',
    )
    setor = models.ForeignKey(Setor, verbose_name='setor', on_delete=models.PROTECT)
    status = models.CharField('status', max_length=12, choices=Status.choices, default=Status.PENDENTE)
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='operador', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='etapas',
    )
    inicio = models.DateTimeField('início', null=True, blank=True)
    fim = models.DateTimeField('fim', null=True, blank=True)
    pares_refugo = models.PositiveIntegerField('pares com defeito', default=0)
    observacao = models.CharField('observação', max_length=200, blank=True)

    class Meta:
        verbose_name = 'etapa da ordem'
        verbose_name_plural = 'etapas da ordem'
        ordering = ['ordem', 'setor__sequencia']
        constraints = [
            models.UniqueConstraint(fields=['ordem', 'setor'], name='setor_unico_na_ordem'),
        ]

    def __str__(self):
        return f'{self.ordem.numero} · {self.setor}'

    @property
    def cor_status(self):
        return {'PENDENTE': 'secondary', 'EM_ANDAMENTO': 'warning', 'CONCLUIDA': 'success'}[self.status]

    @property
    def duracao(self):
        if self.inicio and self.fim:
            return self.fim - self.inicio
        return None
