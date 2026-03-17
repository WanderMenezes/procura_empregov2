"""
Views para dashboards (Admin e Técnico)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
import csv
import json

from accounts.models import User
from accounts.forms import UserRegistrationForm
from profiles.models import YouthProfile, Education
from companies.models import Company, JobPost, Application, ContactRequest
from core.models import District, Notification


def admin_required(view_func):
    """Decorator para verificar se é admin"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            messages.error(request, _('Acesso restrito a administradores.'))
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_or_operador_required(view_func):
    """Decorator para verificar se admin ou operador distrital"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_admin or request.user.is_operador):
            messages.error(request, _('Acesso restrito.'))
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def tecnico_required(view_func):
    """Decorator para verificar se é técnico ou admin"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_tecnico or request.user.is_admin):
            messages.error(request, _('Acesso restrito.'))
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_dashboard(request):
    """Dashboard do administrador"""
    create_user_form = None
    if request.method == 'POST' and request.POST.get('action') == 'create_user':
        create_user_form = UserRegistrationForm(request.POST, request.FILES, user=request.user)
        if create_user_form.is_valid():
            user = create_user_form.save()
            # Se for jovem, criar perfil e guardar foto opcional
            try:
                if user.is_jovem:
                    photo = request.FILES.get('photo')
                    if not user.has_youth_profile():
                        profile = YouthProfile.objects.create(user=user)
                    else:
                        profile = user.youth_profile
                    if photo:
                        profile.photo = photo
                        profile.save()
            except Exception:
                pass

            messages.success(request, _('Utilizador criado com sucesso.'))
            return redirect('dashboard:admin')
    else:
        create_user_form = UserRegistrationForm(user=request.user)

    # Estatísticas gerais
    stats = {
        'total_jovens': YouthProfile.objects.count(),
        'jovens_completos': YouthProfile.objects.filter(completo=True).count(),
        'jovens_validados': YouthProfile.objects.filter(validado=True).count(),
        'total_empresas': Company.objects.count(),
        'empresas_ativas': Company.objects.filter(ativa=True).count(),
        'total_vagas': JobPost.objects.count(),
        'vagas_ativas': JobPost.objects.filter(estado='ATIVA').count(),
        'total_candidaturas': Application.objects.count(),
        'pedidos_contacto_pendentes': ContactRequest.objects.filter(estado='PENDENTE').count(),
        'total_utilizadores': User.objects.count(),
    }
    
    # Dados por distrito
    jovens_por_distrito = []
    for district in District.objects.all():
        count = YouthProfile.objects.filter(user__distrito=district).count()
        if count > 0:
            jovens_por_distrito.append({
                'nome': district.nome,
                'total': count
            })
    
    # Dados por nível de educação
    educacao_stats = []
    for nivel_codigo, nivel_nome in Education.NIVEL_CHOICES:
        count = Education.objects.filter(nivel=nivel_codigo).count()
        if count > 0:
            educacao_stats.append({
                'nome': nivel_nome,
                'total': count
            })
    
    # Dados por área
    area_stats = []
    area_counts = Education.objects.values('area_formacao').annotate(total=Count('id'))
    for item in area_counts:
        if item['area_formacao']:
            area_stats.append({
                'codigo': item['area_formacao'],
                'nome': dict(Education.NIVEL_CHOICES).get(item['area_formacao'], item['area_formacao']),
                'total': item['total']
            })
    
    # Jovens recentes
    jovens_recentes = YouthProfile.objects.select_related('user').order_by('-created_at')[:10]
    
    # Empresas recentes
    empresas_recentes = Company.objects.select_related('user').order_by('-created_at')[:10]
    
    # Vagas recentes
    vagas_recentes = JobPost.objects.select_related('company').order_by('-data_publicacao')[:10]
    
    # Pedidos de contacto pendentes
    pedidos_pendentes = ContactRequest.objects.select_related(
        'company', 'youth', 'youth__user'
    ).filter(estado='PENDENTE').order_by('-created_at')[:10]
    
    # Perfis pendentes de validação
    perfis_pendentes = YouthProfile.objects.select_related('user').filter(
        completo=True, validado=False
    ).order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'jovens_por_distrito': jovens_por_distrito,
        'educacao_stats': educacao_stats,
        'area_stats': area_stats,
        'jovens_recentes': jovens_recentes,
        'empresas_recentes': empresas_recentes,
        'vagas_recentes': vagas_recentes,
        'pedidos_pendentes': pedidos_pendentes,
        'perfis_pendentes': perfis_pendentes,
        'create_user_form': create_user_form,
    }
    
    return render(request, 'dashboard/admin.html', context)


