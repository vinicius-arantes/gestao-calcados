from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class Categoria(models.Model):
    nome = models.CharField('nome', max_length=60, unique=True)
    descricao = models.TextField('descrição', blank=True)

    class Meta:
        verbose_name = 'categoria'
        verbose_name_plural = 'categorias'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Colecao(models.Model):
    class Estacao(models.TextChoices):
        PRIMAVERA_VERAO = 'PV', 'Primavera/Verão'
        OUTONO_INVERNO = 'OI', 'Outono/Inverno'

    nome = models.CharField('nome', max_length=80)
    ano = models.PositiveIntegerField('ano', validators=[MinValueValidator(2000)])
    estacao = models.CharField('estação', max_length=2, choices=Estacao.choices)
    ativa = models.BooleanField('ativa', default=True)

    class Meta:
        verbose_name = 'coleção'
        verbose_name_plural = 'coleções'
        ordering = ['-ano', 'estacao']
        constraints = [
            models.UniqueConstraint(fields=['nome', 'ano', 'estacao'], name='colecao_unica'),
        ]

    def __str__(self):
        return f'{self.nome} {self.get_estacao_display()} {self.ano}'


class Cor(models.Model):
    nome = models.CharField('nome', max_length=40, unique=True)
    codigo_hex = models.CharField(
        'código hexadecimal', max_length=7, default='#000000',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Use o formato #RRGGBB.')],
    )

    class Meta:
        verbose_name = 'cor'
        verbose_name_plural = 'cores'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Tamanho(models.Model):
    numero = models.PositiveSmallIntegerField('numeração', unique=True)

    class Meta:
        verbose_name = 'tamanho'
        verbose_name_plural = 'tamanhos'
        ordering = ['numero']

    def __str__(self):
        return str(self.numero)


class Modelo(models.Model):
    """Modelo de calçado (produto) fabricado pela empresa."""

    class Genero(models.TextChoices):
        FEMININO = 'F', 'Feminino'
        MASCULINO = 'M', 'Masculino'
        UNISSEX = 'U', 'Unissex'
        INFANTIL = 'I', 'Infantil'

    referencia = models.CharField('referência', max_length=20, unique=True)
    nome = models.CharField('nome', max_length=100)
    categoria = models.ForeignKey(
        Categoria, verbose_name='categoria', on_delete=models.PROTECT, related_name='modelos',
    )
    colecao = models.ForeignKey(
        Colecao, verbose_name='coleção', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='modelos',
    )
    genero = models.CharField('gênero', max_length=1, choices=Genero.choices)
    descricao = models.TextField('descrição', blank=True)
    preco_venda = models.DecimalField(
        'preço de venda (R$)', max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )
    tempo_producao_min = models.PositiveIntegerField('tempo de produção por par (min)', default=60)
    ativo = models.BooleanField('ativo', default=True)
    criado_em = models.DateTimeField('criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'modelo'
        verbose_name_plural = 'modelos'
        ordering = ['referencia']

    def __str__(self):
        return f'{self.referencia} — {self.nome}'

    @property
    def custo_materiais(self):
        """Custo de matéria-prima por par, calculado a partir da ficha técnica."""
        return sum(
            (item.custo for item in self.ficha_tecnica.select_related('material')),
            Decimal('0'),
        )

    @property
    def margem(self):
        """Margem bruta (%) sobre o preço de venda, considerando só a matéria-prima."""
        if not self.preco_venda:
            return None
        return (self.preco_venda - self.custo_materiais) / self.preco_venda * 100

    @property
    def estoque_total(self):
        return self.variacoes.aggregate(total=models.Sum('estoque_atual'))['total'] or 0


class ItemFichaTecnica(models.Model):
    """Quantidade de cada material consumida para fabricar um par do modelo."""

    modelo = models.ForeignKey(
        Modelo, verbose_name='modelo', on_delete=models.CASCADE, related_name='ficha_tecnica',
    )
    material = models.ForeignKey(
        'estoque.Material', verbose_name='material', on_delete=models.PROTECT, related_name='usos',
    )
    quantidade_por_par = models.DecimalField(
        'quantidade por par', max_digits=10, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )

    class Meta:
        verbose_name = 'item da ficha técnica'
        verbose_name_plural = 'ficha técnica'
        constraints = [
            models.UniqueConstraint(fields=['modelo', 'material'], name='material_unico_na_ficha'),
        ]

    def __str__(self):
        return f'{self.material} ({self.quantidade_por_par} {self.material.get_unidade_display()})'

    @property
    def custo(self):
        return self.quantidade_por_par * self.material.custo_unitario


class Variacao(models.Model):
    """SKU: combinação de modelo + cor + tamanho, com saldo de produto acabado."""

    modelo = models.ForeignKey(
        Modelo, verbose_name='modelo', on_delete=models.CASCADE, related_name='variacoes',
    )
    cor = models.ForeignKey(Cor, verbose_name='cor', on_delete=models.PROTECT)
    tamanho = models.ForeignKey(Tamanho, verbose_name='tamanho', on_delete=models.PROTECT)
    sku = models.CharField('SKU', max_length=40, unique=True, editable=False)
    estoque_atual = models.IntegerField('estoque atual (pares)', default=0)
    estoque_minimo = models.PositiveIntegerField('estoque mínimo (pares)', default=0)

    class Meta:
        verbose_name = 'variação (SKU)'
        verbose_name_plural = 'variações (SKU)'
        ordering = ['modelo__referencia', 'cor__nome', 'tamanho__numero']
        constraints = [
            models.UniqueConstraint(fields=['modelo', 'cor', 'tamanho'], name='variacao_unica'),
        ]

    def __str__(self):
        return f'{self.modelo.referencia} {self.cor} {self.tamanho}'

    def save(self, *args, **kwargs):
        # SKU gerado automaticamente, ex.: SAN-001-PRE-37
        self.sku = f'{self.modelo.referencia}-{self.cor.nome[:3].upper()}-{self.tamanho.numero}'
        super().save(*args, **kwargs)

    @property
    def abaixo_do_minimo(self):
        return self.estoque_atual < self.estoque_minimo
