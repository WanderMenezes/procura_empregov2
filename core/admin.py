"""
Admin para o app core
"""

from django.contrib import admin
from .models import District, Skill, AuditLog, Notification, SiteConfig


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome']
    search_fields = ['nome', 'codigo']
    ordering = ['nome']


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'aprovada', 'descricao']
    list_filter = ['tipo', 'aprovada']
    search_fields = ['nome']
    ordering = ['nome']

    @admin.action(description='Aprovar skills selecionadas')
    def aprovar_skills(self, request, queryset):
        queryset.update(aprovada=True)

    @admin.action(description='Despublicar skills selecionadas')
    def despublicar_skills(self, request, queryset):
        queryset.update(aprovada=False)

    actions = ['aprovar_skills', 'despublicar_skills']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['acao', 'user', 'ip_address', 'created_at']
    list_filter = ['acao', 'created_at']
    search_fields = ['acao', 'user__telefone', 'user__nome']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'user', 'tipo', 'lida', 'created_at']
    list_filter = ['tipo', 'lida', 'created_at']
    search_fields = ['titulo', 'mensagem', 'user__nome']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ['chave', 'valor', 'descricao']
    search_fields = ['chave', 'valor']
