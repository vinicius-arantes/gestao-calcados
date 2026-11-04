from datetime import timedelta
from decimal import Decimal as D

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalogo.models import Categoria, Colecao, Cor, ItemFichaTecnica, Modelo, Tamanho, Variacao
from contas.models import GRUPO_ESTOQUISTA, GRUPO_GERENTE, GRUPO_OPERADOR
from estoque.models import (
    Fornecedor, Material, MovimentacaoMaterial, MovimentacaoProduto, TipoMovimentacao,
)
from producao import services
from producao.models import ItemOrdemProducao, OrdemProducao, Setor

# Senha usada apenas nos usuários de demonstração (o comando só roda com DEBUG ligado)
SENHA_DEMO = 'passofirme123'

SETORES = ['Corte', 'Pesponto', 'Montagem', 'Acabamento', 'Expedição']

USUARIOS = [
    # usuário, nome, sobrenome, grupo, acessa o admin?, setor
    ('gerente', 'Gabriela', 'Gerente', GRUPO_GERENTE, True, None),
    ('estoquista', 'Eduardo', 'Estoquista', GRUPO_ESTOQUISTA, True, None),
    ('operador', 'Otávio', 'Operador', GRUPO_OPERADOR, False, 'Pesponto'),
]

FORNECEDORES = {
    'couro': ('Curtume Demonstração Ltda', '00.000.001/0001-00', 'Franca', 'SP'),
    'solado': ('Solados Exemplo S.A.', '00.000.002/0001-00', 'Novo Hamburgo', 'RS'),
    'insumos': ('Insumos Fictícios Ltda', '00.000.003/0001-00', 'Birigui', 'SP'),
}

MATERIAIS = {
    # código: nome, tipo, unidade, fornecedor, custo, saldo inicial, estoque mínimo
    'MAT-001': ('Couro bovino', 'COURO', 'm2', 'couro', '85.00', '120', '40'),
    'MAT-002': ('Sintético liso', 'SINTETICO', 'm2', 'couro', '32.00', '30', '50'),
    'MAT-003': ('Solado de borracha', 'SOLADO', 'par', 'solado', '18.50', '300', '100'),
    'MAT-004': ('Solado EVA', 'SOLADO', 'par', 'solado', '12.00', '80', '100'),
    'MAT-005': ('Palmilha anatômica', 'PALMILHA', 'par', 'solado', '6.50', '400', '100'),
    'MAT-006': ('Linha de pesponto', 'LINHA', 'm', 'insumos', '0.08', '5000', '1000'),
    'MAT-007': ('Adesivo PU', 'ADESIVO', 'l', 'insumos', '28.00', '40', '15'),
    'MAT-008': ('Cadarço', 'AVIAMENTO', 'par', 'insumos', '1.90', '200', '50'),
    'MAT-009': ('Fivela metálica', 'AVIAMENTO', 'un', 'insumos', '2.40', '60', '80'),
    'MAT-010': ('Caixa de papelão', 'EMBALAGEM', 'un', 'insumos', '3.20', '500', '200'),
}

BASE_FICHA = [('MAT-006', '4'), ('MAT-007', '0.03'), ('MAT-010', '1')]

MODELOS = {
    # referência: nome, categoria, coleção, gênero, preço, ficha técnica
    'TEN-100': ('Tênis Urbano', 'Tênis', 'verao', 'U', '289.90', [
        ('MAT-001', '0.35'), ('MAT-003', '1'), ('MAT-005', '1'), ('MAT-008', '1'), *BASE_FICHA,
    ]),
    'SAP-200': ('Sapato Social Clássico', 'Sapato social', 'inverno', 'M', '349.90', [
        ('MAT-001', '0.40'), ('MAT-003', '1'), ('MAT-005', '1'), *BASE_FICHA,
    ]),
    'BOT-300': ('Bota Cano Curto', 'Bota', 'inverno', 'F', '419.90', [
        ('MAT-001', '0.60'), ('MAT-003', '1'), ('MAT-005', '1'), ('MAT-009', '1'), *BASE_FICHA,
    ]),
    'SAN-400': ('Sandália Leve', 'Sandália', 'verao', 'F', '139.90', [
        ('MAT-002', '0.15'), ('MAT-004', '1'), ('MAT-009', '2'), *BASE_FICHA,
    ]),
}

