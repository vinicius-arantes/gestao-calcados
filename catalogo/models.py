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
