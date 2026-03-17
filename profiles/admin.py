"""
Admin para o app profiles
"""

from django.contrib import admin
from .models import YouthProfile, Education, Experience, Document, YouthSkill
from django.utils.translation import gettext_lazy as _


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0
    readonly_fields = ['created_at']


class YouthSkillInline(admin.TabularInline):
    model = YouthSkill
    extra = 0


@admin.register(YouthProfile)
class YouthProfileAdmin(admin.ModelAdmin):
    list_display = [
        'nome_completo', 'idade', 'distrito', 'situacao_atual',
        'disponibilidade', 'completo', 'validado', 'visivel', 'created_at'
    ]
    list_filter = [
        'situacao_atual', 'disponibilidade', 'completo',
        'validado', 'visivel', 'sexo', 'created_at'
    ]
    search_fields = ['user__nome', 'user__telefone', 'user__email', 'localidade', 'contacto_alternativo']
    readonly_fields = ['created_at', 'updated_at', 'idade']
    inlines = [EducationInline, ExperienceInline, DocumentInline, YouthSkillInline]
    
    fieldsets = (
        (_('Informações do Utilizador'), {
            'fields': ('user',)
        }),
        (_('Dados Pessoais'), {
            'fields': ('data_nascimento', 'sexo', 'localidade', 'contacto_alternativo')
        }),
        (_('Situação Atual'), {
            'fields': ('situacao_atual', 'disponibilidade')
        }),
        (_('Interesses'), {
            'fields': ('interesse_setorial', 'preferencia_oportunidade', 'sobre')
        }),
        (_('Status'), {
            'fields': ('completo', 'validado', 'visivel')
        }),
        (_('Consentimentos'), {
            'fields': ('consentimento_sms', 'consentimento_whatsapp', 'consentimento_email')
        }),
        (_('Wizard'), {
            'fields': ('wizard_step', 'wizard_data'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['validar_perfis', 'tornar_visiveis', 'tornar_invisiveis', 'exportar_csv']
    
    def validar_perfis(self, request, queryset):
        queryset.update(validado=True)
    validar_perfis.short_description = _('Validar perfis selecionados')
    
    def tornar_visiveis(self, request, queryset):
        queryset.update(visivel=True)
    tornar_visiveis.short_description = _('Tornar visíveis para empresas')
    
    def tornar_invisiveis(self, request, queryset):
        queryset.update(visivel=False)
    tornar_invisiveis.short_description = _('Tornar invisíveis para empresas')
    
    def exportar_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="perfis_jovens.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Nome', 'Telefone', 'Email', 'Distrito', 'Idade', 'Sexo',
            'Situação', 'Disponibilidade', 'Nível Educação', 'Área',
            'Completo', 'Validado', 'Data Registo'
        ])
        
        for profile in queryset:
            educacao = profile.get_education().first()
            writer.writerow([
                profile.nome_completo,
                profile.telefone,
                profile.email or '',
                profile.distrito.nome if profile.distrito else '',
                profile.idade or '',
                profile.get_sexo_display(),
                profile.get_situacao_atual_display(),
                profile.get_disponibilidade_display(),
                educacao.get_nivel_display() if educacao else '',
                educacao.get_area_formacao_display() if educacao else '',
                'Sim' if profile.completo else 'Não',
                'Sim' if profile.validado else 'Não',
                profile.created_at.strftime('%d/%m/%Y')
            ])
        
        return response
    exportar_csv.short_description = _('Exportar para CSV')


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ['profile', 'nivel', 'area_formacao', 'instituicao', 'ano']
    list_filter = ['nivel', 'area_formacao', 'ano']
    search_fields = ['profile__user__nome', 'instituicao']


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ['profile', 'cargo', 'entidade', 'inicio', 'fim', 'atual']
    list_filter = ['atual', 'inicio']
    search_fields = ['profile__user__nome', 'cargo', 'entidade']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['profile', 'tipo', 'nome', 'verificado', 'created_at']
    list_filter = ['tipo', 'verificado', 'created_at']
    search_fields = ['profile__user__nome', 'nome']
    actions = ['verificar_documentos']
    
    def verificar_documentos(self, request, queryset):
        queryset.update(verificado=True)
    verificar_documentos.short_description = _('Marcar como verificados')


@admin.register(YouthSkill)
class YouthSkillAdmin(admin.ModelAdmin):
    list_display = ['profile', 'skill', 'nivel']
    list_filter = ['skill', 'nivel']
    search_fields = ['profile__user__nome', 'skill__nome']
