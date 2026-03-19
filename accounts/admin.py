"""
Admin para o app accounts
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, PasswordResetCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Configuração do admin para o modelo User"""
    
    list_display = [
        'telefone', 'nome', 'email', 'perfil', 'distrito',
        'is_active', 'is_verified', 'date_joined'
    ]
    list_filter = ['perfil', 'is_active', 'is_verified', 'distrito', 'date_joined']
    search_fields = ['telefone', 'nome', 'email', 'nome_empresa', 'nif', 'bi_numero']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('telefone', 'password')}),
        (_('Informações Pessoais'), {
            'fields': ('nome', 'email', 'distrito', 'bi_numero')
        }),
        (_('Perfil'), {
            'fields': ('perfil', 'is_verified')
        }),
        (_('Dados de Empresa'), {
            'fields': ('nome_empresa', 'nif', 'setor_empresa'),
            'classes': ('collapse',)
        }),
        (_('Dados de Operador'), {
            'fields': ('associacao_parceira',),
            'classes': ('collapse',)
        }),
        (_('Consentimentos'), {
            'fields': ('consentimento_dados', 'consentimento_contacto', 'data_consentimento')
        }),
        (_('Permissões'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Datas Importantes'), {
            'fields': ('last_login', 'date_joined'),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('telefone', 'nome', 'email', 'perfil', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined', 'data_consentimento']


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    """Configuração do admin para códigos de recuperação"""
    
    list_display = ['user', 'code', 'created_at', 'used', 'is_valid']
    list_filter = ['used', 'created_at']
    search_fields = ['user__telefone', 'user__nome', 'code']
    readonly_fields = ['created_at']
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = _('válido')
