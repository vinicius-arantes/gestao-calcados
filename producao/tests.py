from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
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
