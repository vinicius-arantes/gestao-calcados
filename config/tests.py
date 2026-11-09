from django import forms
from django.contrib.auth.models import User
from django.test import TestCase

from .forms import BootstrapFormMixin


class ExemploForm(BootstrapFormMixin, forms.Form):
    nome = forms.CharField()
    tipo = forms.ChoiceField(choices=[('a', 'A')])
    ativo = forms.BooleanField(required=False)


class LayoutTests(TestCase):
    def test_pagina_inicial_usa_bootstrap_e_tema(self):
        self.client.force_login(User.objects.create_user('usuario'))
        html = self.client.get('/').content.decode()
        self.assertIn('bootstrap@5.3.3', html)
        self.assertIn('data-bs-theme', html)
        self.assertIn('id="alternar-tema"', html)

    def test_link_do_admin_so_para_equipe(self):
        self.client.force_login(User.objects.create_user('usuario'))
        self.assertNotIn('Administração', self.client.get('/').content.decode())
        self.client.force_login(User.objects.create_user('equipe', is_staff=True))
        self.assertIn('Administração', self.client.get('/').content.decode())

    def test_pagina_403_personalizada(self):
        self.client.force_login(User.objects.create_user('sem_permissao', is_staff=True))
        resposta = self.client.get('/admin/estoque/material/add/')
        self.assertEqual(resposta.status_code, 403)
        self.assertIn('Acesso negado', resposta.content.decode())

    def test_formulario_recebe_classes_do_bootstrap(self):
        form = ExemploForm()
        self.assertEqual(form.fields['nome'].widget.attrs['class'], 'form-control')
        self.assertEqual(form.fields['tipo'].widget.attrs['class'], 'form-select')
        self.assertEqual(form.fields['ativo'].widget.attrs['class'], 'form-check-input')
