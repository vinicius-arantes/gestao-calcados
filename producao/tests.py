from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import F
from django.test import TestCase, override_settings
from django.utils import timezone

from catalogo.models import Categoria, Cor, ItemFichaTecnica, Modelo, Tamanho, Variacao
from contas.models import GRUPO_ESTOQUISTA, GRUPO_GERENTE, GRUPO_OPERADOR
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


class TelasProducaoTests(TestCase):
    def setUp(self):
        call_command('criar_grupos', stdout=StringIO())
        for seq, nome in enumerate(['Corte', 'Montagem'], start=1):
            Setor.objects.create(nome=nome, sequencia=seq)
        self.gerente = self.criar_usuario('gerente', GRUPO_GERENTE)
        self.operador = self.criar_usuario('operador', GRUPO_OPERADOR)
        self.estoquista = self.criar_usuario('estoquista', GRUPO_ESTOQUISTA)

        couro = Material.objects.create(
            codigo='CO-01', nome='Couro', tipo='COURO', unidade='m2', custo_unitario=Decimal('80'),
        )
        MovimentacaoMaterial.objects.create(
            material=couro, tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal('10'), motivo='COMPRA',
        )
        self.modelo = Modelo.objects.create(
            referencia='TEN-01', nome='Tênis', genero='U', preco_venda=Decimal('200'),
            categoria=Categoria.objects.create(nome='Tênis'),
        )
        ItemFichaTecnica.objects.create(modelo=self.modelo, material=couro, quantidade_por_par=Decimal('0.5'))
        self.cor = Cor.objects.create(nome='Preto')
        self.tamanho = Tamanho.objects.create(numero=40)

    def criar_usuario(self, nome, grupo):
        usuario = User.objects.create_user(nome)
        usuario.groups.add(Group.objects.get(name=grupo))
        return usuario

    def criar_ordem(self, pares=4):
        ordem = OrdemProducao.objects.create(
            modelo=self.modelo, cor=self.cor, data_prevista=timezone.localdate() + timedelta(days=5),
        )
        ItemOrdemProducao.objects.create(ordem=ordem, tamanho=self.tamanho, quantidade=pares)
        return ordem

    def test_gerente_cria_ordem_com_grade(self):
        self.client.force_login(self.gerente)
        resposta = self.client.post('/producao/ordens/nova/', {
            'modelo': self.modelo.pk, 'cor': self.cor.pk, 'prioridade': 2,
            'data_prevista': (timezone.localdate() + timedelta(days=5)).isoformat(),
            'itens-TOTAL_FORMS': '1', 'itens-INITIAL_FORMS': '0',
            'itens-MIN_NUM_FORMS': '1', 'itens-MAX_NUM_FORMS': '1000',
            'itens-0-tamanho': self.tamanho.pk, 'itens-0-quantidade': '6',
        })
        ordem = OrdemProducao.objects.get()
        self.assertRedirects(resposta, ordem.get_absolute_url())
        self.assertEqual(ordem.total_pares, 6)
        self.assertEqual(ordem.etapas.count(), 2)

    def test_ordem_sem_grade_nao_e_criada(self):
        self.client.force_login(self.gerente)
        self.client.post('/producao/ordens/nova/', {
            'modelo': self.modelo.pk, 'cor': self.cor.pk, 'prioridade': 2,
            'data_prevista': timezone.localdate().isoformat(),
            'itens-TOTAL_FORMS': '1', 'itens-INITIAL_FORMS': '0',
            'itens-MIN_NUM_FORMS': '1', 'itens-MAX_NUM_FORMS': '1000',
        })
        self.assertFalse(OrdemProducao.objects.exists())

    def test_fluxo_completo_pela_interface(self):
        ordem = self.criar_ordem(pares=4)
        self.client.force_login(self.gerente)
        self.client.post(f'/producao/ordens/{ordem.pk}/iniciar/')
        self.assertEqual(Material.objects.get().estoque_atual, Decimal('8'))

        self.client.force_login(self.operador)
        for etapa in ordem.etapas.all():
            self.client.post(f'/producao/etapas/{etapa.pk}/avancar/')
            self.client.post(f'/producao/etapas/{etapa.pk}/avancar/', {'pares_refugo': '0'})
        self.assertEqual(self.client.post(f'/producao/ordens/{ordem.pk}/concluir/').status_code, 403)

        self.client.force_login(self.gerente)
        self.client.post(f'/producao/ordens/{ordem.pk}/concluir/')
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemProducao.Status.CONCLUIDA)
        self.assertEqual(Variacao.objects.get().estoque_atual, 4)

    def test_iniciar_sem_material_mostra_erro(self):
        ordem = self.criar_ordem(pares=100)
        self.client.force_login(self.gerente)
        resposta = self.client.post(f'/producao/ordens/{ordem.pk}/iniciar/', follow=True)
        self.assertContains(resposta, 'Material insuficiente')
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemProducao.Status.PLANEJADA)

    def test_ordem_em_producao_nao_pode_ser_editada(self):
        ordem = self.criar_ordem()
        services.iniciar_ordem(ordem, self.gerente)
        self.client.force_login(self.gerente)
        self.assertEqual(self.client.get(f'/producao/ordens/{ordem.pk}/editar/').status_code, 404)
        self.assertEqual(self.client.get(f'/producao/ordens/{ordem.pk}/excluir/').status_code, 404)

    def test_avancar_etapa_nao_redireciona_para_outro_site(self):
        ordem = self.criar_ordem()
        services.iniciar_ordem(ordem, self.gerente)
        self.client.force_login(self.operador)
        resposta = self.client.post(
            f'/producao/etapas/{ordem.etapa_atual.pk}/avancar/', {'next': 'https://exemplo.com/'},
        )
        self.assertRedirects(resposta, ordem.get_absolute_url())

    def test_painel_do_operador_abre_no_setor_dele(self):
        montagem = Setor.objects.get(nome='Montagem')
        self.operador.perfil.setor = montagem
        self.operador.perfil.save()
        ordem = self.criar_ordem()
        services.iniciar_ordem(ordem, self.gerente)  # etapa atual: Corte
        self.client.force_login(self.operador)
        self.assertNotContains(self.client.get('/producao/painel/'), ordem.numero)
        self.assertContains(self.client.get('/producao/painel/?setor='), ordem.numero)

    def test_permissoes_por_perfil(self):
        ordem = self.criar_ordem()
        self.client.force_login(self.estoquista)
        self.assertEqual(self.client.get('/producao/ordens/').status_code, 200)
        self.assertEqual(self.client.get('/producao/ordens/nova/').status_code, 403)
        self.assertEqual(self.client.post(f'/producao/ordens/{ordem.pk}/iniciar/').status_code, 403)

    def test_painel_inicial_conforme_perfil(self):
        self.client.force_login(self.gerente)
        self.assertContains(self.client.get('/'), 'Materiais a repor')
        self.client.force_login(self.operador)
        resposta = self.client.get('/')
        self.assertContains(resposta, 'Ordens atrasadas')
        self.assertNotContains(resposta, 'Materiais a repor')
