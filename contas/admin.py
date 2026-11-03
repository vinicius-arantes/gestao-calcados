from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User

from .models import Perfil


class PerfilAcessoFilter(admin.SimpleListFilter):
    title = 'perfil de acesso'
    parameter_name = 'perfil'

    def lookups(self, request, model_admin):
        grupos = [(str(g.pk), g.name) for g in Group.objects.all()]
        return [('admin', 'Administrador'), *grupos, ('nenhum', 'Sem perfil')]

    def queryset(self, request, queryset):
        if self.value() == 'admin':
            return queryset.filter(is_superuser=True)
        if self.value() == 'nenhum':
            return queryset.filter(is_superuser=False, groups__isnull=True)
        if self.value():
            return queryset.filter(groups__id=self.value())
        return queryset


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    verbose_name_plural = 'dados do funcionário'


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [PerfilInline]
    list_display = ['username', 'get_full_name', 'email', 'cargo', 'setor', 'is_active', 'last_login']
    list_filter = [PerfilAcessoFilter, 'is_active', 'is_staff', 'perfil__setor']
    list_select_related = ['perfil__setor']

    @admin.display(description='perfil')
    def cargo(self, obj):
        return obj.perfil.cargo

    @admin.display(description='setor')
    def setor(self, obj):
        return obj.perfil.setor or '-'


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'matricula', 'setor', 'telefone', 'cargo']
    list_filter = ['setor', 'usuario__groups']
    search_fields = ['usuario__username', 'usuario__first_name', 'usuario__last_name', 'matricula']
    autocomplete_fields = ['usuario']
    list_select_related = ['usuario', 'setor']
