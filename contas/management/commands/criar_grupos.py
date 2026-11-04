from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from contas.models import GRUPO_ESTOQUISTA, GRUPO_GERENTE, GRUPO_OPERADOR

# Regras no formato 'app.codename'. 'app.*' = todas do app; 'app.view_*' = todas de consulta do app.
PERMISSOES = {
    GRUPO_GERENTE: [
        'catalogo.*',
        'producao.*',
        'estoque.view_*',
        'estoque.add_movimentacaomaterial',
        'estoque.add_movimentacaoproduto',
        'contas.view_perfil',
        # Necessária para escolher o responsável da ordem na busca do admin
        'auth.view_user',
    ],
    GRUPO_ESTOQUISTA: [
        'estoque.*',
        'catalogo.view_*',
        'catalogo.add_variacao',
        'catalogo.change_variacao',
        'producao.view_*',
    ],
    GRUPO_OPERADOR: [
        'catalogo.view_*',
        'producao.view_*',
        'producao.change_etapaordem',
    ],
}


def resolver_regra(regra):
    app, codename = regra.split('.')
    permissoes = Permission.objects.filter(content_type__app_label=app)
    if codename == '*':
        return permissoes
    if codename.endswith('*'):
        return permissoes.filter(codename__startswith=codename[:-1])
    permissoes = permissoes.filter(codename=codename)
    if not permissoes.exists():
        raise CommandError(f'Permissão inexistente: {regra}')
    return permissoes


class Command(BaseCommand):
    help = 'Cria os grupos (perfis de acesso) e define as permissões de cada um.'

    def handle(self, *args, **options):
        for nome, regras in PERMISSOES.items():
            grupo, _ = Group.objects.get_or_create(name=nome)
            permissoes = [p for regra in regras for p in resolver_regra(regra)]
            grupo.permissions.set(permissoes)
            self.stdout.write(f'{nome}: {len(permissoes)} permissões')
        self.stdout.write(self.style.SUCCESS('Grupos configurados.'))
