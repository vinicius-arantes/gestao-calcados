from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

# Nomes dos grupos que representam os perfis de acesso do sistema
GRUPO_GERENTE = 'Gerente de Produção'
GRUPO_ESTOQUISTA = 'Estoquista'
GRUPO_OPERADOR = 'Operador'


class Perfil(models.Model):
    """Dados complementares do usuário. As permissões vêm dos grupos (perfis de acesso)."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name='usuário', on_delete=models.CASCADE,
        related_name='perfil',
    )
    setor = models.ForeignKey(
        'producao.Setor', verbose_name='setor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='funcionarios',
    )
    matricula = models.CharField('matrícula', max_length=20, blank=True)
    telefone = models.CharField('telefone', max_length=20, blank=True)

    class Meta:
        verbose_name = 'perfil'
        verbose_name_plural = 'perfis'

    def __str__(self):
        return f'Perfil de {self.usuario.get_full_name() or self.usuario.username}'

    @property
    def cargo(self):
        if self.usuario.is_superuser:
            return 'Administrador'
        grupo = self.usuario.groups.first()
        return grupo.name if grupo else 'Sem perfil'


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_perfil(sender, instance, created, **kwargs):
    """Todo usuário novo ganha um Perfil vazio automaticamente."""
    if created:
        Perfil.objects.get_or_create(usuario=instance)
