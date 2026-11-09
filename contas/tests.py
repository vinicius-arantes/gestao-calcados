from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from catalogo.models import Categoria, Cor, Modelo
from producao.models import OrdemProducao

from .models import GRUPO_ESTOQUISTA, GRUPO_GERENTE, GRUPO_OPERADOR


class PerfisDeAcessoTests(TestCase):
    def setUp(self):
        call_command('criar_grupos', stdout=StringIO())

    def logar(self, grupo, is_staff=True):
        usuario = User.objects.create_user(grupo, password='x', is_staff=is_staff)
        usuario.groups.add(Group.objects.get(name=grupo))
        self.client.force_login(usuario)
        return usuario

    def test_comando_e_idempotente(self):
        total = Group.objects.get(name=GRUPO_GERENTE).permissions.count()
        call_command('criar_grupos', stdout=StringIO())
        self.assertEqual(Group.objects.count(), 3)
        self.assertEqual(Group.objects.get(name=GRUPO_GERENTE).permissions.count(), total)

    def test_cargo_do_perfil(self):
        usuario = self.logar(GRUPO_OPERADOR)
        self.assertEqual(usuario.perfil.cargo, GRUPO_OPERADOR)

    def test_gerente_cria_ordem_mas_nao_cadastra_material(self):
        self.logar(GRUPO_GERENTE)
        self.assertEqual(self.client.get('/admin/producao/ordemproducao/add/').status_code, 200)
        self.assertEqual(self.client.get('/admin/estoque/material/').status_code, 200)
        self.assertEqual(self.client.get('/admin/estoque/material/add/').status_code, 403)

    def test_gerente_ve_acoes_de_iniciar_e_concluir(self):
        self.logar(GRUPO_GERENTE)
        OrdemProducao.objects.create(
            modelo=Modelo.objects.create(
                referencia='TEN-01', nome='Tênis', genero='U', preco_venda=100,
                categoria=Categoria.objects.create(nome='Tênis'),
            ),
            cor=Cor.objects.create(nome='Branco'),
            data_prevista=timezone.localdate() + timedelta(days=5),
        )
        html = self.client.get('/admin/producao/ordemproducao/').content.decode()
        self.assertIn('value="iniciar"', html)
        self.assertIn('value="concluir"', html)

    def test_estoquista_cadastra_material_mas_nao_cria_ordem(self):
        self.logar(GRUPO_ESTOQUISTA)
        self.assertEqual(self.client.get('/admin/estoque/material/add/').status_code, 200)
        self.assertEqual(self.client.get('/admin/producao/ordemproducao/').status_code, 200)
        self.assertEqual(self.client.get('/admin/producao/ordemproducao/add/').status_code, 403)

    def test_operador_nao_entra_no_admin(self):
        self.logar(GRUPO_OPERADOR, is_staff=False)
        resposta = self.client.get('/admin/')
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/admin/login/', resposta['Location'])


class AutenticacaoTests(TestCase):
    SENHA = 'Sapato#2026x'

    def test_area_do_usuario_exige_login(self):
        resposta = self.client.get('/')
        self.assertRedirects(resposta, '/contas/entrar/?next=/')

    def test_login_e_logout(self):
        User.objects.create_user('ana', password=self.SENHA)
        resposta = self.client.post('/contas/entrar/', {'username': 'ana', 'password': self.SENHA})
        self.assertRedirects(resposta, '/')
        resposta = self.client.post('/contas/sair/')
        self.assertRedirects(resposta, '/contas/entrar/')
        self.assertRedirects(self.client.get('/'), '/contas/entrar/?next=/')

    def test_login_com_senha_errada(self):
        User.objects.create_user('ana', password=self.SENHA)
        resposta = self.client.post('/contas/entrar/', {'username': 'ana', 'password': 'errada'})
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cadastro_cria_operador_e_entra_no_sistema(self):
        resposta = self.client.post('/contas/cadastro/', {
            'username': 'novo', 'first_name': 'Novo', 'last_name': 'Usuário',
            'email': 'novo@exemplo.com', 'matricula': 'M-1',
            'password1': self.SENHA, 'password2': self.SENHA,
        })
        self.assertRedirects(resposta, '/')
        usuario = User.objects.get(username='novo')
        self.assertEqual(usuario.perfil.cargo, GRUPO_OPERADOR)
        self.assertEqual(usuario.perfil.matricula, 'M-1')
        self.assertFalse(usuario.is_staff)

    def test_cadastro_recusa_email_repetido(self):
        User.objects.create_user('ana', email='ana@exemplo.com')
        resposta = self.client.post('/contas/cadastro/', {
            'username': 'outra', 'first_name': 'A', 'last_name': 'B', 'email': 'ANA@exemplo.com',
            'password1': self.SENHA, 'password2': self.SENHA,
        })
        self.assertContains(resposta, 'Já existe um usuário com este e-mail')
        self.assertFalse(User.objects.filter(username='outra').exists())

    def test_meu_perfil_salva_dados(self):
        self.client.force_login(User.objects.create_user('ana'))
        self.client.post('/contas/perfil/', {
            'first_name': 'Ana', 'last_name': 'Souza', 'email': 'ana@exemplo.com',
            'matricula': 'M-9', 'telefone': '(35) 90000-0000', 'setor': '',
        })
        usuario = User.objects.get(username='ana')
        self.assertEqual(usuario.last_name, 'Souza')
        self.assertEqual(usuario.perfil.telefone, '(35) 90000-0000')
