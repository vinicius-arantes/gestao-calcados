from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from catalogo.models import Categoria, Cor, Modelo, Tamanho, Variacao
from contas.models import GRUPO_ESTOQUISTA, GRUPO_GERENTE, GRUPO_OPERADOR

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


class TelasEstoqueTests(TestCase):
    def setUp(self):
        call_command('criar_grupos', stdout=StringIO())
        self.estoquista = self.criar_usuario('estoquista', GRUPO_ESTOQUISTA)
        self.gerente = self.criar_usuario('gerente', GRUPO_GERENTE)
        self.operador = self.criar_usuario('operador', GRUPO_OPERADOR)
        self.material = Material.objects.create(
            codigo='CO-01', nome='Couro', tipo=Material.Tipo.COURO, unidade=Material.Unidade.METRO_QUADRADO,
            custo_unitario=Decimal('80'), estoque_minimo=Decimal('10'),
        )

    def criar_usuario(self, nome, grupo):
        usuario = User.objects.create_user(nome)
        usuario.groups.add(Group.objects.get(name=grupo))
        return usuario

    def test_estoquista_cadastra_material_sem_informar_saldo(self):
        self.client.force_login(self.estoquista)
        self.client.post('/estoque/materiais/novo/', {
            'codigo': 'LI-01', 'nome': 'Linha', 'tipo': 'LINHA', 'unidade': 'm',
            'custo_unitario': '0.10', 'estoque_minimo': '100', 'ativo': 'on',
            'estoque_atual': '999',  # campo fora do formulário: deve ser ignorado
        })
        self.assertEqual(Material.objects.get(codigo='LI-01').estoque_atual, 0)

    def test_filtro_abaixo_do_minimo(self):
        self.client.force_login(self.estoquista)
        Material.objects.create(codigo='LI-01', nome='Linha', tipo='LINHA', unidade='m',
                                custo_unitario=Decimal('0.1'))
        resposta = self.client.get('/estoque/materiais/?repor=1')
        self.assertContains(resposta, 'CO-01')
        self.assertNotContains(resposta, 'LI-01')

    def test_movimentacao_registra_usuario_e_atualiza_saldo(self):
        self.client.force_login(self.gerente)
        self.client.post('/estoque/movimentacoes/material/', {
            'material': self.material.pk, 'tipo': 'E', 'motivo': 'COMPRA', 'quantidade': '25',
        })
        self.material.refresh_from_db()
        self.assertEqual(self.material.estoque_atual, Decimal('25'))
        self.assertEqual(MovimentacaoMaterial.objects.get().usuario, self.gerente)

    def test_formulario_barra_saida_maior_que_saldo(self):
        self.client.force_login(self.estoquista)
        resposta = self.client.post('/estoque/movimentacoes/material/', {
            'material': self.material.pk, 'tipo': 'S', 'motivo': 'PERDA', 'quantidade': '1',
        })
        self.assertContains(resposta, 'Saldo insuficiente')
        self.assertFalse(MovimentacaoMaterial.objects.exists())

    def test_consumo_da_producao_nao_e_lancado_manualmente(self):
        self.client.force_login(self.estoquista)
        resposta = self.client.post('/estoque/movimentacoes/material/', {
            'material': self.material.pk, 'tipo': 'E', 'motivo': 'CONSUMO', 'quantidade': '5',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(MovimentacaoMaterial.objects.exists())

    def test_permissoes_por_perfil(self):
        self.client.force_login(self.gerente)
        self.assertEqual(self.client.get('/estoque/materiais/').status_code, 200)
        self.assertEqual(self.client.get('/estoque/materiais/novo/').status_code, 403)
        self.client.force_login(self.operador)
        self.assertEqual(self.client.get('/estoque/produtos/').status_code, 200)
        self.assertEqual(self.client.get('/estoque/materiais/').status_code, 403)
        self.assertEqual(self.client.get('/estoque/movimentacoes/').status_code, 403)
