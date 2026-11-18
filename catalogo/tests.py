from decimal import Decimal
from importlib import import_module
from io import StringIO

from django.apps import apps
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase

from contas.models import GRUPO_GERENTE, GRUPO_OPERADOR
from estoque.models import Material

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


class TelasCatalogoTests(TestCase):
    def setUp(self):
        call_command('criar_grupos', stdout=StringIO())
        self.gerente = User.objects.create_user('gerente')
        self.gerente.groups.add(Group.objects.get(name=GRUPO_GERENTE))
        self.operador = User.objects.create_user('operador')
        self.operador.groups.add(Group.objects.get(name=GRUPO_OPERADOR))
        self.categoria = Categoria.objects.create(nome='Tênis')
        self.material = Material.objects.create(
            codigo='CO-01', nome='Couro', tipo='COURO', unidade='m2', custo_unitario=Decimal('80'),
        )

    def dados_modelo(self, **extras):
        dados = {
            'referencia': 'TEN-01', 'nome': 'Tênis Casual', 'categoria': self.categoria.pk,
            'genero': 'U', 'preco_venda': '200.00', 'tempo_producao_min': '60', 'ativo': 'on',
            'ficha_tecnica-TOTAL_FORMS': '1', 'ficha_tecnica-INITIAL_FORMS': '0',
            'ficha_tecnica-MIN_NUM_FORMS': '0', 'ficha_tecnica-MAX_NUM_FORMS': '1000',
            'ficha_tecnica-0-material': self.material.pk, 'ficha_tecnica-0-quantidade_por_par': '0.5',
        }
        dados.update(extras)
        return dados

    def test_gerente_cadastra_modelo_com_ficha_tecnica(self):
        self.client.force_login(self.gerente)
        resposta = self.client.post('/catalogo/modelos/novo/', self.dados_modelo())
        modelo = Modelo.objects.get(referencia='TEN-01')
        self.assertRedirects(resposta, modelo.get_absolute_url())
        self.assertEqual(modelo.custo_materiais, Decimal('40'))

    def test_lista_filtra_por_busca(self):
        self.client.force_login(self.operador)
        Modelo.objects.create(referencia='BOT-01', nome='Bota', categoria=self.categoria,
                              genero='F', preco_venda=Decimal('300'))
        resposta = self.client.get('/catalogo/modelos/?q=bota')
        self.assertContains(resposta, 'Bota')
        self.assertNotContains(self.client.get('/catalogo/modelos/?q=sandalia'), 'BOT-01')

    def test_operador_consulta_mas_nao_cadastra(self):
        self.client.force_login(self.operador)
        self.assertEqual(self.client.get('/catalogo/modelos/').status_code, 200)
        self.assertEqual(self.client.get('/catalogo/modelos/novo/').status_code, 403)
        self.assertEqual(self.client.post('/catalogo/modelos/novo/', self.dados_modelo()).status_code, 403)
        self.assertFalse(Modelo.objects.exists())

    def test_crud_de_categoria(self):
        self.client.force_login(self.gerente)
        self.client.post('/catalogo/categorias/nova/', {'nome': 'Bota', 'descricao': ''})
        categoria = Categoria.objects.get(nome='Bota')
        self.client.post(f'/catalogo/categorias/{categoria.pk}/editar/', {'nome': 'Botas', 'descricao': 'Cano curto'})
        categoria.refresh_from_db()
        self.assertEqual(categoria.descricao, 'Cano curto')
        self.client.post(f'/catalogo/categorias/{categoria.pk}/excluir/')
        self.assertFalse(Categoria.objects.filter(pk=categoria.pk).exists())

    def test_nao_exclui_categoria_em_uso(self):
        self.client.force_login(self.gerente)
        Modelo.objects.create(referencia='BOT-01', nome='Bota', categoria=self.categoria,
                              genero='F', preco_venda=Decimal('300'))
        resposta = self.client.post(f'/catalogo/categorias/{self.categoria.pk}/excluir/', follow=True)
        self.assertContains(resposta, 'Não é possível excluir')
        self.assertTrue(Categoria.objects.filter(pk=self.categoria.pk).exists())
