from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from catalogo.models import Categoria, Cor, Modelo, Tamanho, Variacao

from .models import Material, MovimentacaoMaterial, MovimentacaoProduto, TipoMovimentacao


class MovimentacaoMaterialTests(TestCase):
    def setUp(self):
        self.material = Material.objects.create(
            codigo='CO-01', nome='Couro bovino', tipo=Material.Tipo.COURO,
            unidade=Material.Unidade.METRO_QUADRADO, custo_unitario=Decimal('80.00'),
        )

    def movimentar(self, tipo, quantidade):
        return MovimentacaoMaterial.objects.create(
            material=self.material, tipo=tipo, quantidade=Decimal(quantidade),
            motivo=MovimentacaoMaterial.Motivo.INVENTARIO,
        )

    def saldo(self):
        self.material.refresh_from_db()
        return self.material.estoque_atual

    def test_entrada_e_saida_atualizam_saldo(self):
        self.movimentar(TipoMovimentacao.ENTRADA, '10')
        self.movimentar(TipoMovimentacao.SAIDA, '3.5')
        self.assertEqual(self.saldo(), Decimal('6.5'))

    def test_edicao_recalcula_saldo(self):
        mov = self.movimentar(TipoMovimentacao.ENTRADA, '10')
        mov.quantidade = Decimal('4')
        mov.save()
        self.assertEqual(self.saldo(), Decimal('4'))

    def test_exclusao_desfaz_efeito(self):
        mov = self.movimentar(TipoMovimentacao.ENTRADA, '10')
        mov.delete()
        self.assertEqual(self.saldo(), Decimal('0'))

    def test_saida_maior_que_saldo_e_invalida(self):
        self.movimentar(TipoMovimentacao.ENTRADA, '2')
        mov = MovimentacaoMaterial(
            material=self.material, tipo=TipoMovimentacao.SAIDA, quantidade=Decimal('5'),
            motivo=MovimentacaoMaterial.Motivo.PERDA,
        )
        with self.assertRaises(ValidationError):
            mov.full_clean()


class MovimentacaoProdutoTests(TestCase):
    def test_entrada_de_pares_e_sku(self):
        modelo = Modelo.objects.create(
            referencia='SAN-001', nome='Sandália Verão', genero=Modelo.Genero.FEMININO,
            categoria=Categoria.objects.create(nome='Sandália'), preco_venda=Decimal('129.90'),
        )
        cor = Cor.objects.create(nome='Preto')
        variacao = Variacao.objects.create(
            modelo=modelo, cor=cor, tamanho=Tamanho.objects.create(numero=37),
        )
        MovimentacaoProduto.objects.create(
            variacao=variacao, tipo=TipoMovimentacao.ENTRADA, quantidade=12,
            motivo=MovimentacaoProduto.Motivo.INVENTARIO,
        )
        variacao.refresh_from_db()
        self.assertEqual(variacao.sku, f'SAN-001-{cor.pk}-37')
        self.assertEqual(variacao.estoque_atual, 12)
