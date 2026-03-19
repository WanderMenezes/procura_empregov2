"""
Admin para o app companies
"""

from django import forms
from django.contrib import admin
from .models import Company, JobPost, Application, ContactRequest
from django.utils.translation import gettext_lazy as _


class JobPostInline(admin.TabularInline):
    model = JobPost
    extra = 0
    readonly_fields = ['data_publicacao']


class CompanyAdminForm(forms.ModelForm):
    setor = forms.MultipleChoiceField(
        label=_('Setores de atividade'),
        choices=Company.SETOR_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Company
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setor_value = self.initial.get('setor')
        if setor_value is None and getattr(self.instance, 'pk', None):
            setor_value = self.instance.setor

        if isinstance(setor_value, str):
            self.initial['setor'] = [setor_value] if setor_value else []
        elif setor_value is None:
            self.initial['setor'] = []

    def clean_setor(self):
        return list(dict.fromkeys(self.cleaned_data.get('setor') or []))


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm
    list_display = [
        'nome', 'nif', 'setores_display_admin', 'distrito', 'ativa',
        'verificada', 'total_vagas', 'vagas_ativas', 'created_at'
    ]
    list_filter = ['ativa', 'verificada', 'created_at']
    search_fields = ['nome', 'nif', 'user__telefone', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [JobPostInline]
    
    actions = ['verificar_empresas', 'ativar_empresas', 'desativar_empresas']
    
    def verificar_empresas(self, request, queryset):
        queryset.update(verificada=True)
    verificar_empresas.short_description = _('Verificar empresas selecionadas')
    
    def ativar_empresas(self, request, queryset):
        queryset.update(ativa=True)
    ativar_empresas.short_description = _('Ativar empresas')
    
    def desativar_empresas(self, request, queryset):
        queryset.update(ativa=False)
    desativar_empresas.short_description = _('Desativar empresas')

    @admin.display(description=_('setores'))
    def setores_display_admin(self, obj):
        return obj.setores_display or '-'


class ApplicationInline(admin.TabularInline):
    model = Application
    extra = 0
    readonly_fields = ['created_at']


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = [
        'titulo', 'company', 'tipo', 'distrito', 'estado',
        'numero_vagas',
        'total_candidaturas', 'visualizacoes', 'data_publicacao'
    ]
    list_filter = ['tipo', 'estado', 'nivel_educacao', 'data_publicacao']
    search_fields = ['titulo', 'company__nome', 'descricao']
    readonly_fields = ['data_publicacao', 'visualizacoes']
    inlines = [ApplicationInline]
    
    actions = ['ativar_vagas', 'fechar_vagas', 'pausar_vagas', 'exportar_candidaturas']
    
    def ativar_vagas(self, request, queryset):
        queryset.update(estado='ATIVA')
    ativar_vagas.short_description = _('Ativar vagas')
    
    def fechar_vagas(self, request, queryset):
        queryset.update(estado='FECHADA')
    fechar_vagas.short_description = _('Fechar vagas')
    
    def pausar_vagas(self, request, queryset):
        queryset.update(estado='PAUSADA')
    pausar_vagas.short_description = _('Pausar vagas')
    
    def exportar_candidaturas(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="candidaturas.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Vaga', 'Empresa', 'Jovem', 'Telefone', 'Estado', 'Data'])
        
        for vaga in queryset:
            for app in vaga.applications.all():
                writer.writerow([
                    vaga.titulo,
                    vaga.company.nome,
                    app.youth.user.nome,
                    app.youth.user.telefone,
                    app.get_estado_display(),
                    app.created_at.strftime('%d/%m/%Y %H:%M')
                ])
        
        return response
    exportar_candidaturas.short_description = _('Exportar candidaturas')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['youth', 'job', 'estado', 'created_at']
    list_filter = ['estado', 'created_at']
    search_fields = ['youth__user__nome', 'job__titulo']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['aceitar_candidaturas', 'rejeitar_candidaturas']
    
    def aceitar_candidaturas(self, request, queryset):
        queryset.update(estado='ACEITE')
    aceitar_candidaturas.short_description = _('Aceitar candidaturas')
    
    def rejeitar_candidaturas(self, request, queryset):
        queryset.update(estado='REJEITADA')
    rejeitar_candidaturas.short_description = _('Rejeitar candidaturas')


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ['company', 'youth', 'estado', 'created_at']
    list_filter = ['estado', 'created_at']
    search_fields = ['company__nome', 'youth__user__nome', 'motivo']
    readonly_fields = ['created_at', 'responded_at']
    
    actions = ['aprovar_pedidos', 'rejeitar_pedidos']
    
    def aprovar_pedidos(self, request, queryset):
        from django.utils import timezone
        queryset.update(estado='APROVADO', responded_at=timezone.now())
    aprovar_pedidos.short_description = _('Aprovar pedidos')
    
    def rejeitar_pedidos(self, request, queryset):
        from django.utils import timezone
        queryset.update(estado='REJEITADO', responded_at=timezone.now())
    rejeitar_pedidos.short_description = _('Rejeitar pedidos')
