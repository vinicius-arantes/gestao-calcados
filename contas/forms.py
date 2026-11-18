from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from config.forms import BootstrapFormMixin

from .models import Perfil


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class CadastroForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(label='Nome', max_length=150)
    last_name = forms.CharField(label='Sobrenome', max_length=150)
    email = forms.EmailField(label='E-mail')
    matricula = forms.CharField(label='Matrícula', max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Já existe um usuário com este e-mail.')
        return email


class UsuarioForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class PerfilForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['matricula', 'telefone', 'setor']
