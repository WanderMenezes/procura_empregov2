"""
Views para dashboards (Admin e Técnico)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta, time
from io import BytesIO
import csv
import json
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF

from accounts.models import User
from accounts.forms import UserRegistrationForm, AdminUserUpdateForm
from profiles.models import YouthProfile, Education
from companies.models import Company, JobPost, Application, ContactRequest
from core.models import District, Notification


def _get_date_range(request):
    """Parse date range (data_inicio/data_fim) with sane defaults."""
    today = timezone.localdate()
    default_start = today - timedelta(days=30 * 6)

    start_str = request.GET.get('data_inicio')
    end_str = request.GET.get('data_fim')

    start_date = default_start
    end_date = today

    if start_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except Exception:
            start_date = default_start
    if end_str:
        try:
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        except Exception:
            end_date = today

    invalid_range = start_date > end_date

    tz = timezone.get_current_timezone()
    if invalid_range:
        start_dt = None
        end_dt = None
    else:
        start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
        end_dt = timezone.make_aware(datetime.combine(end_date, time.max), tz)

    return start_date, end_date, start_dt, end_dt, invalid_range


def _add_percent(items):
    """Normalize totals into percentages for lightweight dashboard bars."""
    max_total = max((item['total'] for item in items), default=0)
    normalized = []
    for item in items:
        current = dict(item)
        current['percent'] = int((current['total'] / max_total) * 100) if max_total else 0
        normalized.append(current)
    return normalized


def _with_admin_context(request, context=None):
    """Attach shared navigation stats to admin dashboard pages."""
    nav_context = {
        'admin_nav': {
            'pending_profiles': YouthProfile.objects.filter(completo=True, validado=False).count(),
            'pending_contacts': 0,
            'total_users': 0,
            'active_jobs': 0,
        }
    }

    if getattr(request.user, 'is_admin', False):
        nav_context['admin_nav'].update({
            'pending_contacts': ContactRequest.objects.filter(estado='PENDENTE').count(),
            'total_users': User.objects.count(),
            'active_jobs': JobPost.objects.filter(estado='ATIVA').count(),
        })

    if context:
        nav_context.update(context)
    return nav_context


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
    seven_days_ago = timezone.now() - timedelta(days=7)
    thirty_days_ago = timezone.now() - timedelta(days=30)
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
    stats['validacoes_pendentes'] = max(0, stats['jovens_completos'] - stats['jovens_validados'])
    stats['jovens_nao_completos'] = max(0, stats['total_jovens'] - stats['jovens_completos'])
    stats['taxa_validacao'] = int((stats['jovens_validados'] / stats['jovens_completos']) * 100) if stats['jovens_completos'] else 0
    stats['taxa_empresas_ativas'] = int((stats['empresas_ativas'] / stats['total_empresas']) * 100) if stats['total_empresas'] else 0
    stats['taxa_vagas_ativas'] = int((stats['vagas_ativas'] / stats['total_vagas']) * 100) if stats['total_vagas'] else 0
    stats['novos_utilizadores_7d'] = User.objects.filter(date_joined__gte=seven_days_ago).count()
    stats['novas_vagas_30d'] = JobPost.objects.filter(data_publicacao__gte=thirty_days_ago).count()

    # Dados por distrito
    jovens_por_distrito = []
    for district in District.objects.all():
        count = YouthProfile.objects.filter(user__distrito=district).count()
        if count > 0:
            jovens_por_distrito.append({
                'nome': district.nome,
                'total': count
            })
    jovens_por_distrito = _add_percent(jovens_por_distrito)
    
    # Dados por nível de educação
    educacao_stats = []
    for nivel_codigo, nivel_nome in Education.NIVEL_CHOICES:
        count = Education.objects.filter(nivel=nivel_codigo).count()
        if count > 0:
            educacao_stats.append({
                'nome': nivel_nome,
                'total': count
            })
    educacao_stats = _add_percent(educacao_stats)
    
    # Dados por área
    area_stats = []
    area_labels = dict(getattr(settings, 'AREAS_FORMACAO', []))
    area_counts = Education.objects.values('area_formacao').annotate(total=Count('id'))
    for item in area_counts:
        if item['area_formacao']:
            area_stats.append({
                'codigo': item['area_formacao'],
                'nome': area_labels.get(item['area_formacao'], item['area_formacao']),
                'total': item['total']
            })
    area_stats = _add_percent(area_stats)
    
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
    
    context = _with_admin_context(request, {
        'stats': stats,
        'jovens_por_distrito': jovens_por_distrito,
        'educacao_stats': educacao_stats,
        'area_stats': area_stats,
        'jovens_recentes': jovens_recentes,
        'empresas_recentes': empresas_recentes,
        'vagas_recentes': vagas_recentes,
        'pedidos_pendentes': pedidos_pendentes,
        'perfis_pendentes': perfis_pendentes,
    })
    
    return render(request, 'dashboard/admin.html', context)


@tecnico_required
def tecnico_dashboard(request):
    """Dashboard técnico com indicadores de leitura para monitorização."""
    seven_days_ago = timezone.now() - timedelta(days=7)
    thirty_days_ago = timezone.now() - timedelta(days=30)

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
    stats['validacoes_pendentes'] = YouthProfile.objects.filter(completo=True, validado=False).count()
    stats['jovens_nao_completos'] = max(stats['total_jovens'] - stats['jovens_completos'], 0)
    stats['taxa_validacao'] = int((stats['jovens_validados'] / stats['jovens_completos']) * 100) if stats['jovens_completos'] else 0
    stats['taxa_empresas_ativas'] = int((stats['empresas_ativas'] / stats['total_empresas']) * 100) if stats['total_empresas'] else 0
    stats['taxa_vagas_ativas'] = int((stats['vagas_ativas'] / stats['total_vagas']) * 100) if stats['total_vagas'] else 0
    stats['novos_utilizadores_7d'] = User.objects.filter(date_joined__gte=seven_days_ago).count()
    stats['novas_vagas_30d'] = JobPost.objects.filter(data_publicacao__gte=thirty_days_ago).count()
    stats['media_candidaturas_por_vaga'] = round(
        stats['total_candidaturas'] / stats['total_vagas'], 1
    ) if stats['total_vagas'] else 0

    jovens_por_distrito = []
    for district in District.objects.all():
        count = YouthProfile.objects.filter(user__distrito=district).count()
        if count > 0:
            jovens_por_distrito.append({
                'nome': district.nome,
                'total': count,
            })
    jovens_por_distrito = _add_percent(
        sorted(jovens_por_distrito, key=lambda item: item['total'], reverse=True)
    )

    educacao_stats = []
    for nivel_codigo, nivel_nome in Education.NIVEL_CHOICES:
        count = Education.objects.filter(nivel=nivel_codigo).count()
        if count > 0:
            educacao_stats.append({
                'nome': nivel_nome,
                'total': count,
            })
    educacao_stats = _add_percent(
        sorted(educacao_stats, key=lambda item: item['total'], reverse=True)
    )

    area_labels = dict(getattr(settings, 'AREAS_FORMACAO', []))
    area_counts = (
        Education.objects
        .exclude(area_formacao='')
        .values('area_formacao')
        .annotate(total=Count('id'))
        .order_by('-total', 'area_formacao')
    )
    area_stats = _add_percent([
        {
            'codigo': item['area_formacao'],
            'nome': area_labels.get(item['area_formacao'], item['area_formacao']),
            'total': item['total'],
        }
        for item in area_counts
    ])

    jovens_recentes = YouthProfile.objects.select_related('user', 'user__distrito').order_by('-created_at')[:6]
    empresas_recentes = Company.objects.select_related('user').order_by('-created_at')[:6]
    vagas_recentes = JobPost.objects.select_related('company').order_by('-data_publicacao')[:6]

    context = {
        'stats': stats,
        'jovens_por_distrito': jovens_por_distrito,
        'educacao_stats': educacao_stats,
        'area_stats': area_stats,
        'jovens_recentes': jovens_recentes,
        'empresas_recentes': empresas_recentes,
        'vagas_recentes': vagas_recentes,
        'top_district': jovens_por_distrito[0] if jovens_por_distrito else None,
        'top_level': educacao_stats[0] if educacao_stats else None,
        'top_area': area_stats[0] if area_stats else None,
        'distritos_ativos': len(jovens_por_distrito),
        'areas_ativas': len(area_stats),
    }

    return render(request, 'dashboard/tecnico.html', context)


# Gestão de Utilizadores
@admin_required
def user_list(request):
    """Lista de utilizadores"""
    create_user_form = None
    if request.method == 'POST' and request.POST.get('action') == 'create_user':
        create_user_form = UserRegistrationForm(request.POST, request.FILES, user=request.user)
        if create_user_form.is_valid():
            user = create_user_form.save()
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
                elif user.is_empresa:
                    if not user.has_company_profile():
                        Company.objects.create(
                            user=user,
                            nome=user.nome,
                            setor=[],
                            telefone=user.telefone or '',
                            email=user.email or ''
                        )
            except Exception:
                pass

            messages.success(request, _('Utilizador criado com sucesso.'))
            return redirect('dashboard:user_list')
    else:
        create_user_form = UserRegistrationForm(user=request.user)

    users = User.objects.select_related('distrito').all().order_by('-date_joined')

    query = (request.GET.get('q') or '').strip()
    if query:
        users = users.filter(
            Q(nome__icontains=query) |
            Q(nome_empresa__icontains=query) |
            Q(telefone__icontains=query) |
            Q(email__icontains=query) |
            Q(nif__icontains=query) |
            Q(bi_numero__icontains=query)
        )

    # Filtros
    perfil = request.GET.get('perfil')
    if perfil:
        users = users.filter(perfil=perfil)
    
    ativo = request.GET.get('ativo')
    if ativo:
        users = users.filter(is_active=(ativo == 'sim'))

    summary = {
        'total': User.objects.count(),
        'ativos': User.objects.filter(is_active=True).count(),
        'empresas': User.objects.filter(perfil='EMP').count(),
        'equipa': User.objects.filter(perfil__in=['ADM', 'OP', 'TEC']).count(),
        'novos_7d': User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=7)).count(),
        'filtrados': users.count(),
    }

    context = _with_admin_context(request, {
        'users': users,
        'filtro_q': query,
        'filtro_perfil': perfil,
        'filtro_ativo': ativo,
        'create_user_form': create_user_form,
        'user_summary': summary,
    })
    
    return render(request, 'dashboard/user_list.html', context)


@admin_required
def user_edit(request, pk):
    """Editar dados principais de um utilizador pelo painel admin."""
    target_user = get_object_or_404(User.objects.select_related('distrito'), pk=pk)
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('dashboard:user_list')

    if request.method == 'POST':
        edit_user_form = AdminUserUpdateForm(request.POST, instance=target_user)
        if edit_user_form.is_valid():
            edit_user_form.save()
            messages.success(request, _('Utilizador atualizado com sucesso.'))
            return redirect(next_url)
    else:
        edit_user_form = AdminUserUpdateForm(instance=target_user)

    context = _with_admin_context(request, {
        'edit_user_form': edit_user_form,
        'edit_target': target_user,
        'next_url': next_url,
    })

    return render(request, 'dashboard/user_edit.html', context)


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
    
    next_url = request.GET.get('next')
    return redirect(next_url or 'dashboard:user_list')


# Validação de Perfis
@admin_or_operador_required
def validate_profiles(request):
    """Lista de perfis pendentes de validação"""
    pending_profiles = YouthProfile.objects.filter(
        completo=True, validado=False
    ).select_related('user', 'user__distrito').order_by('-created_at')

    query = (request.GET.get('q') or '').strip()
    distrito_id = (request.GET.get('distrito') or '').strip()

    perfis = pending_profiles
    if query:
        perfis = perfis.filter(
            Q(user__nome__icontains=query) |
            Q(user__telefone__icontains=query) |
            Q(user__email__icontains=query) |
            Q(user__bi_numero__icontains=query)
        )
    if distrito_id:
        perfis = perfis.filter(user__distrito_id=distrito_id)

    validation_summary = {
        'total_pending': pending_profiles.count(),
        'pending_today': pending_profiles.filter(created_at__date=timezone.localdate()).count(),
        'districts': pending_profiles.exclude(user__distrito__isnull=True).values('user__distrito').distinct().count(),
        'filtered_total': perfis.count(),
    }

    context = _with_admin_context(request, {
        'perfis': perfis,
        'districts': District.objects.all().order_by('nome'),
        'filtro_q': query,
        'filtro_distrito': distrito_id,
        'validation_summary': validation_summary,
    })

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
    
    next_url = request.GET.get('next')
    return redirect(next_url or 'dashboard:validate_profiles')


# Gestão de Pedidos de Contacto
@admin_required
def manage_contact_requests(request):
    """Gerir pedidos de contacto"""
    all_requests = ContactRequest.objects.select_related(
        'company', 'company__user', 'youth', 'youth__user'
    ).order_by('-created_at')

    query = (request.GET.get('q') or '').strip()
    estado = request.GET.get('estado')
    pedidos = all_requests
    if query:
        pedidos = pedidos.filter(
            Q(company__nome__icontains=query) |
            Q(company__user__telefone__icontains=query) |
            Q(youth__user__nome__icontains=query) |
            Q(youth__user__telefone__icontains=query)
        )
    if estado:
        pedidos = pedidos.filter(estado=estado)

    summary = {
        'pendentes': all_requests.filter(estado='PENDENTE').count(),
        'aprovados': all_requests.filter(estado='APROVADO').count(),
        'desativados': all_requests.filter(estado='DESATIVADO').count(),
        'rejeitados': all_requests.filter(estado='REJEITADO').count(),
        'filtrados': pedidos.count(),
    }

    context = _with_admin_context(request, {
        'pedidos': pedidos,
        'filtro_q': query,
        'filtro_estado': estado,
        'contact_summary': summary,
    })
    
    return render(request, 'dashboard/manage_contact_requests.html', context)


@admin_required
def contact_request_action(request, pk, action):
    """Aprovar, rejeitar ou desativar pedido de contacto"""
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

    elif action == 'desativar':
        if contact.estado != 'APROVADO':
            messages.warning(request, _('Apenas pedidos aprovados podem ser desativados.'))
        else:
            contact.estado = 'DESATIVADO'
            contact.responded_at = timezone.now()
            if not contact.resposta_admin:
                contact.resposta_admin = _('O acesso direto ao contacto foi desativado pelo administrador.')
            contact.save()

            Notification.objects.create(
                user=contact.company.user,
                titulo=_('Pedido de contacto desativado'),
                mensagem=_('O acesso ao contacto de {} foi desativado pelo administrador.').format(
                    contact.youth.user.nome
                ),
                tipo='ALERTA'
            )

            Notification.objects.create(
                user=contact.youth.user,
                titulo=_('Contacto desativado'),
                mensagem=_('O acesso direto da empresa "{}" ao teu contacto foi desativado pelo administrador.').format(
                    contact.company.nome
                ),
                tipo='INFO'
            )

            messages.warning(request, _('Pedido desativado.'))
    
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

    else:
        messages.error(request, _('Acao invalida para o pedido de contacto.'))
    
    next_url = request.GET.get('next')
    return redirect(next_url or 'dashboard:manage_contact_requests')


# Relatórios
@admin_required
def reports(request):
    """Página de relatórios"""

    start_date, end_date, start_dt, end_dt, invalid_range = _get_date_range(request)

    if invalid_range:
        messages.error(request, _('A data final não pode ser menor que a data inicial.'))
        jovens_novos = empresas_novas = vagas_novas = candidaturas_novas = 0
    else:
        # Estatísticas do período
        jovens_novos = YouthProfile.objects.filter(created_at__range=(start_dt, end_dt)).count()
        empresas_novas = Company.objects.filter(created_at__range=(start_dt, end_dt)).count()
        vagas_novas = JobPost.objects.filter(data_publicacao__range=(start_dt, end_dt)).count()
        candidaturas_novas = Application.objects.filter(created_at__range=(start_dt, end_dt)).count()
    period_days = ((end_date - start_date).days + 1) if not invalid_range else 0
    total_movimentos = jovens_novos + empresas_novas + vagas_novas + candidaturas_novas
    media_diaria = round(total_movimentos / period_days, 1) if period_days else 0
    report_mix = _add_percent([
        {'nome': 'Jovens', 'total': jovens_novos, 'icon': 'bi-person'},
        {'nome': 'Empresas', 'total': empresas_novas, 'icon': 'bi-building'},
        {'nome': 'Vagas', 'total': vagas_novas, 'icon': 'bi-briefcase'},
        {'nome': 'Candidaturas', 'total': candidaturas_novas, 'icon': 'bi-send'},
    ])

    context = _with_admin_context(request, {
        'data_inicio': start_date,
        'data_fim': end_date,
        'data_inicio_value': start_date.strftime('%Y-%m-%d'),
        'data_fim_value': end_date.strftime('%Y-%m-%d'),
        'jovens_novos': jovens_novos,
        'empresas_novas': empresas_novas,
        'vagas_novas': vagas_novas,
        'candidaturas_novas': candidaturas_novas,
        'period_days': period_days,
        'total_movimentos': total_movimentos,
        'media_diaria': media_diaria,
        'report_mix': report_mix,
    })
    
    return render(request, 'dashboard/reports.html', context)


@admin_required
def export_report_csv(request):
    """Exportar relatório CSV"""
    start_date, end_date, start_dt, end_dt, invalid_range = _get_date_range(request)
    if invalid_range:
        return HttpResponse(
            'Data final não pode ser menor que a data inicial.',
            status=400,
            content_type='text/plain; charset=utf-8'
        )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_base_nacional.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Tipo', 'ID', 'Nome', 'Distrito', 'Data', 'Status'
    ])
    
    # Jovens
    for profile in YouthProfile.objects.filter(created_at__range=(start_dt, end_dt)):
        writer.writerow([
            'Jovem',
            profile.id,
            profile.nome_completo,
            profile.distrito.nome if profile.distrito else '',
            profile.created_at.strftime('%d/%m/%Y'),
            'Validado' if profile.validado else 'Pendente'
        ])
    
    # Empresas
    for company in Company.objects.filter(created_at__range=(start_dt, end_dt)):
        writer.writerow([
            'Empresa',
            company.id,
            company.nome,
            company.distrito.nome if company.distrito else '',
            company.created_at.strftime('%d/%m/%Y'),
            'Ativa' if company.ativa else 'Inativa'
        ])
    
    return response


@admin_required
def export_report_pdf(request):
    """Exportar relatório em PDF (resumo)"""
    start_date, end_date, start_dt, end_dt, invalid_range = _get_date_range(request)
    if invalid_range:
        return HttpResponse(
            'Data final não pode ser menor que a data inicial.',
            status=400,
            content_type='text/plain; charset=utf-8'
        )

    # Totais gerais
    total_jovens = YouthProfile.objects.filter(created_at__range=(start_dt, end_dt)).count()
    total_empresas = Company.objects.filter(created_at__range=(start_dt, end_dt)).count()
    total_vagas = JobPost.objects.filter(data_publicacao__range=(start_dt, end_dt)).count()
    total_candidaturas = Application.objects.filter(created_at__range=(start_dt, end_dt)).count()
    pedidos_contacto = ContactRequest.objects.filter(estado='PENDENTE', created_at__range=(start_dt, end_dt)).count()

    jovens_novos = total_jovens
    empresas_novas = total_empresas
    vagas_novas = total_vagas
    candidaturas_novas = total_candidaturas

    # Dados por distrito, nível e área
    district_counts = (
        YouthProfile.objects
        .filter(created_at__range=(start_dt, end_dt))
        .values('user__distrito__nome')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    district_list = []
    for item in district_counts:
        nome = item.get('user__distrito__nome')
        if nome:
            district_list.append((nome, int(item['total'])))

    level_counts = Education.objects.filter(profile__created_at__range=(start_dt, end_dt)).values('nivel').annotate(total=Count('id')).order_by('-total')
    level_labels = dict(Education.NIVEL_CHOICES)
    level_list = []
    for item in level_counts:
        if item['nivel']:
            level_list.append((level_labels.get(item['nivel'], item['nivel']), int(item['total'])))

    area_counts = Education.objects.filter(profile__created_at__range=(start_dt, end_dt)).values('area_formacao').annotate(total=Count('id')).order_by('-total')
    area_labels = dict(getattr(settings, 'AREAS_FORMACAO', []))
    area_list = []
    for item in area_counts:
        if item['area_formacao']:
            area_list.append((area_labels.get(item['area_formacao'], item['area_formacao']), int(item['total'])))

    def build_chart_data(items, max_items=6):
        labels = []
        values = []
        for nome, total in items[:max_items]:
            labels.append(str(nome))
            values.append(total)
        if len(items) > max_items:
            outros = sum(total for _, total in items[max_items:])
            labels.append("Outros")
            values.append(outros)
        return labels, values

    def draw_header(title, subtitle):
        header_height = 70
        pdf.setFillColor(colors.HexColor("#0b3b6f"))
        pdf.rect(0, height - header_height, width, header_height, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(margin, height - 28, title)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(margin, height - 46, subtitle)

        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'cnj_logo.jpg')
        if os.path.exists(logo_path):
            try:
                pdf.drawImage(logo_path, width - margin - 140, height - 54, width=140, height=32,
                              preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        pdf.setFillColor(colors.HexColor("#1f2d3d"))
        return height - header_height - 24

    def draw_table(data, col_widths):
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f6fb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2d3d")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#dbe3ef")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ]))
        return table

    def draw_chart(labels, values, x, y, width_px=220, height_px=130):
        if not values or max(values) == 0:
            pdf.setFont("Helvetica", 10)
            pdf.drawString(x, y + height_px - 12, "Sem dados.")
            return
        drawing = Drawing(width_px, height_px)
        chart = VerticalBarChart()
        chart.x = 0
        chart.y = 16
        chart.height = height_px - 24
        chart.width = width_px
        chart.data = [values]
        chart.strokeColor = colors.HexColor("#0b5ed7")
        chart.fillColor = colors.HexColor("#1a73e8")
        max_val = max(values)
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = max(5, int(max_val * 1.2))
        chart.valueAxis.valueStep = max(1, int(max_val / 4) or 1)
        chart.categoryAxis.categoryNames = labels
        chart.categoryAxis.labels.boxAnchor = 'ne'
        chart.categoryAxis.labels.angle = 30
        chart.categoryAxis.labels.fontSize = 6
        chart.categoryAxis.labels.dy = -2
        chart.categoryAxis.labels.dx = -2
        drawing.add(chart)
        renderPDF.draw(drawing, pdf, x, y)

    def draw_section(title, items, y):
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(colors.HexColor("#1f2d3d"))
        pdf.drawString(margin, y, title)
        y -= 12

        table_rows = [[nome, str(total)] for nome, total in items[:10]]
        table_height = 0
        left_x = margin
        right_x = margin + 270

        if table_rows:
            table = draw_table([["Categoria", "Total"]] + table_rows, [200, 60])
            w, h = table.wrap(0, 0)
            table_height = h
            table.drawOn(pdf, left_x, y - h)
        else:
            pdf.setFont("Helvetica", 10)
            pdf.drawString(left_x, y - 12, "Sem dados.")
            table_height = 16

        labels, values = build_chart_data(items, max_items=6)
        chart_height = 130
        draw_chart(labels, values, right_x, y - chart_height + 6, 220, chart_height)

        return y - max(table_height, chart_height) - 24

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 56

    y = draw_header(
        "Relatório - Base Nacional de Jovens",
        f"Período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
    )
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#1f2d3d"))
    pdf.drawString(margin, y + 8, f"Gerado em: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 12

    # Tabela de totais
    totals_data = [
        ["Indicador", "Total"],
        ["Jovens registados", f"{total_jovens}"],
        ["Empresas", f"{total_empresas}"],
        ["Vagas", f"{total_vagas}"],
        ["Candidaturas", f"{total_candidaturas}"],
        ["Pedidos contacto pendentes", f"{pedidos_contacto}"],
    ]
    totals_table = draw_table(totals_data, [300, 120])
    w, h = totals_table.wrap(0, 0)
    totals_table.drawOn(pdf, margin, y - h)
    y -= h + 24

    # Tabela do período
    period_data = [
        ["Indicador", f"Últimos {meses} meses"],
        ["Novos jovens", f"{jovens_novos}"],
        ["Novas empresas", f"{empresas_novas}"],
        ["Novas vagas", f"{vagas_novas}"],
        ["Novas candidaturas", f"{candidaturas_novas}"],
    ]
    period_table = draw_table(period_data, [300, 120])
    w, h = period_table.wrap(0, 0)
    period_table.drawOn(pdf, margin, y - h)

    # Nova página com gráficos e tabelas detalhadas
    pdf.showPage()
    y = draw_header("Relatório - Distribuições", "Resumo por distrito, nível e área")

    y = draw_section("Jovens por Distrito", district_list, y)
    if y < 200:
        pdf.showPage()
        y = draw_header("Relatório - Distribuições", "Resumo por distrito, nível e área")
    y = draw_section("Por Nível de Educação", level_list, y)
    if y < 200:
        pdf.showPage()
        y = draw_header("Relatório - Distribuições", "Resumo por distrito, nível e área")
    y = draw_section("Por Área de Formação", area_list, y)

    pdf.save()

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_base_nacional.pdf"'
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