@tecnico_required
def tecnico_dashboard(request):
    """Dashboard do técnico PNUD (apenas leitura)"""
    
    # Estatísticas (apenas leitura)
    stats = {
        'total_jovens': YouthProfile.objects.count(),
        'jovens_completos': YouthProfile.objects.filter(completo=True).count(),
        'jovens_validados': YouthProfile.objects.filter(validado=True).count(),
        'total_empresas': Company.objects.count(),
        'empresas_ativas': Company.objects.filter(ativa=True).count(),
        'total_vagas': JobPost.objects.count(),
        'vagas_ativas': JobPost.objects.filter(estado='ATIVA').count(),
        'total_candidaturas': Application.objects.count(),
    }
    
    # Dados por distrito
    jovens_por_distrito = []
    for district in District.objects.all():
        count = YouthProfile.objects.filter(user__distrito=district).count()
        if count > 0:
            jovens_por_distrito.append({
                'nome': district.nome,
                'total': count
            })
    
    # Dados por nível de educação
    educacao_stats = []
    for nivel_codigo, nivel_nome in Education.NIVEL_CHOICES:
        count = Education.objects.filter(nivel=nivel_codigo).count()
        if count > 0:
            educacao_stats.append({
                'nome': nivel_nome,
                'total': count
            })
    
    context = {
        'stats': stats,
        'jovens_por_distrito': jovens_por_distrito,
        'educacao_stats': educacao_stats,
    }
    
    return render(request, 'dashboard/tecnico.html', context)


# Gestão de Utilizadores
@admin_required
def user_list(request):
    """Lista de utilizadores"""
    users = User.objects.all().order_by('-date_joined')
    
    # Filtros
    perfil = request.GET.get('perfil')
    if perfil:
        users = users.filter(perfil=perfil)
    
    ativo = request.GET.get('ativo')
    if ativo:
        users = users.filter(is_active=(ativo == 'sim'))
    
    context = {
        'users': users,
        'filtro_perfil': perfil,
        'filtro_ativo': ativo,
    }
    
    return render(request, 'dashboard/user_list.html', context)


@admin_required
def user_toggle_active(request, pk):
    """Ativar/desativar utilizador"""
    user = get_object_or_404(User, pk=pk)
    
    if user == request.user:
        messages.error(request, _('Não podes desativar a tua própria conta.'))
        return redirect('dashboard:user_list')
    
    user.is_active = not user.is_active
    user.save()
    
    status = _('ativado') if user.is_active else _('desativado')
    messages.success(request, _('Utilizador {} com sucesso!').format(status))
    
    return redirect('dashboard:user_list')


# Validação de Perfis
@admin_or_operador_required
def validate_profiles(request):
    """Lista de perfis pendentes de validação"""
    perfis = YouthProfile.objects.filter(
        completo=True, validado=False
    ).select_related('user').order_by('-created_at')
    
    context = {
        'perfis': perfis
    }
    
    return render(request, 'dashboard/validate_profiles.html', context)


@admin_or_operador_required
def validate_profile(request, pk, action):
    """Validar ou rejeitar perfil"""
    profile = get_object_or_404(YouthProfile, pk=pk)
    
    if action == 'aprovar':
        profile.validado = True
        profile.save()
        
        # Notificar jovem
        Notification.objects.create(
            user=profile.user,
            titulo=_('Perfil validado!'),
            mensagem=_('O teu perfil foi validado e está agora visível para empresas.'),
            tipo='SUCESSO'
        )
        
        messages.success(request, _('Perfil validado com sucesso!'))
    
    elif action == 'rejeitar':
        # Marcar como não validado
        profile.validado = False
        profile.visivel = False
        profile.save()
        
        Notification.objects.create(
            user=profile.user,
            titulo=_('Perfil não validado'),
            mensagem=_('O teu perfil não foi validado. Por favor, verifica os dados e submete novamente.'),
            tipo='ALERTA'
        )
        
        messages.warning(request, _('Perfil rejeitado.'))
    
    return redirect('dashboard:validate_profiles')


# Gestão de Pedidos de Contacto
@admin_required
def manage_contact_requests(request):
    """Gerir pedidos de contacto"""
    pedidos = ContactRequest.objects.select_related(
        'company', 'youth', 'youth__user'
    ).order_by('-created_at')
    
    estado = request.GET.get('estado')
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    context = {
        'pedidos': pedidos,
        'filtro_estado': estado,
    }
    
    return render(request, 'dashboard/manage_contact_requests.html', context)


