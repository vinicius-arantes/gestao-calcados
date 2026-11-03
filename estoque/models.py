from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F


class Fornecedor(models.Model):
    nome = models.CharField('razão social', max_length=120)
    cnpj = models.CharField('CNPJ', max_length=18, unique=True)
    email = models.EmailField('e-mail', blank=True)
    telefone = models.CharField('telefone', max_length=20, blank=True)
    cidade = models.CharField('cidade', max_length=80, blank=True)
    uf = models.CharField('UF', max_length=2, blank=True)
    ativo = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'fornecedor'
        verbose_name_plural = 'fornecedores'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Material(models.Model):
    """Matéria-prima ou insumo usado na fabricação dos calçados."""

    class Tipo(models.TextChoices):
        COURO = 'COURO', 'Couro'
        SINTETICO = 'SINTETICO', 'Sintético'
        TECIDO = 'TECIDO', 'Tecido'
        SOLADO = 'SOLADO', 'Solado'
        PALMILHA = 'PALMILHA', 'Palmilha'
        LINHA = 'LINHA', 'Linha'
        ADESIVO = 'ADESIVO', 'Adesivo'
        AVIAMENTO = 'AVIAMENTO', 'Aviamento'
        EMBALAGEM = 'EMBALAGEM', 'Embalagem'

    class Unidade(models.TextChoices):
        METRO = 'm', 'metro'
        METRO_QUADRADO = 'm2', 'm²'
        PAR = 'par', 'par'
        UNIDADE = 'un', 'unidade'
        QUILO = 'kg', 'kg'
        LITRO = 'l', 'litro'

    codigo = models.CharField('código', max_length=20, unique=True)
    nome = models.CharField('nome', max_length=100)
    tipo = models.CharField('tipo', max_length=10, choices=Tipo.choices)
    unidade = models.CharField('unidade', max_length=3, choices=Unidade.choices)
    fornecedor = models.ForeignKey(
        Fornecedor, verbose_name='fornecedor principal', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='materiais',
    )
    custo_unitario = models.DecimalField(
        'custo unitário (R$)', max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )
    estoque_atual = models.DecimalField('estoque atual', max_digits=12, decimal_places=3, default=0)
    estoque_minimo = models.DecimalField('estoque mínimo', max_digits=12, decimal_places=3, default=0)
    ativo = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'material'
        verbose_name_plural = 'materiais'
        ordering = ['nome']

    def __str__(self):
        return f'{self.codigo} — {self.nome}'

    @property
    def abaixo_do_minimo(self):
        return self.estoque_atual < self.estoque_minimo

    @property
    def valor_em_estoque(self):
        return self.estoque_atual * self.custo_unitario


class TipoMovimentacao(models.TextChoices):
    ENTRADA = 'E', 'Entrada'
    SAIDA = 'S', 'Saída'


class Movimentacao(models.Model):
    """
    Base abstrata das movimentações de estoque. Ao salvar ou excluir uma
    movimentação, o saldo do item movimentado é atualizado automaticamente.
    """

    tipo = models.CharField('tipo', max_length=1, choices=TipoMovimentacao.choices)
    data = models.DateTimeField('data', auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='usuário', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    ordem_producao = models.ForeignKey(
        'producao.OrdemProducao', verbose_name='ordem de produção', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    observacao = models.CharField('observação', max_length=200, blank=True)

    # Nome do campo (FK) do item cujo saldo é afetado; definido nas subclasses
    campo_item = None

    class Meta:
        abstract = True
        ordering = ['-data']

    @property
    def item(self):
        return getattr(self, self.campo_item)

    @property
    def item_id(self):
        return getattr(self, f'{self.campo_item}_id')

    def efeito(self):
        """Variação que esta movimentação causa no saldo (+ entrada, - saída)."""
        return self.quantidade if self.tipo == TipoMovimentacao.ENTRADA else -self.quantidade

    def clean(self):
        # Impede saída maior que o saldo disponível
        if self.tipo != TipoMovimentacao.SAIDA or not self.item_id or not self.quantidade:
            return
        saldo = self.item.estoque_atual
        if self.pk:
            antiga = type(self).objects.get(pk=self.pk)
            if antiga.item_id == self.item_id:
                saldo -= antiga.efeito()
        if self.quantidade > saldo:
            raise ValidationError({'quantidade': f'Saldo insuficiente. Disponível: {saldo}.'})

    def _aplicar(self, item_id, efeito):
        modelo_item = self._meta.get_field(self.campo_item).related_model
        modelo_item.objects.filter(pk=item_id).update(estoque_atual=F('estoque_atual') + efeito)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                # Em uma edição, desfaz o efeito antigo antes de aplicar o novo
                antiga = type(self).objects.select_for_update().get(pk=self.pk)
                self._aplicar(antiga.item_id, -antiga.efeito())
            super().save(*args, **kwargs)
            self._aplicar(self.item_id, self.efeito())

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            self._aplicar(self.item_id, -self.efeito())
            return super().delete(*args, **kwargs)


class MovimentacaoMaterial(Movimentacao):
    class Motivo(models.TextChoices):
        COMPRA = 'COMPRA', 'Compra de fornecedor'
        CONSUMO = 'CONSUMO', 'Consumo na produção'
        DEVOLUCAO = 'DEVOLUCAO', 'Devolução'
        PERDA = 'PERDA', 'Perda / avaria'
        INVENTARIO = 'INVENTARIO', 'Ajuste de inventário'

    material = models.ForeignKey(
        Material, verbose_name='material', on_delete=models.PROTECT, related_name='movimentacoes',
    )
    motivo = models.CharField('motivo', max_length=10, choices=Motivo.choices)
    quantidade = models.DecimalField(
        'quantidade', max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    custo_unitario = models.DecimalField(
        'custo unitário (R$)', max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Informe em compras para registrar o preço pago.',
    )

    campo_item = 'material'

    class Meta(Movimentacao.Meta):
        verbose_name = 'movimentação de material'
        verbose_name_plural = 'movimentações de material'

    def __str__(self):
        return f'{self.get_tipo_display()} de {self.quantidade} {self.material.unidade} — {self.material.nome}'


class MovimentacaoProduto(Movimentacao):
    class Motivo(models.TextChoices):
        PRODUCAO = 'PRODUCAO', 'Entrada da produção'
        VENDA = 'VENDA', 'Venda / expedição'
        DEVOLUCAO = 'DEVOLUCAO', 'Devolução de cliente'
        PERDA = 'PERDA', 'Perda / avaria'
        INVENTARIO = 'INVENTARIO', 'Ajuste de inventário'

    variacao = models.ForeignKey(
        'catalogo.Variacao', verbose_name='variação (SKU)', on_delete=models.PROTECT,
        related_name='movimentacoes',
    )
    motivo = models.CharField('motivo', max_length=10, choices=Motivo.choices)
    quantidade = models.PositiveIntegerField('quantidade (pares)', validators=[MinValueValidator(1)])

    campo_item = 'variacao'

    class Meta(Movimentacao.Meta):
        verbose_name = 'movimentação de produto'
        verbose_name_plural = 'movimentações de produto'

    def __str__(self):
        return f'{self.get_tipo_display()} de {self.quantidade} par(es) — {self.variacao}'
