from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import F
from django.test import TestCase, override_settings
from django.utils import timezone

from catalogo.models import Categoria, Cor, ItemFichaTecnica, Modelo, Tamanho, Variacao
from estoque.models import Material, MovimentacaoMaterial, TipoMovimentacao

from . import services
from .models import ItemOrdemProducao, OrdemProducao, Setor


class FluxoProducaoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('gerente', password='x')
        for seq, nome in enumerate(['Corte', 'Pesponto', 'Montagem'], start=1):
            Setor.objects.create(nome=nome, sequencia=seq)

        self.couro = Material.objects.create(
            codigo='CO-01', nome='Couro', tipo=Material.Tipo.COURO,
            unidade=Material.Unidade.METRO_QUADRADO, custo_unitario=Decimal('80'),
        )
        MovimentacaoMaterial.objects.create(
            material=self.couro, tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal('10'),
            motivo=MovimentacaoMaterial.Motivo.COMPRA,
        )
        self.modelo = Modelo.objects.create(
            referencia='TEN-01', nome='Tênis Casual', genero=Modelo.Genero.UNISSEX,
            categoria=Categoria.objects.create(nome='Tênis'), preco_venda=Decimal('250'),
        )
        ItemFichaTecnica.objects.create(
            modelo=self.modelo, material=self.couro, quantidade_por_par=Decimal('0.5'),
        )
        self.ordem = OrdemProducao.objects.create(
            modelo=self.modelo, cor=Cor.objects.create(nome='Branco'),
            data_prevista=timezone.localdate() + timedelta(days=10),
        )
        for numero, pares in [(38, 4), (40, 6)]:
            ItemOrdemProducao.objects.create(
                ordem=self.ordem, tamanho=Tamanho.objects.create(numero=numero), quantidade=pares,
            )

    def test_ordem_nova_recebe_numero_e_etapas(self):
        self.assertTrue(self.ordem.numero.startswith('OP-'))
        self.assertEqual(self.ordem.etapas.count(), 3)
        self.assertEqual(self.ordem.total_pares, 10)

    def test_fluxo_completo_movimenta_estoque(self):
        services.iniciar_ordem(self.ordem, self.usuario)
        self.couro.refresh_from_db()
        self.assertEqual(self.couro.estoque_atual, Decimal('5'))  # 10 pares x 0,5 m²

        for etapa in self.ordem.etapas.all():
            services.avancar_etapa(etapa, self.usuario)  # inicia
            etapa.refresh_from_db()
            services.avancar_etapa(etapa, self.usuario)  # conclui
        self.assertEqual(self.ordem.progresso, 100)

        services.concluir_ordem(self.ordem, self.usuario)
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.status, OrdemProducao.Status.CONCLUIDA)
        self.assertEqual(Variacao.objects.get(tamanho__numero=40).estoque_atual, 6)

    def test_nao_inicia_sem_material_suficiente(self):
        ItemOrdemProducao.objects.filter(ordem=self.ordem).update(quantidade=50)
        with self.assertRaises(ValidationError):
            services.iniciar_ordem(self.ordem, self.usuario)
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.status, OrdemProducao.Status.PLANEJADA)

    def test_etapas_seguem_a_sequencia(self):
        services.iniciar_ordem(self.ordem, self.usuario)
        ultima = self.ordem.etapas.last()
        with self.assertRaises(ValidationError):
            services.avancar_etapa(ultima, self.usuario)

    def test_nao_conclui_com_etapas_pendentes(self):
        services.iniciar_ordem(self.ordem, self.usuario)
        with self.assertRaises(ValidationError):
            services.concluir_ordem(self.ordem, self.usuario)


class PopularDadosTests(TestCase):
    def popular(self):
        call_command('popular_dados', stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_cria_cenario_completo(self):
        self.popular()
        for status in OrdemProducao.Status.values:
            self.assertTrue(OrdemProducao.objects.filter(status=status).exists(), status)
        self.assertTrue(any(o.atrasada for o in OrdemProducao.objects.all()))
        self.assertTrue(Material.objects.filter(estoque_atual__lt=F('estoque_minimo')).exists())
        self.assertTrue(Variacao.objects.filter(estoque_atual__lt=F('estoque_minimo')).exists())
        self.assertEqual(Variacao.objects.get(modelo__referencia='TEN-100', cor__nome='Branco', tamanho__numero=42).estoque_atual, 2)
        # 120 m² iniciais - consumo das 3 ordens iniciadas (26x0,35 + 20x0,40 + 20x0,60)
        self.assertEqual(Material.objects.get(codigo='MAT-001').estoque_atual, Decimal('90.9'))

    @override_settings(DEBUG=True)
    def test_pode_rodar_duas_vezes(self):
        self.popular()
        ordens = OrdemProducao.objects.count()
        saldo = Material.objects.get(codigo='MAT-001').estoque_atual
        self.popular()
        self.assertEqual(OrdemProducao.objects.count(), ordens)
        self.assertEqual(Material.objects.get(codigo='MAT-001').estoque_atual, saldo)

    @override_settings(DEBUG=False)
    def test_nao_roda_sem_debug(self):
        with self.assertRaises(CommandError):
            self.popular()
        self.assertFalse(User.objects.filter(username='admin').exists())
