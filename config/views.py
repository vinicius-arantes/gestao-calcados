from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.shortcuts import render
from django.utils import timezone

from catalogo.models import Variacao
from estoque.models import Material, MovimentacaoMaterial
from producao.models import OrdemProducao


@login_required
def inicio(request):
    """Painel com os indicadores que o perfil do usuário pode ver."""
    usuario = request.user
    contexto = {}

    if usuario.has_perm('producao.view_ordemproducao'):
        abertas = OrdemProducao.objects.filter(
            status__in=[OrdemProducao.Status.PLANEJADA, OrdemProducao.Status.EM_PRODUCAO],
        )
        por_status = dict(OrdemProducao.objects.values_list('status').annotate(total=Count('id')).order_by())
        contexto.update({
            'qtd_em_producao': por_status.get(OrdemProducao.Status.EM_PRODUCAO, 0),
            'qtd_atrasadas': abertas.filter(data_prevista__lt=timezone.localdate()).count(),
            'status_ordens': [
                (rotulo, por_status.get(valor, 0), valor) for valor, rotulo in OrdemProducao.Status.choices
            ],
            'proximas_entregas': abertas.select_related('modelo', 'cor').order_by('data_prevista')[:6],
        })

    if usuario.has_perm('catalogo.view_variacao'):
        contexto['pares_estoque'] = Variacao.objects.aggregate(total=Sum('estoque_atual'))['total'] or 0

    if usuario.has_perm('estoque.view_material'):
        repor = Material.objects.filter(ativo=True, estoque_atual__lt=F('estoque_minimo'))
        contexto['qtd_materiais_repor'] = repor.count()
        contexto['materiais_repor'] = repor.order_by('nome')[:6]

    if usuario.has_perm('estoque.view_movimentacaomaterial'):
        contexto['ultimas_movimentacoes'] = MovimentacaoMaterial.objects.select_related('material')[:6]

    return render(request, 'inicio.html', contexto)
