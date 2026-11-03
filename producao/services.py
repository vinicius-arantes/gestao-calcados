"""
Regras de negócio do fluxo de produção, compartilhadas entre o Django Admin
e as telas da área do usuário.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from catalogo.models import Variacao
from estoque.models import MovimentacaoMaterial, MovimentacaoProduto, TipoMovimentacao

from .models import EtapaOrdem, OrdemProducao


def materiais_faltantes(ordem):
    """Retorna [(material, necessário, disponível)] dos materiais sem saldo suficiente."""
    return [
        (material, necessario, material.estoque_atual)
        for material, necessario in ordem.necessidade_materiais()
        if necessario > material.estoque_atual
    ]


@transaction.atomic
def iniciar_ordem(ordem, usuario):
    """Dá baixa nos materiais da ficha técnica e coloca a OP em produção."""
    if ordem.status != OrdemProducao.Status.PLANEJADA:
        raise ValidationError('Apenas ordens planejadas podem ser iniciadas.')
    if ordem.total_pares == 0:
        raise ValidationError('Informe a grade de tamanhos antes de iniciar a ordem.')
    if not ordem.modelo.ficha_tecnica.exists():
        raise ValidationError('O modelo não possui ficha técnica cadastrada.')
    faltantes = materiais_faltantes(ordem)
    if faltantes:
        lista = ', '.join(
            f'{m.nome} (faltam {necessario - disponivel:.3f} {m.unidade})'
            for m, necessario, disponivel in faltantes
        )
        raise ValidationError(f'Material insuficiente: {lista}.')

    for material, quantidade in ordem.necessidade_materiais():
        MovimentacaoMaterial.objects.create(
            material=material, tipo=TipoMovimentacao.SAIDA,
            motivo=MovimentacaoMaterial.Motivo.CONSUMO, quantidade=quantidade,
            usuario=usuario, ordem_producao=ordem, observacao=f'Consumo da {ordem.numero}',
        )
    ordem.status = OrdemProducao.Status.EM_PRODUCAO
    ordem.data_inicio = timezone.now()
    ordem.save(update_fields=['status', 'data_inicio'])


@transaction.atomic
def avancar_etapa(etapa, usuario, pares_refugo=0, observacao=''):
    """Inicia a etapa pendente ou conclui a etapa em andamento, respeitando a sequência."""
    ordem = etapa.ordem
    if ordem.status != OrdemProducao.Status.EM_PRODUCAO:
        raise ValidationError('A ordem precisa estar em produção.')
    if etapa != ordem.etapa_atual:
        raise ValidationError('As etapas devem seguir a sequência dos setores.')

    agora = timezone.now()
    if etapa.status == EtapaOrdem.Status.PENDENTE:
        etapa.status = EtapaOrdem.Status.EM_ANDAMENTO
        etapa.inicio = agora
        etapa.operador = usuario
    else:
        etapa.status = EtapaOrdem.Status.CONCLUIDA
        etapa.fim = agora
        etapa.pares_refugo = pares_refugo
        etapa.observacao = observacao
    etapa.save()


@transaction.atomic
def concluir_ordem(ordem, usuario):
    """Finaliza a OP e dá entrada dos pares produzidos no estoque de produto acabado."""
    if ordem.status != OrdemProducao.Status.EM_PRODUCAO:
        raise ValidationError('Apenas ordens em produção podem ser concluídas.')
    if ordem.etapas.exclude(status=EtapaOrdem.Status.CONCLUIDA).exists():
        raise ValidationError('Todas as etapas precisam estar concluídas.')

    for item in ordem.itens.select_related('tamanho'):
        variacao, _ = Variacao.objects.get_or_create(
            modelo=ordem.modelo, cor=ordem.cor, tamanho=item.tamanho,
        )
        MovimentacaoProduto.objects.create(
            variacao=variacao, tipo=TipoMovimentacao.ENTRADA,
            motivo=MovimentacaoProduto.Motivo.PRODUCAO, quantidade=item.quantidade,
            usuario=usuario, ordem_producao=ordem, observacao=f'Entrada da {ordem.numero}',
        )
    ordem.status = OrdemProducao.Status.CONCLUIDA
    ordem.data_conclusao = timezone.now()
    ordem.save(update_fields=['status', 'data_conclusao'])