ORDENS = [
    # referência, cor, descrição (identifica a ordem), status final, prazo em dias, grade
    ('TEN-100', 'Branco', 'Reposição de estoque do Tênis Urbano', 'CONCLUIDA', -3, {38: 8, 40: 12, 42: 6}),
    ('SAP-200', 'Preto', 'Pedido de lojas parceiras', 'EM_PRODUCAO', 9, {39: 6, 41: 10, 43: 4}),
    ('BOT-300', 'Marrom', 'Lançamento da coleção de inverno', 'ATRASADA', -2, {35: 5, 37: 10, 39: 5}),
    ('SAN-400', 'Bege', 'Sandália para feira de verão', 'PLANEJADA', 15, {34: 15, 36: 25, 38: 20}),
    ('TEN-100', 'Preto', 'Pedido cancelado pelo cliente', 'CANCELADA', 20, {40: 10}),
]


class Command(BaseCommand):
    help = 'Popula o banco com dados de demonstração. Pode ser executado mais de uma vez.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Por segurança, este comando só roda com DEBUG ligado.')

        call_command('criar_grupos', stdout=self.stdout)
        setores = self._criar_setores()
        usuarios = self._criar_usuarios(setores)
        self._criar_catalogo_e_materiais(usuarios['estoquista'])
        self._criar_ordens(usuarios)

        self.stdout.write(self.style.SUCCESS(
            f'Dados prontos. Usuários: admin, gerente, estoquista, operador — senha: {SENHA_DEMO}'
        ))

    def _criar_setores(self):
        setores = {}
        proxima = max(Setor.objects.values_list('sequencia', flat=True), default=0) + 1
        for nome in SETORES:
            setor, criado = Setor.objects.get_or_create(nome=nome, defaults={'sequencia': proxima})
            proxima += 1 if criado else 0
            setores[nome] = setor
        return setores

    def _criar_usuario(self, username, **dados):
        usuario, criado = User.objects.get_or_create(username=username, defaults=dados)
        if criado:
            usuario.set_password(SENHA_DEMO)
            usuario.save()
        return usuario

    def _criar_usuarios(self, setores):
        usuarios = {'admin': self._criar_usuario(
            'admin', first_name='Ana', last_name='Administradora', is_staff=True, is_superuser=True,
        )}
        for username, nome, sobrenome, grupo, staff, setor in USUARIOS:
            usuario = self._criar_usuario(
                username, first_name=nome, last_name=sobrenome, is_staff=staff,
            )
            usuario.groups.add(Group.objects.get(name=grupo))
            if setor:
                usuario.perfil.setor = setores[setor]
                usuario.perfil.save()
            usuarios[username] = usuario
        return usuarios

    def _criar_catalogo_e_materiais(self, estoquista):
        fornecedores = {
            chave: Fornecedor.objects.get_or_create(
                cnpj=cnpj, defaults={'nome': nome, 'cidade': cidade, 'uf': uf},
            )[0]
            for chave, (nome, cnpj, cidade, uf) in FORNECEDORES.items()
        }
        for codigo, (nome, tipo, unidade, fornecedor, custo, saldo, minimo) in MATERIAIS.items():
            material, criado = Material.objects.get_or_create(codigo=codigo, defaults={
                'nome': nome, 'tipo': tipo, 'unidade': unidade, 'custo_unitario': D(custo),
                'fornecedor': fornecedores[fornecedor], 'estoque_minimo': D(minimo),
            })
            if criado:
                # O saldo inicial entra por movimentação, como no uso real do sistema
                MovimentacaoMaterial.objects.create(
                    material=material, tipo=TipoMovimentacao.ENTRADA, quantidade=D(saldo),
                    motivo=MovimentacaoMaterial.Motivo.COMPRA, custo_unitario=D(custo),
                    usuario=estoquista, observacao='Saldo inicial',
                )

        for numero in range(34, 45):
            Tamanho.objects.get_or_create(numero=numero)
        for nome, codigo in [('Branco', '#FFFFFF'), ('Preto', '#000000'), ('Marrom', '#6F4E37'), ('Bege', '#D9C3A0')]:
            Cor.objects.get_or_create(nome=nome, defaults={'codigo_hex': codigo})

        colecoes = {
            'verao': Colecao.objects.get_or_create(nome='Essencial', ano=2026, estacao='PV')[0],
            'inverno': Colecao.objects.get_or_create(nome='Essencial', ano=2026, estacao='OI')[0],
        }
        for referencia, (nome, categoria, colecao, genero, preco, ficha) in MODELOS.items():
            modelo, criado = Modelo.objects.get_or_create(referencia=referencia, defaults={
                'nome': nome, 'genero': genero, 'preco_venda': D(preco),
                'categoria': Categoria.objects.get_or_create(nome=categoria)[0],
                'colecao': colecoes[colecao],
            })
            if criado:
                for codigo, quantidade in ficha:
                    ItemFichaTecnica.objects.create(
                        modelo=modelo, material=Material.objects.get(codigo=codigo),
                        quantidade_por_par=D(quantidade),
                    )

    def _criar_ordens(self, usuarios):
        hoje = timezone.localdate()
        gerente, operador = usuarios['gerente'], usuarios['operador']
        for referencia, cor, descricao, situacao, prazo, grade in ORDENS:
            if OrdemProducao.objects.filter(observacoes=descricao).exists():
                continue
            ordem = OrdemProducao.objects.create(
                modelo=Modelo.objects.get(referencia=referencia), cor=Cor.objects.get(nome=cor),
                responsavel=gerente, observacoes=descricao,
                data_emissao=hoje - timedelta(days=20), data_prevista=hoje + timedelta(days=prazo),
            )
            for numero, pares in grade.items():
                ItemOrdemProducao.objects.create(
                    ordem=ordem, tamanho=Tamanho.objects.get(numero=numero), quantidade=pares,
                )

            if situacao == 'CANCELADA':
                ordem.status = OrdemProducao.Status.CANCELADA
                ordem.save(update_fields=['status'])
            elif situacao == 'CONCLUIDA':
                services.iniciar_ordem(ordem, gerente)
                self._avancar(ordem, operador, ordem.etapas.count())
                services.concluir_ordem(ordem, gerente)
                self._vender_e_definir_minimos(ordem, gerente)
            elif situacao == 'EM_PRODUCAO':
                services.iniciar_ordem(ordem, gerente)
                self._avancar(ordem, operador, 2)
            elif situacao == 'ATRASADA':
                services.iniciar_ordem(ordem, gerente)
                self._avancar(ordem, operador, 1)

    def _avancar(self, ordem, operador, etapas_concluidas):
        """Conclui as primeiras etapas e deixa a seguinte em andamento, se houver."""
        for _ in range(etapas_concluidas):
            etapa = ordem.etapa_atual
            services.avancar_etapa(etapa, operador)  # inicia
            etapa.refresh_from_db()
            services.avancar_etapa(etapa, operador)  # conclui
        etapa = ordem.etapa_atual
        if etapa:
            services.avancar_etapa(etapa, operador)

    def _vender_e_definir_minimos(self, ordem, usuario):
        # Deixa um SKU abaixo do mínimo para aparecer no filtro de situação do estoque
        variacoes = Variacao.objects.filter(modelo=ordem.modelo, cor=ordem.cor)
        variacoes.update(estoque_minimo=5)
        MovimentacaoProduto.objects.create(
            variacao=variacoes.get(tamanho__numero=42), tipo=TipoMovimentacao.SAIDA, quantidade=4,
            motivo=MovimentacaoProduto.Motivo.VENDA, usuario=usuario, observacao='Venda a lojista',
        )
