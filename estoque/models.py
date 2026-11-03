from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


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
