from decimal import Decimal
from importlib import import_module

from django.apps import apps
from django.test import TestCase

from .models import Categoria, Cor, Modelo, Tamanho, Variacao


class SkuTests(TestCase):
    def setUp(self):
        self.modelo = Modelo.objects.create(
            referencia='TEN-100', nome='Tênis Urbano', genero=Modelo.Genero.UNISSEX,
            categoria=Categoria.objects.create(nome='Tênis'), preco_venda=Decimal('289.90'),
        )
        self.tamanho = Tamanho.objects.create(numero=40)

    def test_cores_com_o_mesmo_inicio_geram_skus_diferentes(self):
        marfim = Variacao.objects.create(
            modelo=self.modelo, cor=Cor.objects.create(nome='Marfim'), tamanho=self.tamanho,
        )
        marinho = Variacao.objects.create(
            modelo=self.modelo, cor=Cor.objects.create(nome='Marinho'), tamanho=self.tamanho,
        )
        self.assertNotEqual(marfim.sku, marinho.sku)

    def test_formato_do_sku(self):
        cor = Cor.objects.create(nome='Preto')
        variacao = Variacao.objects.create(modelo=self.modelo, cor=cor, tamanho=self.tamanho)
        self.assertEqual(variacao.sku, f'TEN-100-{cor.pk}-40')

    def test_migracao_recalcula_skus_existentes(self):
        cor = Cor.objects.create(nome='Preto')
        variacao = Variacao.objects.create(modelo=self.modelo, cor=cor, tamanho=self.tamanho)
        Variacao.objects.filter(pk=variacao.pk).update(sku='TEN-100-PRE-40')

        migracao = import_module('catalogo.migrations.0003_recalcula_sku')
        migracao.recalcular_skus(apps, None)

        variacao.refresh_from_db()
        self.assertEqual(variacao.sku, f'TEN-100-{cor.pk}-40')