@admin_required
def contact_request_action(request, pk, action):
    """Aprovar ou rejeitar pedido de contacto"""
    contact = get_object_or_404(ContactRequest, pk=pk)
    
    if action == 'aprovar':
        contact.estado = 'APROVADO'
        contact.responded_at = timezone.now()
        contact.save()
        
        # Notificar empresa
        Notification.objects.create(
            user=contact.company.user,
            titulo=_('Pedido de contacto aprovado'),
            mensagem=_('O teu pedido de contacto para {} foi aprovado. Podes agora contactar o jovem através do telefone: {}').format(
                contact.youth.user.nome,
                contact.youth.user.telefone
            ),
            tipo='SUCESSO'
        )
        
        # Notificar jovem
        Notification.objects.create(
            user=contact.youth.user,
            titulo=_('Novo contacto autorizado'),
            mensagem=_('A empresa "{}" foi autorizada a contactar-te.').format(contact.company.nome),
            tipo='INFO'
        )
        
        messages.success(request, _('Pedido aprovado!'))
    
    elif action == 'rejeitar':
        contact.estado = 'REJEITADO'
        contact.responded_at = timezone.now()
        contact.save()
        
        Notification.objects.create(
            user=contact.company.user,
            titulo=_('Pedido de contacto rejeitado'),
            mensagem=_('O teu pedido de contacto para {} foi rejeitado.').format(contact.youth.user.nome),
            tipo='ALERTA'
        )
        
        messages.warning(request, _('Pedido rejeitado.'))
    
    return redirect('dashboard:manage_contact_requests')


# Relatórios
@admin_required
def reports(request):
    """Página de relatórios"""
    
    # Período
    meses = int(request.GET.get('meses', 6))
    data_inicio = timezone.now() - timedelta(days=30*meses)
    
    # Estatísticas do período
    jovens_novos = YouthProfile.objects.filter(created_at__gte=data_inicio).count()
    empresas_novas = Company.objects.filter(created_at__gte=data_inicio).count()
    vagas_novas = JobPost.objects.filter(data_publicacao__gte=data_inicio).count()
    candidaturas_novas = Application.objects.filter(created_at__gte=data_inicio).count()
    
    context = {
        'meses': meses,
        'data_inicio': data_inicio,
        'jovens_novos': jovens_novos,
        'empresas_novas': empresas_novas,
        'vagas_novas': vagas_novas,
        'candidaturas_novas': candidaturas_novas,
    }
    
    return render(request, 'dashboard/reports.html', context)


@admin_required
def export_report_csv(request):
    """Exportar relatório CSV"""
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_base_nacional.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Tipo', 'ID', 'Nome', 'Distrito', 'Data', 'Status'
    ])
    
    # Jovens
    for profile in YouthProfile.objects.all():
        writer.writerow([
            'Jovem',
            profile.id,
            profile.nome_completo,
            profile.distrito.nome if profile.distrito else '',
            profile.created_at.strftime('%d/%m/%Y'),
            'Validado' if profile.validado else 'Pendente'
        ])
    
    # Empresas
    for company in Company.objects.all():
        writer.writerow([
            'Empresa',
            company.id,
            company.nome,
            company.distrito.nome if company.distrito else '',
            company.created_at.strftime('%d/%m/%Y'),
            'Ativa' if company.ativa else 'Inativa'
        ])
    
    return response


# API para gráficos
@admin_required
def api_stats(request):
    """API para dados estatísticos (gráficos)"""
    
    # Jovens por mês (últimos 6 meses)
    hoje = timezone.now()
    jovens_por_mes = []
    
    for i in range(5, -1, -1):
        mes = hoje - timedelta(days=30*i)
        inicio_mes = mes.replace(day=1, hour=0, minute=0, second=0)
        if mes.month < 12:
            fim_mes = mes.replace(month=mes.month+1, day=1) - timedelta(seconds=1)
        else:
            fim_mes = mes.replace(year=mes.year+1, month=1, day=1) - timedelta(seconds=1)
        
        count = YouthProfile.objects.filter(created_at__gte=inicio_mes, created_at__lte=fim_mes).count()
        jovens_por_mes.append({
            'mes': mes.strftime('%b %Y'),
            'total': count
        })
    
    return JsonResponse({
        'jovens_por_mes': jovens_por_mes,
    })
