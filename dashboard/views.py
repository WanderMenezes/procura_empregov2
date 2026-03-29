"""
Views para dashboards (Admin e Técnico)
"""

from collections import Counter
from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
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
from dashboard.forms import OfflineRegistrationExportForm, OfflineRegistrationImportForm
from profiles.models import YouthProfile, Education
from profiles.progress import build_profile_progress_snapshot
from companies.models import Company, JobPost, Application, ContactRequest
from core.models import AuditLog, District, Notification
from core.notifications import notify_admins


def _get_date_range(request):
    'Parse daté range (data_inicio/data_fim) with sane defaults.'
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


def _employment_placements_queryset():
    """Accepted job applications that represent employment placements."""
    return Application.objects.select_related(
        'job',
        'job__company',
        'job__company__user',
        'youth',
        'youth__user',
        'youth__user__distrito',
    ).filter(
        estado='ACEITE',
        job__tipo='EMP',
    )


def _employment_placements_summary(queryset):
    latest_item = queryset.order_by('-updated_at', '-id').first()
    return {
        'placements': queryset.count(),
        'youths': queryset.order_by().values('youth_id').distinct().count(),
        'companies': queryset.order_by().values('job__company_id').distinct().count(),
        'jobs': queryset.order_by().values('job_id').distinct().count(),
        'latest_update': latest_item.updated_at if latest_item else None,
    }


def _profile_progress_queryset():
    return YouthProfile.objects.select_related(
        'user',
        'user__distrito',
    ).prefetch_related(
        'education',
        'documents',
        'youth_skills',
    )


def _decorate_profile_progress(profile):
    snapshot = build_profile_progress_snapshot(profile)
    next_step = snapshot['next_step'] or {
        'step': 'final',
        'title': 'Submissao final',
        'short_title': 'Submissao final',
        'filled': snapshot['total_steps'],
        'total': snapshot['total_steps'],
        'missing': 0,
    }

    profile.progress_snapshot = snapshot
    profile.progress_percent = snapshot['progress']
    profile.step_stats = snapshot['step_stats']
    profile.completed_steps = snapshot['completed_steps']
    profile.total_steps = snapshot['total_steps']
    profile.total_missing = snapshot['total_missing']
    profile.next_step = next_step
    profile.approval_threshold = profile.MINIMUM_APPROVAL_PROGRESS
    return profile


def _split_validation_profiles(queryset):
    ready_profiles = []
    draft_profiles = []

    for profile in queryset:
        decorated = _decorate_profile_progress(profile)
        if decorated.is_ready_for_approval:
            ready_profiles.append(decorated)
        else:
            draft_profiles.append(decorated)

    return ready_profiles, draft_profiles


def _validation_bucket_counts():
    ready_profiles, draft_profiles = _split_validation_profiles(
        _profile_progress_queryset().filter(validado=False)
    )
    return {
        'pending_profiles': len(ready_profiles),
        'incomplete_profiles': len(draft_profiles),
    }


def _resolve_report_range(request):
    """Resolve report preset or custom dates."""
    today = timezone.localdate()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    available_periods = {'diario', 'quinzenal', 'mensal', 'anual', 'personalizado'}
    has_custom_dates = bool(request.GET.get('data_inicio') or request.GET.get('data_fim'))

    period_key = (request.GET.get('periodo') or '').strip().lower()
    if period_key not in available_periods:
        period_key = 'personalizado' if has_custom_dates else 'mensal'

    def parse_date(value, fallback):
        if not value:
            return fallback
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return fallback

    if period_key == 'diario':
        start_date = end_date = today
    elif period_key == 'quinzenal':
        start_date = today - timedelta(days=14)
        end_date = today
    elif period_key == 'mensal':
        start_date = month_start
        end_date = today
    elif period_key == 'anual':
        start_date = year_start
        end_date = today
    else:
        start_date = parse_date(request.GET.get('data_inicio'), month_start)
        end_date = parse_date(request.GET.get('data_fim'), today)

    invalid_range = start_date > end_date
    if invalid_range:
        start_dt = None
        end_dt = None
    else:
        tz = timezone.get_current_timezone()
        start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
        end_dt = timezone.make_aware(datetime.combine(end_date, time.max), tz)

    labels = {
        'diario': 'Diario',
        'quinzenal': 'Quinzenal',
        'mensal': 'Mensal',
        'anual': 'Anual',
        'personalizado': 'Personalizado',
    }
    descriptions = {
        'diario': 'Leitura do dia corrente.',
        'quinzenal': 'Panorama acumulado dos ultimos 15 dias.',
        'mensal': 'Leitura do mes em curso ate hoje.',
        'anual': 'Consolidado do ano em curso ate hoje.',
        'personalizado': 'Intervalo definido manualmente pela equipa.',
    }

    query_params = {'periodo': period_key}
    if start_date and end_date:
        query_params['data_inicio'] = start_date.strftime('%Y-%m-%d')
        query_params['data_fim'] = end_date.strftime('%Y-%m-%d')

    return {
        'period_key': period_key,
        'period_label': labels.get(period_key, 'Mensal'),
        'period_description': descriptions.get(period_key, descriptions['mensal']),
        'start_date': start_date,
        'end_date': end_date,
        'start_dt': start_dt,
        'end_dt': end_dt,
        'invalid_range': invalid_range,
        'period_days': ((end_date - start_date).days + 1) if not invalid_range else 0,
        'querystring': urlencode(query_params),
    }


def _safe_rate(numerator, denominator):
    return round((numerator / denominator) * 100, 1) if denominator else 0


def _format_decimal(value):
    text = f"{value:.1f}"
    return text[:-2] if text.endswith('.0') else text


def _format_number(value):
    return f"{int(value):,}".replace(',', ' ')


def _format_percent(value):
    return f"{_format_decimal(value)}%"


def _top_counter_item(labels, empty_label):
    counts = Counter(label for label in labels if label)
    if not counts:
        return {'label': empty_label, 'total': 0}
    label, total = counts.most_common(1)[0]
    return {'label': str(label), 'total': int(total)}


def _top_group(queryset, value_field, mapping=None, empty_label='Sem dados no periodo.'):
    item = queryset.first()
    if not item:
        return {'label': empty_label, 'total': 0}

    raw_value = item.get(value_field)
    total = int(item.get('total') or 0)
    if not raw_value:
        return {'label': empty_label, 'total': total}

    label = mapping.get(raw_value, raw_value) if mapping else raw_value
    return {'label': str(label), 'total': total}


def _build_report_data(range_data):
    start_date = range_data['start_date']
    end_date = range_data['end_date']
    start_dt = range_data['start_dt']
    end_dt = range_data['end_dt']
    invalid_range = range_data['invalid_range']
    period_days = range_data['period_days']

    district_fallback = 'Exterior / sem distrito em STP'
    area_labels = dict(getattr(settings, 'AREAS_FORMACAO', []))
    job_type_labels = dict(JobPost.TIPO_CHOICES)

    if invalid_range:
        jovens_qs = YouthProfile.objects.none()
        empresas_qs = Company.objects.none()
        vagas_qs = JobPost.objects.none()
        candidaturas_qs = Application.objects.none()
        contactos_qs = ContactRequest.objects.none()
        jovens_novos = empresas_novas = vagas_novas = candidaturas_novas = 0
        pedidos_contacto_novos = perfis_validados = candidaturas_aceites = 0
        pedidos_contacto_aprovados = colocacoes_emprego = 0
        pedidos_contacto_respondidos = 0
        pending_profiles_snapshot = pending_contacts_snapshot = active_jobs_snapshot = 0
        top_district = {'label': 'Sem entradas de jovens', 'total': 0}
        top_company = {'label': 'Sem candidaturas', 'total': 0}
        top_area = {'label': 'Sem area dominante', 'total': 0}
        top_job_type = {'label': 'Sem tipo dominante', 'total': 0}
        district_list = []
        level_list = []
        area_list = []
        job_type_list = []
    else:
        jovens_qs = YouthProfile.objects.select_related('user__distrito').filter(
            created_at__range=(start_dt, end_dt)
        )
        empresas_qs = Company.objects.select_related('distrito').filter(
            created_at__range=(start_dt, end_dt)
        )
        vagas_qs = JobPost.objects.select_related('company', 'distrito').filter(
            data_publicacao__range=(start_dt, end_dt)
        )
        candidaturas_qs = Application.objects.select_related(
            'job',
            'job__company',
            'youth',
            'youth__user',
        ).filter(created_at__range=(start_dt, end_dt))
        contactos_qs = ContactRequest.objects.select_related(
            'company',
            'company__user',
            'youth',
            'youth__user',
        ).filter(created_at__range=(start_dt, end_dt))

        jovens_novos = jovens_qs.count()
        empresas_novas = empresas_qs.count()
        vagas_novas = vagas_qs.count()
        candidaturas_novas = candidaturas_qs.count()
        pedidos_contacto_novos = contactos_qs.count()

        perfis_validados = YouthProfile.objects.filter(
            validado=True,
            updated_at__range=(start_dt, end_dt),
        ).count()
        candidaturas_aceites = Application.objects.filter(
            estado='ACEITE',
            updated_at__range=(start_dt, end_dt),
        ).count()
        pedidos_contacto_aprovados = ContactRequest.objects.filter(
            estado='APROVADO',
            responded_at__range=(start_dt, end_dt),
        ).count()
        pedidos_contacto_respondidos = ContactRequest.objects.filter(
            responded_at__range=(start_dt, end_dt),
        ).count()
        colocacoes_emprego = _employment_placements_queryset().filter(
            updated_at__range=(start_dt, end_dt),
        ).count()

        pending_profiles_snapshot = YouthProfile.objects.filter(
            completo=True,
            validado=False,
            created_at__lte=end_dt,
        ).count()
        pending_contacts_snapshot = ContactRequest.objects.filter(
            estado='PENDENTE',
            created_at__lte=end_dt,
        ).count()
        active_jobs_snapshot = JobPost.objects.filter(
            estado='ATIVA',
            data_publicacao__lte=end_dt,
        ).count()

        top_district = _top_counter_item(
            [
                profile.distrito.nome if profile.distrito else district_fallback
                for profile in jovens_qs
            ],
            'Sem entradas de jovens',
        )
        top_company = _top_group(
            Company.objects.filter(job_posts__applications__created_at__range=(start_dt, end_dt))
            .values('nome')
            .annotate(total=Count('job_posts__applications'))
            .order_by('-total', 'nome'),
            'nome',
            empty_label='Sem candidaturas',
        )
        top_area = _top_group(
            Education.objects.filter(profile__created_at__range=(start_dt, end_dt))
            .values('area_formacao')
            .annotate(total=Count('id'))
            .order_by('-total', 'area_formacao'),
            'area_formacao',
            mapping=area_labels,
            empty_label='Sem area dominante',
        )
        top_job_type = _top_group(
            vagas_qs.values('tipo').annotate(total=Count('id')).order_by('-total', 'tipo'),
            'tipo',
            mapping=job_type_labels,
            empty_label='Sem tipo dominante',
        )

        district_counter = Counter(
            profile.distrito.nome if profile.distrito else district_fallback
            for profile in jovens_qs
        )
        district_list = district_counter.most_common()

        level_list = [
            (
                dict(Education.NIVEL_CHOICES).get(item['nivel'], item['nivel']),
                int(item['total']),
            )
            for item in Education.objects.filter(profile__created_at__range=(start_dt, end_dt))
            .values('nivel')
            .annotate(total=Count('id'))
            .order_by('-total', 'nivel')
            if item['nivel']
        ]
        area_list = [
            (
                area_labels.get(item['area_formacao'], item['area_formacao']),
                int(item['total']),
            )
            for item in Education.objects.filter(profile__created_at__range=(start_dt, end_dt))
            .values('area_formacao')
            .annotate(total=Count('id'))
            .order_by('-total', 'area_formacao')
            if item['area_formacao']
        ]
        job_type_list = [
            (
                job_type_labels.get(item['tipo'], item['tipo']),
                int(item['total']),
            )
            for item in vagas_qs.values('tipo').annotate(total=Count('id')).order_by('-total', 'tipo')
            if item['tipo']
        ]

    total_movimentos = (
        jovens_novos
        + empresas_novas
        + vagas_novas
        + candidaturas_novas
        + pedidos_contacto_novos
    )
    media_diaria = round(total_movimentos / period_days, 1) if period_days else 0
    validation_rate = _safe_rate(perfis_validados, jovens_novos)
    acceptance_rate = _safe_rate(candidaturas_aceites, candidaturas_novas)
    contact_response_rate = _safe_rate(pedidos_contacto_respondidos, pedidos_contacto_novos)
    contact_approval_rate = _safe_rate(pedidos_contacto_aprovados, pedidos_contacto_respondidos)
    applications_per_job = round(candidaturas_novas / vagas_novas, 1) if vagas_novas else 0

    report_mix = _add_percent([
        {'nome': 'Jovens', 'total': jovens_novos, 'icon': 'bi-person'},
        {'nome': 'Empresas', 'total': empresas_novas, 'icon': 'bi-building'},
        {'nome': 'Vagas', 'total': vagas_novas, 'icon': 'bi-briefcase'},
        {'nome': 'Candidaturas', 'total': candidaturas_novas, 'icon': 'bi-send'},
        {'nome': 'Contactos', 'total': pedidos_contacto_novos, 'icon': 'bi-telephone'},
    ])

    if invalid_range:
        headline_insight = 'Ajuste o intervalo para gerar o relatorio.'
    elif total_movimentos == 0:
        headline_insight = 'Nao houve novos movimentos no periodo selecionado.'
    elif colocacoes_emprego:
        headline_insight = (
            f"O periodo fechou com {_format_number(colocacoes_emprego)} colocacoes em emprego "
            f"e {_format_number(candidaturas_aceites)} candidaturas aceites."
        )
    elif candidaturas_novas and top_company['total']:
        headline_insight = (
            f"A procura esteve mais concentrada em {top_company['label']}, "
            f"que reuniu {_format_number(top_company['total'])} candidaturas."
        )
    elif vagas_novas and top_job_type['total']:
        headline_insight = f"A oferta do periodo foi puxada por vagas de {top_job_type['label']}."
    else:
        headline_insight = (
            f"Foram registados {_format_number(total_movimentos)} movimentos em "
            f"{_format_number(period_days)} dias."
        )

    executive_metrics = [
        {
            'label': 'Novos jovens',
            'value': _format_number(jovens_novos),
            'subtitle': 'Entradas de perfis no periodo.',
            'icon': 'bi-person',
        },
        {
            'label': 'Novas empresas',
            'value': _format_number(empresas_novas),
            'subtitle': 'Perfis empresariais criados.',
            'icon': 'bi-building',
        },
        {
            'label': 'Novas vagas',
            'value': _format_number(vagas_novas),
            'subtitle': 'Publicacoes de oportunidades.',
            'icon': 'bi-briefcase',
        },
        {
            'label': 'Candidaturas',
            'value': _format_number(candidaturas_novas),
            'subtitle': f"{_format_decimal(applications_per_job)} candidaturas por vaga.",
            'icon': 'bi-send',
        },
        {
            'label': 'Pedidos de contacto',
            'value': _format_number(pedidos_contacto_novos),
            'subtitle': 'Solicitacoes abertas por empresas.',
            'icon': 'bi-telephone',
        },
    ]

    outcome_metrics = [
        {
            'label': 'Perfis validados',
            'value': _format_number(perfis_validados),
            'subtitle': f"Taxa de validacao: {_format_percent(validation_rate)}.",
            'icon': 'bi-patch-check',
        },
        {
            'label': 'Candidaturas aceites',
            'value': _format_number(candidaturas_aceites),
            'subtitle': f"Taxa de aceite: {_format_percent(acceptance_rate)}.",
            'icon': 'bi-hand-thumbs-up',
        },
        {
            'label': 'Pedidos aprovados',
            'value': _format_number(pedidos_contacto_aprovados),
            'subtitle': f"Aprovacao sobre respondidos: {_format_percent(contact_approval_rate)}.",
            'icon': 'bi-telephone-forward',
        },
        {
            'label': 'Pedidos respondidos',
            'value': _format_number(pedidos_contacto_respondidos),
            'subtitle': f"Taxa de resposta: {_format_percent(contact_response_rate)}.",
            'icon': 'bi-reply',
        },
        {
            'label': 'Colocacoes em emprego',
            'value': _format_number(colocacoes_emprego),
            'subtitle': 'Candidaturas aceites em vagas de emprego.',
            'icon': 'bi-briefcase-fill',
        },
    ]

    backlog_metrics = [
        {'label': 'Perfis por validar', 'value': _format_number(pending_profiles_snapshot)},
        {'label': 'Pedidos pendentes', 'value': _format_number(pending_contacts_snapshot)},
        {'label': 'Vagas ativas', 'value': _format_number(active_jobs_snapshot)},
    ]

    highlights = [
        {
            'label': 'Distrito com mais entradas',
            'value': top_district['label'],
            'note': (
                f"{_format_number(top_district['total'])} jovens."
                if top_district['total'] else 'Sem entradas de jovens no periodo.'
            ),
        },
        {
            'label': 'Empresa com mais candidaturas',
            'value': top_company['label'],
            'note': (
                f"{_format_number(top_company['total'])} candidaturas recebidas."
                if top_company['total'] else 'Sem candidaturas registadas no periodo.'
            ),
        },
        {
            'label': 'Area formativa dominante',
            'value': top_area['label'],
            'note': (
                f"{_format_number(top_area['total'])} registos de formacao."
                if top_area['total'] else 'Sem area dominante neste intervalo.'
            ),
        },
        {
            'label': 'Tipo de vaga dominante',
            'value': top_job_type['label'],
            'note': (
                f"{_format_number(top_job_type['total'])} vagas abertas."
                if top_job_type['total'] else 'Sem publicacoes de vagas no periodo.'
            ),
        },
    ]

    overview_rows = [
        ('Periodo', range_data['period_label']),
        ('Intervalo', f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"),
        ('Dias analisados', _format_number(period_days)),
        ('Total de movimentos', _format_number(total_movimentos)),
        ('Media diaria', _format_decimal(media_diaria)),
        ('Novos jovens', _format_number(jovens_novos)),
        ('Novas empresas', _format_number(empresas_novas)),
        ('Novas vagas', _format_number(vagas_novas)),
        ('Candidaturas', _format_number(candidaturas_novas)),
        ('Pedidos de contacto', _format_number(pedidos_contacto_novos)),
    ]

    outcome_rows = [
        ('Perfis validados', _format_number(perfis_validados)),
        ('Taxa de validacao', _format_percent(validation_rate)),
        ('Candidaturas aceites', _format_number(candidaturas_aceites)),
        ('Taxa de aceite', _format_percent(acceptance_rate)),
        ('Pedidos respondidos', _format_number(pedidos_contacto_respondidos)),
        ('Taxa de resposta', _format_percent(contact_response_rate)),
        ('Pedidos aprovados', _format_number(pedidos_contacto_aprovados)),
        ('Taxa de aprovacao', _format_percent(contact_approval_rate)),
        ('Colocacoes em emprego', _format_number(colocacoes_emprego)),
    ]

    snapshot_rows = [
        ('Perfis por validar', _format_number(pending_profiles_snapshot)),
        ('Pedidos pendentes', _format_number(pending_contacts_snapshot)),
        ('Vagas ativas', _format_number(active_jobs_snapshot)),
    ]

    highlight_rows = [(item['label'], item['value'], item['note']) for item in highlights]

    return {
        'jovens_qs': jovens_qs,
        'empresas_qs': empresas_qs,
        'vagas_qs': vagas_qs,
        'candidaturas_qs': candidaturas_qs,
        'contactos_qs': contactos_qs,
        'jovens_novos': jovens_novos,
        'empresas_novas': empresas_novas,
        'vagas_novas': vagas_novas,
        'candidaturas_novas': candidaturas_novas,
        'pedidos_contacto_novos': pedidos_contacto_novos,
        'perfis_validados': perfis_validados,
        'candidaturas_aceites': candidaturas_aceites,
        'pedidos_contacto_aprovados': pedidos_contacto_aprovados,
        'pedidos_contacto_respondidos': pedidos_contacto_respondidos,
        'colocacoes_emprego': colocacoes_emprego,
        'period_days': period_days,
        'total_movimentos': total_movimentos,
        'media_diaria': media_diaria,
        'report_mix': report_mix,
        'executive_metrics': executive_metrics,
        'outcome_metrics': outcome_metrics,
        'backlog_metrics': backlog_metrics,
        'highlights': highlights,
        'headline_insight': headline_insight,
        'overview_rows': overview_rows,
        'outcome_rows': outcome_rows,
        'snapshot_rows': snapshot_rows,
        'highlight_rows': highlight_rows,
        'district_list': district_list,
        'level_list': level_list,
        'area_list': area_list,
        'job_type_list': job_type_list,
        'applications_per_job': applications_per_job,
        'validation_rate': validation_rate,
        'acceptance_rate': acceptance_rate,
        'contact_response_rate': contact_response_rate,
        'contact_approval_rate': contact_approval_rate,
    }


def _with_admin_context(request, context=None):
    """Attach shared navigation stats to admin dashboard pages."""
    queue_counts = _validation_bucket_counts()
    nav_context = {
        'admin_nav': {
            'pending_profiles': queue_counts['pending_profiles'],
            'incomplete_profiles': queue_counts['incomplete_profiles'],
            'pending_contacts': 0,
            'total_users': 0,
            'active_jobs': 0,
            'placed_youths': 0,
        }
    }

    if getattr(request.user, 'is_admin', False):
        placement_qs = _employment_placements_queryset()
        nav_context['admin_nav'].update({
            'pending_contacts': ContactRequest.objects.filter(estado='PENDENTE').count(),
            'total_users': User.objects.count(),
            'active_jobs': JobPost.objects.filter(estado='ATIVA').count(),
            'placed_youths': placement_qs.order_by().values('youth_id').distinct().count(),
        })

    if context:
        nav_context.update(context)
    return nav_context


def _get_client_ip(request):
    forwarded = (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip()
    return forwarded or request.META.get('REMOTE_ADDR')


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'sim', 'yes', 'y'}
    return False


def _display_value(value, empty='-'):
    if value is None:
        return empty
    if isinstance(value, bool):
        return _('Sim') if value else _('Nao')
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return ', '.join(items) if items else empty
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, indent=2) if value else empty
    if isinstance(value, str):
        value = value.strip()
        return value or empty
    return value


def _display_date(value, with_time=False):
    if not value:
        return '-'
    if with_time:
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%d/%m/%Y %H:%M')
    return value.strftime('%d/%m/%Y')


def _make_field(label, value, keep_empty=False):
    display = _display_value(value, empty='')
    if display == '':
        if not keep_empty:
            return None
        display = '-'
    return {'label': label, 'value': display}


def _decode_offline_json(uploaded_file):
    raw = uploaded_file.read()
    uploaded_file.seek(0)

    decoded = None
    for encoding in ('utf-8-sig', 'utf-8', 'cp1252'):
        try:
            decoded = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if decoded is None:
        raise ValueError(_('Não foi possível ler o ficheiro offline.'))

    try:
        return json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ValueError(_('O ficheiro offline não contem um JSON valido.')) from exc


def _build_choice_reference(choices):
    return [
        {
            'value': value,
            'label': str(label),
        }
        for value, label in choices
    ]


def _clean_text(value):
    return str(value or '').strip()


def _normalize_code_list(value):
    if isinstance(value, str):
        raw_items = value.split(',') if ',' in value else [value]
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = []

    normalized = []
    for item in raw_items:
        current = str(item or '').strip().upper()
        if current and current not in normalized:
            normalized.append(current)
    return normalized


def _build_offline_registration_payload(profile_type, admin_user):
    districts = [
        {
            'code': district.codigo,
            'name': district.nome,
        }
        for district in District.objects.order_by('nome')
    ]
    profile_label = 'Jovem' if profile_type == 'JO' else 'Empresa'

    registration_data = {
        'nome': '',
        'telefone': '',
        'email': '',
        'distrito_codigo': '',
        'consentimento_dados': False,
        'consentimento_contacto': False,
        'password': '',
        'password_confirm': '',
        'collected_offline_at': '',
        'collected_by_name': '',
        'collected_by_role': '',
        'observacoes': '',
    }

    references = {
        'districts': districts,
    }

    if profile_type == 'JO':
        registration_data.update({
            'bi_numero': '',
            'data_nascimento': '',
            'sexo': '',
            'localidade': '',
            'contacto_alternativo': '',
            'situacao_atual': 'DES',
            'disponibilidade': 'SIM',
            'preferencia_oportunidade': 'EMP',
            'nivel': '',
            'area_formacao': '',
            'instituicao': '',
            'ano': '',
            'curso': '',
        })
        references.update({
            'sexo_choices': _build_choice_reference(YouthProfile.SEXO_CHOICES),
            'situacao_choices': _build_choice_reference(YouthProfile.SITUACAO_CHOICES),
            'disponibilidade_choices': _build_choice_reference(YouthProfile.DISPONIBILIDADE_CHOICES),
            'preferencia_choices': _build_choice_reference(YouthProfile.OPORTUNIDADE_CHOICES),
            'education_level_choices': _build_choice_reference(Education.NIVEL_CHOICES),
            'area_formacao_choices': _build_choice_reference(settings.AREAS_FORMACAO),
        })
    else:
        registration_data.update({
            'nif': '',
            'setor_codes': [],
            'descricao': '',
            'website': '',
            'endereco': '',
        })
        references.update({
            'setor_choices': _build_choice_reference(Company.SETOR_CHOICES),
        })

    return {
        'schema': 'bnj_offline_registration',
        'version': 1,
        'profile_type': profile_type,
        'profile_label': profile_label,
        'generated_at': timezone.now().isoformat(),
        'generated_by': {
            'admin_id': admin_user.id,
            'admin_name': admin_user.nome,
        },
        'instructions': [
            'Preencha apenas os campos dentro de "registration_data".',
            'Use os codigos apresentados em "references" para distrito, setor ou escolhas do perfil.',
            'A palavra-passe deve ter pelo menos 8 caracteres e ser confirmada no proprio ficheiro.',
            'Depois da importação, elimine o ficheiro local se ele contiver dados sensiveis.',
        ],
        'references': references,
        'registration_data': registration_data,
    }


def _offline_registrations_context(request, export_form=None, import_form=None):
    recent_logs = AuditLog.objects.filter(
        acao__in=['Registo offline exportado', 'Registo offline importado']
    ).order_by('-created_at')[:6]

    context = {
        'export_form': export_form or OfflineRegistrationExportForm(),
        'import_form': import_form or OfflineRegistrationImportForm(),
        'offline_summary': {
            'jovens': User.objects.filter(perfil=User.ProfileType.JOVEM).count(),
            'empresas': User.objects.filter(perfil=User.ProfileType.EMPRESA).count(),
            'exports': AuditLog.objects.filter(acao='Registo offline exportado').count(),
            'imports': AuditLog.objects.filter(acao='Registo offline importado').count(),
        },
        'recent_offline_logs': recent_logs,
    }
    return _with_admin_context(request, context)


def _import_offline_registration_payload(payload, admin_user, file_name, ip_address):
    if payload.get('schema') != 'bnj_offline_registration':
        raise ValueError(_('O ficheiro não pertence ao formato de registo offline da plataforma.'))
    if payload.get('version') != 1:
        raise ValueError(_('A versao do ficheiro offline não e suportada.'))

    profile_type = _clean_text(payload.get('profile_type')).upper()
    if profile_type not in {User.ProfileType.JOVEM, User.ProfileType.EMPRESA}:
        raise ValueError(_('O tipo de registo offline deve ser Jovem ou Empresa.'))

    data = payload.get('registration_data') or {}

    nome = _clean_text(data.get('nome'))
    telefone = _clean_text(data.get('telefone'))
    email = _clean_text(data.get('email')) or None
    district_code = _clean_text(data.get('distrito_codigo')).upper()
    password = _clean_text(data.get('password'))
    password_confirm = _clean_text(data.get('password_confirm'))
    consentimento_dados = _coerce_bool(data.get('consentimento_dados'))
    consentimento_contacto = _coerce_bool(data.get('consentimento_contacto'))
    collected_offline_at = _clean_text(data.get('collected_offline_at'))
    collected_by_name = _clean_text(data.get('collected_by_name'))
    collected_by_role = _clean_text(data.get('collected_by_role'))
    observacoes = _clean_text(data.get('observacoes'))

    if not nome:
        raise ValueError(_('O nome é obrigatório no registo offline.'))
    if not telefone:
        raise ValueError(_('O telemóvel é obrigatório no registo offline.'))
    if len(password) < 8:
        raise ValueError(_('A palavra-passe do registo offline deve ter pelo menos 8 caracteres.'))
    if password != password_confirm:
        raise ValueError(_('A palavra-passe e a confirmação não coincidem.'))

    if User.objects.filter(telefone=telefone).exists():
        raise ValueError(_('Já existe um utilizador com este telemóvel.'))
    if email and User.objects.filter(email__iexact=email).exists():
        raise ValueError(_('Já existe um utilizador com este email.'))

    district = None
    if district_code:
        try:
            district = District.objects.get(codigo__iexact=district_code)
        except District.DoesNotExist as exc:
            raise ValueError(_('O distrito indicado no ficheiro offline não existe.')) from exc
    elif profile_type == User.ProfileType.EMPRESA:
        raise ValueError(_('O distrito é obrigatório para registos offline de empresas.'))

    data_consentimento = timezone.now() if consentimento_dados or consentimento_contacto else None

    with transaction.atomic():
        if profile_type == User.ProfileType.JOVEM:
            bi_numero = _clean_text(data.get('bi_numero'))
            if not bi_numero:
                raise ValueError(_('O número do BI é obrigatório para registos offline de jovens.'))
            if User.objects.filter(bi_numero__iexact=bi_numero).exists():
                raise ValueError(_('Já existe um utilizador com este número de BI.'))

            data_nascimento_raw = _clean_text(data.get('data_nascimento'))
            data_nascimento = None
            if data_nascimento_raw:
                try:
                    data_nascimento = datetime.strptime(data_nascimento_raw, '%Y-%m-%d').date()
                except ValueError as exc:
                    raise ValueError(_('A data de nascimento deve estar no formato AAAA-MM-DD.')) from exc

            sexo = _clean_text(data.get('sexo')).upper()
            localidade = _clean_text(data.get('localidade'))
            contacto_alternativo = _clean_text(data.get('contacto_alternativo'))
            situacao_atual = _clean_text(data.get('situacao_atual') or 'DES').upper()
            disponibilidade = _clean_text(data.get('disponibilidade') or 'SIM').upper()
            preferencia_oportunidade = _clean_text(data.get('preferencia_oportunidade') or 'EMP').upper()
            nivel = _clean_text(data.get('nivel')).upper()
            area_formacao = _clean_text(data.get('area_formacao')).upper()
            instituicao = _clean_text(data.get('instituicao'))
            ano_raw = _clean_text(data.get('ano'))
            curso = _clean_text(data.get('curso'))

            if sexo and sexo not in dict(YouthProfile.SEXO_CHOICES):
                raise ValueError(_('O valor de sexo indicado no ficheiro offline e invalido.'))
            if situacao_atual not in dict(YouthProfile.SITUACAO_CHOICES):
                raise ValueError(_('A situação atual indicada no ficheiro offline e invalida.'))
            if disponibilidade not in dict(YouthProfile.DISPONIBILIDADE_CHOICES):
                raise ValueError(_('A disponibilidade indicada no ficheiro offline e invalida.'))
            if preferencia_oportunidade not in dict(YouthProfile.OPORTUNIDADE_CHOICES):
                raise ValueError(_('A preferencia de oportunidade indicada no ficheiro offline e invalida.'))

            if nivel and nivel not in dict(Education.NIVEL_CHOICES):
                raise ValueError(_('O nivel de educação indicado no ficheiro offline e invalido.'))
            if area_formacao and area_formacao not in dict(settings.AREAS_FORMACAO):
                raise ValueError(_('A área de formação indicada no ficheiro offline e invalida.'))
            if any([nivel, area_formacao, instituicao, ano_raw, curso]) and (not nivel or not area_formacao):
                raise ValueError(_('Para guardar educação offline, informe pelo menos nivel e área de formação.'))

            ano = None
            if ano_raw:
                try:
                    ano = int(ano_raw)
                except (TypeError, ValueError) as exc:
                    raise ValueError(_('O ano de conclusao do registo offline deve ser numerico.')) from exc

            user = User.objects.create_user(
                telefone=telefone,
                nome=nome,
                password=password,
                email=email,
                perfil=User.ProfileType.JOVEM,
                distrito=district,
                consentimento_dados=consentimento_dados,
                consentimento_contacto=consentimento_contacto,
                data_consentimento=data_consentimento,
                bi_numero=bi_numero,
            )
            YouthProfile.objects.create(
                user=user,
                data_nascimento=data_nascimento,
                sexo=sexo,
                localidade=localidade,
                contacto_alternativo=contacto_alternativo,
                situacao_atual=situacao_atual,
                disponibilidade=disponibilidade,
                preferencia_oportunidade=preferencia_oportunidade,
                consentimento_sms=consentimento_contacto,
                consentimento_whatsapp=consentimento_contacto,
                consentimento_email=bool(email) and consentimento_contacto,
                completo=True,
                validado=False,
            )
            if nivel and area_formacao:
                Education.objects.create(
                    profile=user.youth_profile,
                    nivel=nivel,
                    area_formacao=area_formacao,
                    instituicao=instituicao or 'Não específicado',
                    ano=ano,
                    curso=curso,
                )
            imported_label = 'Jovem'
        else:
            nif = _clean_text(data.get('nif'))
            if not nif:
                raise ValueError(_('O NIF é obrigatório para registos offline de empresas.'))
            if User.objects.filter(nif__iexact=nif).exists():
                raise ValueError(_('Já existe um utilizador com este NIF.'))

            setor_codes = _normalize_code_list(data.get('setor_codes'))
            invalid_setores = [code for code in setor_codes if code not in dict(Company.SETOR_CHOICES)]
            if invalid_setores:
                raise ValueError(_('O ficheiro offline contem setores invalidos para a empresa.'))

            user = User.objects.create_user(
                telefone=telefone,
                nome=nome,
                password=password,
                email=email,
                perfil=User.ProfileType.EMPRESA,
                distrito=district,
                consentimento_dados=consentimento_dados,
                consentimento_contacto=consentimento_contacto,
                data_consentimento=data_consentimento,
                nome_empresa=nome,
                nif=nif,
            )
            Company.objects.create(
                user=user,
                nome=nome,
                nif=nif,
                setor=setor_codes,
                descricao=_clean_text(data.get('descricao')),
                telefone=telefone,
                email=email or '',
                website=_clean_text(data.get('website')),
                distrito=district,
                endereco=_clean_text(data.get('endereco')),
                ativa=True,
                verificada=False,
            )
            imported_label = 'Empresa'

        Notification.objects.create(
            user=user,
            titulo=_('Registo offline recebido'),
            mensagem=_('O teu registo offline foi importado com sucesso na plataforma.'),
            tipo='SUCESSO',
        )

        notify_admins(
            _('Novo utilizador registado'),
            _('Novo utilizador importado offline: %(nome)s (%(perfil)s).') % {
                'nome': user.nome,
                'perfil': user.get_perfil_display(),
            },
            tipo='INFO',
        )

        if user.is_jovem and user.has_youth_profile():
            profile = user.youth_profile
            if profile.is_ready_for_approval and not profile.validado:
                if profile.is_underage_for_validation:
                    validation_message = _(
                        'O perfil offline de %(nome)s atingiu %(progress)s%%, mas o candidato tem menos de %(minimum_age)s anos e nao pode ser aprovado.'
                    ) % {
                        'nome': user.nome,
                        'progress': profile.approval_progress,
                        'minimum_age': profile.MINIMUM_VALIDATION_AGE,
                    }
                else:
                    validation_message = _(
                        'O perfil offline de %(nome)s atingiu %(progress)s%% e aguarda validacao administrativa.'
                    ) % {
                        'nome': user.nome,
                        'progress': profile.approval_progress,
                    }

                notify_admins(
                    _('Perfil pronto para validacao'),
                    validation_message,
                    tipo='INFO',
                )

        AuditLog.objects.create(
            user=admin_user,
            acao='Registo offline importado',
            payload={
                'file_name': file_name,
                'profile_type': profile_type,
                'user_id': user.id,
                'user_name': user.nome,
                'telefone': user.telefone,
                'district_code': district.codigo if district else '',
                'collected_offline_at': collected_offline_at,
                'collected_by_name': collected_by_name,
                'collected_by_role': collected_by_role,
                'observacoes': observacoes,
            },
            ip_address=ip_address,
        )

    return user, imported_label


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
    employment_placements = _employment_placements_queryset()
    employment_summary = _employment_placements_summary(employment_placements)
    queue_base = _profile_progress_queryset().filter(validado=False).order_by('-updated_at', '-created_at')
    perfis_pendentes, perfis_incompletos = _split_validation_profiles(queue_base)
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
        'jovens_colocados': employment_summary['youths'],
        'colocacoes_emprego': employment_summary['placements'],
        'empresas_com_colocacoes': employment_summary['companies'],
    }
    stats['validacoes_pendentes'] = len(perfis_pendentes)
    stats['jovens_nao_completos'] = len(perfis_incompletos)
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
    colocacoes_recentes = employment_placements.order_by('-updated_at', '-id')[:10]
    
    context = _with_admin_context(request, {
        'stats': stats,
        'jovens_por_distrito': jovens_por_distrito,
        'educacao_stats': educacao_stats,
        'area_stats': area_stats,
        'jovens_recentes': jovens_recentes,
        'empresas_recentes': empresas_recentes,
        'vagas_recentes': vagas_recentes,
        'pedidos_pendentes': pedidos_pendentes,
        'perfis_pendentes': perfis_pendentes[:10],
        'colocacoes_recentes': colocacoes_recentes,
    })
    
    return render(request, 'dashboard/admin.html', context)


@admin_required
def incomplete_profiles(request):
    """Admin queue for profiles still below the approval threshold."""
    all_profiles = _profile_progress_queryset().filter(validado=False)

    query = (request.GET.get('q') or '').strip()
    distrito_id = (request.GET.get('distrito') or '').strip()

    filtered_profiles = all_profiles
    if query:
        filtered_profiles = filtered_profiles.filter(
            Q(user__nome__icontains=query) |
            Q(user__telefone__icontains=query) |
            Q(user__email__icontains=query) |
            Q(user__bi_numero__icontains=query)
        )
    if distrito_id:
        filtered_profiles = filtered_profiles.filter(user__distrito_id=distrito_id)

    today = timezone.localdate()
    _, all_draft_profiles = _split_validation_profiles(all_profiles.order_by('-updated_at', '-created_at'))
    _, filtered_draft_profiles = _split_validation_profiles(filtered_profiles.order_by('-updated_at', '-created_at'))
    profile_cards = []
    near_ready_count = 0
    early_stage_count = 0

    for profile in filtered_draft_profiles:
        profile.is_recently_updated = profile.updated_at.date() == today

        if profile.progress_percent >= max(35, profile.MINIMUM_APPROVAL_PROGRESS - 10):
            profile.progress_stage = 'Quase pronto'
            profile.progress_stage_tone = 'success'
            near_ready_count += 1
        elif profile.progress_percent < 20 or profile.completed_steps == 0:
            profile.progress_stage = 'Primeiros passos'
            profile.progress_stage_tone = 'pending'
            early_stage_count += 1
        else:
            profile.progress_stage = 'Em preenchimento'
            profile.progress_stage_tone = 'info'

        profile_cards.append(profile)

    profile_cards.sort(
        key=lambda item: (item.completed_steps, item.progress_percent, item.updated_at, item.created_at),
        reverse=True,
    )

    paginator = Paginator(profile_cards, 12)
    page_number = request.GET.get('page') or 1
    profiles_page = paginator.get_page(page_number)

    filters = request.GET.copy()
    if 'page' in filters:
        del filters['page']
    filters_qs = filters.urlencode()

    summary = {
        'total_incomplete': len(all_draft_profiles),
        'filtered_total': len(profile_cards),
        'districts': len({profile.user.distrito_id for profile in filtered_draft_profiles if profile.user.distrito_id}),
        'updated_today': sum(1 for profile in filtered_draft_profiles if profile.updated_at.date() == today),
        'near_ready': near_ready_count,
        'early_stage': early_stage_count,
        'minimum_progress': YouthProfile.MINIMUM_APPROVAL_PROGRESS,
    }

    context = _with_admin_context(request, {
        'profiles_page': profiles_page,
        'districts': District.objects.all().order_by('nome'),
        'filtro_q': query,
        'filtro_distrito': distrito_id,
        'filters_qs': filters_qs,
        'incomplete_summary': summary,
    })

    return render(request, 'dashboard/incomplete_profiles.html', context)


@admin_required
def employment_placements(request):
    """Admin view for youths placed in jobs through accepted applications."""
    all_placements = _employment_placements_queryset().order_by('-updated_at', '-id')
    query = (request.GET.get('q') or '').strip()
    placements = all_placements

    if query:
        placements = placements.filter(
            Q(youth__user__nome__icontains=query) |
            Q(youth__user__telefone__icontains=query) |
            Q(job__company__nome__icontains=query) |
            Q(job__company__user__telefone__icontains=query) |
            Q(job__titulo__icontains=query)
        )

    summary = _employment_placements_summary(all_placements)
    summary['filtered'] = placements.count()
    summary['filtered_youths'] = placements.order_by().values('youth_id').distinct().count()

    context = _with_admin_context(request, {
        'placements': placements,
        'employment_summary': summary,
        'filtro_q': query,
    })

    return render(request, 'dashboard/employment_placements.html', context)


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
    stats['validacoes_pendentes'] = _validation_bucket_counts()['pending_profiles']
    stats['jovens_nao_completos'] = _validation_bucket_counts()['incomplete_profiles']
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
    'Lista de utilizadores'
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

            notify_admins(
                _('Novo utilizador registado'),
                _('Novo utilizador criado no painel administrativo: %(nome)s (%(perfil)s).') % {
                    'nome': user.nome,
                    'perfil': user.get_perfil_display(),
                },
                tipo='INFO',
            )

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

    filtered_total = users.count()
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)

    summary = {
        'total': User.objects.count(),
        'ativos': User.objects.filter(is_active=True).count(),
        'empresas': User.objects.filter(perfil='EMP').count(),
        'equipa': User.objects.filter(perfil__in=['ADM', 'OP', 'TEC']).count(),
        'novos_7d': User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=7)).count(),
        'filtrados': filtered_total,
    }

    context = _with_admin_context(request, {
        'users': users_page.object_list,
        'users_page': users_page,
        'filtro_q': query,
        'filtro_perfil': perfil,
        'filtro_ativo': ativo,
        'create_user_form': create_user_form,
        'user_summary': summary,
    })
    
    return render(request, 'dashboard/user_list.html', context)


@admin_required
def user_detail(request, pk):
    'Detalhe completo de um utilizador para consulta administrativa.'
    target_user = get_object_or_404(User.objects.select_related('distrito'), pk=pk)
    next_url = request.GET.get('next') or reverse('dashboard:user_list')

    youth_profile = None
    company_profile = None
    youth_fields = []
    company_fields = []
    youth_education = []
    youth_experiences = []
    youth_documents = []
    youth_skills = []
    youth_applications = []
    youth_contact_requests = []
    company_jobs = []
    company_applications = []
    company_contact_requests = []
    account_fields = [
        field for field in [
            _make_field('Perfil', target_user.get_perfil_display(), keep_empty=True),
            _make_field('Nome', target_user.nome, keep_empty=True),
            _make_field('Telemovel', target_user.telefone, keep_empty=True),
            _make_field('Email', target_user.email),
            _make_field('Distrito', target_user.distrito.nome if target_user.distrito else None),
            _make_field('Conta ativa', target_user.is_active, keep_empty=True),
            _make_field('Conta verificada', target_user.is_verified, keep_empty=True),
            _make_field('Consentimento de dados', target_user.consentimento_dados, keep_empty=True),
            _make_field('Consentimento de contacto', target_user.consentimento_contacto, keep_empty=True),
            _make_field('Registo', _display_date(target_user.date_joined, with_time=True)),
            _make_field('Numero do BI', target_user.bi_numero),
            _make_field('Nome da empresa', target_user.nome_empresa),
            _make_field('NIF', target_user.nif),
            _make_field('Setor', target_user.setor_empresa),
            _make_field('Associacao/parceiro', target_user.associacao_parceira),
        ] if field
    ]

    if target_user.is_jovem:
        youth_profile = (
            YouthProfile.objects.select_related('user', 'user__distrito')
            .prefetch_related(
                'education',
                'experiences',
                'documents',
                'youth_skills__skill',
                'applications__job__company',
                'applications__job__distrito',
                'contact_requests__company',
            )
            .filter(user=target_user)
            .first()
        )

        if youth_profile:
            youth_education = youth_profile.education.all()
            youth_experiences = youth_profile.experiences.all()
            youth_documents = youth_profile.documents.all()
            youth_skills = youth_profile.youth_skills.all()
            youth_applications = youth_profile.applications.all()
            youth_contact_requests = youth_profile.contact_requests.all()
            youth_fields = [
                field for field in [
                    _make_field('Data de nascimento', _display_date(youth_profile.data_nascimento)),
                    _make_field('Idade', youth_profile.idade),
                    _make_field('Sexo', youth_profile.get_sexo_display()),
                    _make_field('Localidade', youth_profile.localidade),
                    _make_field('Contacto alternativo', youth_profile.contacto_alternativo),
                    _make_field('Situacao atual', youth_profile.get_situacao_atual_display(), keep_empty=True),
                    _make_field('Disponibilidade', youth_profile.get_disponibilidade_display(), keep_empty=True),
                    _make_field('Preferencia', youth_profile.get_preferencia_oportunidade_display(), keep_empty=True),
                    _make_field('Setores de interesse', youth_profile.interesses_setoriais_display),
                    _make_field('Perfil completo', youth_profile.completo, keep_empty=True),
                    _make_field('Perfil validado', youth_profile.validado, keep_empty=True),
                    _make_field('Disponivel para empresas', youth_profile.is_visible_to_companies, keep_empty=True),
                    _make_field('Consentimento SMS', youth_profile.consentimento_sms, keep_empty=True),
                    _make_field('Consentimento WhatsApp', youth_profile.consentimento_whatsapp, keep_empty=True),
                    _make_field('Consentimento email', youth_profile.consentimento_email, keep_empty=True),
                ] if field
            ]
        else:
            youth_fields = []

    elif target_user.is_empresa:
        company_profile = (
            Company.objects.select_related('user', 'distrito')
            .prefetch_related('job_posts__distrito', 'contact_requests__youth__user')
            .filter(user=target_user)
            .first()
        )

        if company_profile:
            company_jobs = company_profile.job_posts.annotate(applications_count=Count('applications'))
            company_applications = (
                Application.objects.select_related('job', 'youth__user')
                .filter(job__company=company_profile)
                .order_by('-created_at')
            )
            company_contact_requests = company_profile.contact_requests.all()

            company_fields = [
                field for field in [
                    _make_field('Nome da empresa', company_profile.nome, keep_empty=True),
                    _make_field('NIF', company_profile.nif),
                    _make_field('Setores de atividade', company_profile.setores_display),
                    _make_field('Telefone', company_profile.telefone),
                    _make_field('Email', company_profile.email),
                    _make_field('Website', company_profile.website),
                    _make_field('Distrito', company_profile.distrito.nome if company_profile.distrito else None),
                    _make_field('Endereco', company_profile.endereco),
                    _make_field('Ativa', company_profile.ativa, keep_empty=True),
                    _make_field('Verificada', company_profile.verificada, keep_empty=True),
                ] if field
            ]
        else:
            company_fields = []
    else:
        youth_fields = []
        company_fields = []

    summary_stats = [
        {'label': 'Perfil', 'value': _display_value(target_user.get_perfil_display())},
        {'label': 'Estado', 'value': _('Ativo') if target_user.is_active else _('Inativo')},
    ]

    if youth_profile:
        summary_stats.extend([
            {'label': 'Formacoes', 'value': len(youth_education)},
            {'label': 'Experiencias', 'value': len(youth_experiences)},
            {'label': 'Documentos', 'value': len(youth_documents)},
            {'label': 'Skills', 'value': len(youth_skills)},
            {'label': 'Candidaturas', 'value': len(youth_applications)},
        ])
    elif company_profile:
        summary_stats.extend([
            {'label': 'Vagas publicadas', 'value': company_profile.total_vagas},
            {'label': 'Vagas ativas', 'value': company_profile.vagas_ativas},
            {'label': 'Candidaturas recebidas', 'value': company_profile.total_candidaturas},
            {'label': 'Pedidos de contacto', 'value': company_contact_requests.count()},
        ])

    context = _with_admin_context(request, {
        'target_user': target_user,
        'next_url': next_url,
        'account_fields': account_fields,
        'summary_stats': summary_stats,
        'youth_profile': youth_profile,
        'youth_fields': youth_fields,
        'youth_education': youth_education,
        'youth_experiences': youth_experiences,
        'youth_documents': youth_documents,
        'youth_skills': youth_skills,
        'youth_applications': youth_applications,
        'youth_contact_requests': youth_contact_requests,
        'company_profile': company_profile,
        'company_fields': company_fields,
        'company_jobs': company_jobs,
        'company_applications': company_applications,
        'company_contact_requests': company_contact_requests,
    })

    return render(request, 'dashboard/user_detail.html', context)


@admin_required
def user_edit(request, pk):
    'Editar dados principais de um utilizador pelo painel admin.'
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
    'Ativar/desativar utilizador'
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
    base_profiles = _profile_progress_queryset().filter(validado=False)

    query = (request.GET.get('q') or '').strip()
    distrito_id = (request.GET.get('distrito') or '').strip()

    filtered_profiles = base_profiles
    if query:
        filtered_profiles = filtered_profiles.filter(
            Q(user__nome__icontains=query) |
            Q(user__telefone__icontains=query) |
            Q(user__email__icontains=query) |
            Q(user__bi_numero__icontains=query)
        )
    if distrito_id:
        filtered_profiles = filtered_profiles.filter(user__distrito_id=distrito_id)

    pending_profiles, incomplete_profiles = _split_validation_profiles(
        base_profiles.order_by('-updated_at', '-created_at')
    )
    perfis, filtered_incomplete_profiles = _split_validation_profiles(
        filtered_profiles.order_by('-updated_at', '-created_at')
    )
    today = timezone.localdate()

    validation_summary = {
        'total_pending': len(pending_profiles),
        'pending_today': sum(1 for profile in pending_profiles if profile.updated_at.date() == today),
        'districts': len({profile.user.distrito_id for profile in pending_profiles if profile.user.distrito_id}),
        'filtered_total': len(perfis),
        'incomplete_profiles': len(incomplete_profiles),
        'incomplete_today': sum(1 for profile in filtered_incomplete_profiles if profile.updated_at.date() == today),
        'minimum_progress': YouthProfile.MINIMUM_APPROVAL_PROGRESS,
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
        if not profile.is_ready_for_approval:
            messages.error(request, profile.approval_progress_message)

            next_url = request.GET.get('next')
            return redirect(next_url or 'dashboard:validate_profiles')

        if profile.is_underage_for_validation:
            Notification.objects.create(
                user=profile.user,
                titulo=_('Perfil pendente por idade minima'),
                mensagem=profile.validation_age_message,
                tipo='ALERTA'
            )

            messages.error(
                request,
                _('Perfil nao pode ser validado: o candidato tem %(age)s anos e a idade minima e %(minimum_age)s.') % {
                    'age': profile.idade,
                    'minimum_age': profile.MINIMUM_VALIDATION_AGE,
                }
            )

            next_url = request.GET.get('next')
            return redirect(next_url or 'dashboard:validate_profiles')

        profile.validado = True
        profile.save()
        
        # Notificar jovem
        if profile.is_visible_to_companies:
            youth_title = _('Perfil validado!')
            youth_message = _('O teu perfil foi validado e esta agora visivel para empresas.')
            admin_message = _('Perfil validado com sucesso!')
        else:
            youth_title = _('Perfil aprovado pelo admin!')
            youth_message = profile.company_visibility_status_message
            admin_message = _(
                'Perfil aprovado com sucesso. O candidato ainda precisa cumprir os requisitos para ficar visivel para empresas.'
            )

        Notification.objects.create(
            user=profile.user,
            titulo=youth_title,
            mensagem=youth_message,
            tipo='SUCESSO'
        )
        
        messages.success(request, admin_message)
    
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
        messages.error(request, _('Ação invalida para o pedido de contacto.'))
    
    next_url = request.GET.get('next')
    return redirect(next_url or 'dashboard:manage_contact_requests')


@admin_required
def offline_registrations(request):
    'Área para gerar e importar registos offline de utilizadores.'
    context = _offline_registrations_context(request)
    return render(request, 'dashboard/offline_registrations.html', context)


@admin_required
def offline_registration_export(request):
    """Gerar ficheiro preenchivel para registo offline."""
    if request.method != 'POST':
        return redirect('dashboard:offline_registrations')

    export_form = OfflineRegistrationExportForm(request.POST)
    import_form = OfflineRegistrationImportForm()
    if not export_form.is_valid():
        context = _offline_registrations_context(
            request,
            export_form=export_form,
            import_form=import_form,
        )
        return render(request, 'dashboard/offline_registrations.html', context)

    profile_type = export_form.cleaned_data['profile_type']
    payload = _build_offline_registration_payload(profile_type, request.user)
    profile_label = 'jovem' if profile_type == User.ProfileType.JOVEM else 'empresa'

    AuditLog.objects.create(
        user=request.user,
        acao='Registo offline exportado',
        payload={
            'profile_type': profile_type,
            'profile_label': profile_label,
        },
        ip_address=_get_client_ip(request),
    )

    document = render_to_string(
        'dashboard/offline_registration_form_document.html',
        {
            'payload': payload,
            'profile_type': profile_type,
            'profile_label': 'Jovem' if profile_type == User.ProfileType.JOVEM else 'Empresa',
            'districts': payload['references']['districts'],
            'sexo_choices': payload['references'].get('sexo_choices', []),
            'situacao_choices': payload['references'].get('situacao_choices', []),
            'disponibilidade_choices': payload['references'].get('disponibilidade_choices', []),
            'preferencia_choices': payload['references'].get('preferencia_choices', []),
            'education_level_choices': payload['references'].get('education_level_choices', []),
            'area_formacao_choices': payload['references'].get('area_formacao_choices', []),
            'setor_choices': payload['references'].get('setor_choices', []),
        },
    )

    filename = f'registo_offline_{profile_label}.html'
    response = HttpResponse(
        document,
        content_type='text/html; charset=utf-8',
    )
    response['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
    return response


@admin_required
def offline_registration_import(request):
    'Importar ficheiro offline e criar o registo do utilizador.'
    if request.method != 'POST':
        return redirect('dashboard:offline_registrations')

    export_form = OfflineRegistrationExportForm()
    import_form = OfflineRegistrationImportForm(request.POST, request.FILES)
    if not import_form.is_valid():
        context = _offline_registrations_context(
            request,
            export_form=export_form,
            import_form=import_form,
        )
        return render(request, 'dashboard/offline_registrations.html', context)

    uploaded_file = import_form.cleaned_data['file']
    try:
        payload = _decode_offline_json(uploaded_file)
        imported_user, imported_label = _import_offline_registration_payload(
            payload,
            request.user,
            uploaded_file.name,
            _get_client_ip(request),
        )
    except ValueError as exc:
        import_form.add_error('file', str(exc))
        context = _offline_registrations_context(
            request,
            export_form=export_form,
            import_form=import_form,
        )
        return render(request, 'dashboard/offline_registrations.html', context)

    messages.success(
        request,
        _('Registo offline importado com sucesso para %(tipo)s "%(nome)s".') % {
            'tipo': imported_label.lower(),
            'nome': imported_user.nome,
        }
    )
    return redirect('dashboard:offline_registrations')


# Relatórios
@admin_required
def _legacy_reports(request):
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
def _legacy_export_report_csv(request):
    """Exportar relatório CSV"""
    start_date, end_date, start_dt, end_dt, invalid_range = _get_date_range(request)
    if invalid_range:
        return HttpResponse(
            'Data final não pode ser menor que a data inicial.',
            status=400,
            content_type='text/plain; charset=utf-8'
        )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatório_base_nacional.csv"'
    
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
def _legacy_export_report_pdf(request):
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
    period_days = (end_date - start_date).days + 1
    period_label = f"Periodo selecionado ({period_days} dia{'s' if period_days != 1 else ''})"

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
        "Relatório - CNJ - Conselho Nacional da Juventude",
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
        ["Indicador", period_label],
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
    response['Content-Disposition'] = 'attachment; filename="relatório_base_nacional.pdf"'
    return response


# API para gráficos
@admin_required
def reports(request):
    """Pagina de relatorios."""

    range_data = _resolve_report_range(request)
    report_data = _build_report_data(range_data)

    if range_data['invalid_range']:
        messages.error(request, _('A data final nao pode ser menor que a data inicial.'))

    period_options = [
        {'key': 'diario', 'label': 'Diario', 'url': f"{reverse('dashboard:reports')}?periodo=diario"},
        {'key': 'quinzenal', 'label': 'Quinzenal', 'url': f"{reverse('dashboard:reports')}?periodo=quinzenal"},
        {'key': 'mensal', 'label': 'Mensal', 'url': f"{reverse('dashboard:reports')}?periodo=mensal"},
        {'key': 'anual', 'label': 'Anual', 'url': f"{reverse('dashboard:reports')}?periodo=anual"},
        {'key': 'personalizado', 'label': 'Personalizado', 'url': reverse('dashboard:reports')},
    ]
    for option in period_options:
        option['active'] = option['key'] == range_data['period_key']

    context = _with_admin_context(request, {
        'data_inicio': range_data['start_date'],
        'data_fim': range_data['end_date'],
        'data_inicio_value': range_data['start_date'].strftime('%Y-%m-%d'),
        'data_fim_value': range_data['end_date'].strftime('%Y-%m-%d'),
        'active_period_key': range_data['period_key'],
        'active_period_label': range_data['period_label'],
        'period_description': range_data['period_description'],
        'report_querystring': range_data['querystring'],
        'period_options': period_options,
        **report_data,
    })
    return render(request, 'dashboard/reports.html', context)


@admin_required
def export_report_csv(request):
    """Exportar relatorio CSV."""
    range_data = _resolve_report_range(request)
    report_data = _build_report_data(range_data)
    if range_data['invalid_range']:
        return HttpResponse(
            'Data final nao pode ser menor que a data inicial.',
            status=400,
            content_type='text/plain; charset=utf-8',
        )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_base_nacional.csv"'

    writer = csv.writer(response)
    writer.writerow(['Resumo executivo'])
    writer.writerow(['Indicador', 'Valor'])
    for label, value in report_data['overview_rows']:
        writer.writerow([label, value])

    writer.writerow([])
    writer.writerow(['Resultados e conversao'])
    writer.writerow(['Indicador', 'Valor'])
    for label, value in report_data['outcome_rows']:
        writer.writerow([label, value])

    writer.writerow([])
    writer.writerow(['Backlog operacional'])
    writer.writerow(['Indicador', 'Valor'])
    for label, value in report_data['snapshot_rows']:
        writer.writerow([label, value])

    writer.writerow([])
    writer.writerow(['Destaques do periodo'])
    writer.writerow(['Leitura', 'Destaque', 'Nota'])
    for label, value, note in report_data['highlight_rows']:
        writer.writerow([label, value, note])

    writer.writerow([])
    writer.writerow(['Jovens no periodo'])
    writer.writerow(['ID', 'Nome', 'Localizacao', 'Data', 'Estado'])
    for profile in report_data['jovens_qs']:
        writer.writerow([
            profile.id,
            profile.nome_completo,
            profile.location_display,
            profile.created_at.strftime('%d/%m/%Y'),
            'Validado' if profile.validado else 'Pendente',
        ])

    writer.writerow([])
    writer.writerow(['Empresas no periodo'])
    writer.writerow(['ID', 'Nome', 'Distrito', 'Data', 'Estado'])
    for company in report_data['empresas_qs']:
        writer.writerow([
            company.id,
            company.nome,
            company.distrito.nome if company.distrito else '',
            company.created_at.strftime('%d/%m/%Y'),
            'Ativa' if company.ativa else 'Inativa',
        ])

    writer.writerow([])
    writer.writerow(['Vagas no periodo'])
    writer.writerow(['ID', 'Titulo', 'Empresa', 'Tipo', 'Data', 'Estado'])
    for job in report_data['vagas_qs']:
        writer.writerow([
            job.id,
            job.titulo,
            job.company.nome,
            job.get_tipo_display(),
            timezone.localtime(job.data_publicacao).strftime('%d/%m/%Y'),
            job.get_estado_display(),
        ])

    writer.writerow([])
    writer.writerow(['Candidaturas no periodo'])
    writer.writerow(['ID', 'Jovem', 'Vaga', 'Empresa', 'Data', 'Estado'])
    for application in report_data['candidaturas_qs']:
        writer.writerow([
            application.id,
            application.youth.user.nome,
            application.job.titulo,
            application.job.company.nome,
            timezone.localtime(application.created_at).strftime('%d/%m/%Y'),
            application.get_estado_display(),
        ])

    writer.writerow([])
    writer.writerow(['Pedidos de contacto no periodo'])
    writer.writerow(['ID', 'Empresa', 'Jovem', 'Data', 'Estado'])
    for contact in report_data['contactos_qs']:
        writer.writerow([
            contact.id,
            contact.company.nome,
            contact.youth.user.nome,
            timezone.localtime(contact.created_at).strftime('%d/%m/%Y'),
            contact.get_estado_display(),
        ])

    return response


@admin_required
def api_stats(request):
    """API para dados estatÃ­sticos (grÃ¡ficos)"""
    
    # Jovens por mÃªs (Ãºltimos 6 meses)
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


@admin_required
def export_report_pdf(request):
    """Exportar relatorio em PDF."""
    range_data = _resolve_report_range(request)
    report_data = _build_report_data(range_data)
    if range_data['invalid_range']:
        return HttpResponse(
            'Data final nao pode ser menor que a data inicial.',
            status=400,
            content_type='text/plain; charset=utf-8',
        )

    def build_chart_data(items, max_items=6):
        labels = []
        values = []
        for nome, total in items[:max_items]:
            labels.append(str(nome))
            values.append(total)
        if len(items) > max_items:
            labels.append('Outros')
            values.append(sum(total for _, total in items[max_items:]))
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
                pdf.drawImage(
                    logo_path,
                    width - margin - 140,
                    height - 54,
                    width=140,
                    height=32,
                    preserveAspectRatio=True,
                    mask='auto',
                )
            except Exception:
                pass
        pdf.setFillColor(colors.HexColor("#1f2d3d"))
        return height - header_height - 24

    def draw_table(data, col_widths, right_align_last=True):
        table = Table(data, colWidths=col_widths)
        styles = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f6fb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2d3d")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#dbe3ef")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        if right_align_last:
            styles.append(("ALIGN", (-1, 1), (-1, -1), "RIGHT"))
        table.setStyle(TableStyle(styles))
        return table

    def draw_table_block(title, headers, rows, y, col_widths, subtitle=None, right_align_last=True):
        if subtitle:
            pdf.setFont("Helvetica", 10)
            pdf.drawString(margin, y, subtitle)
            y -= 18

        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(colors.HexColor("#1f2d3d"))
        pdf.drawString(margin, y, title)
        y -= 12

        table = draw_table([headers] + rows, col_widths, right_align_last=right_align_last)
        _, table_height = table.wrap(0, 0)
        if y - table_height < 60:
            pdf.showPage()
            y = draw_header(title, range_data['period_description'])
            table = draw_table([headers] + rows, col_widths, right_align_last=right_align_last)
            _, table_height = table.wrap(0, 0)
        table.drawOn(pdf, margin, y - table_height)
        return y - table_height - 24

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

    def draw_distribution_section(title, items, y):
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(colors.HexColor("#1f2d3d"))
        pdf.drawString(margin, y, title)
        y -= 12

        table_rows = [[nome, str(total)] for nome, total in items[:10]] or [['Sem dados', '0']]
        table = draw_table([["Categoria", "Total"]] + table_rows, [200, 60])
        _, table_height = table.wrap(0, 0)
        if y - max(table_height, 130) < 60:
            pdf.showPage()
            y = draw_header("Relatorio - Distribuicoes", range_data['period_description'])
            pdf.setFont("Helvetica-Bold", 12)
            pdf.setFillColor(colors.HexColor("#1f2d3d"))
            pdf.drawString(margin, y, title)
            y -= 12
            table = draw_table([["Categoria", "Total"]] + table_rows, [200, 60])
            _, table_height = table.wrap(0, 0)

        table.drawOn(pdf, margin, y - table_height)
        labels, values = build_chart_data(items, max_items=6)
        draw_chart(labels, values, margin + 270, y - 124, 220, 130)
        return y - max(table_height, 130) - 24

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 56

    y = draw_header(
        "Relatorio executivo - CNJ",
        f"Periodo {range_data['period_label']}: {range_data['start_date'].strftime('%d/%m/%Y')} a {range_data['end_date'].strftime('%d/%m/%Y')}",
    )
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#1f2d3d"))
    pdf.drawString(margin, y + 8, f"Gerado em: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 12
    y = draw_table_block(
        "Leitura executiva",
        ["Indicador", "Valor"],
        [[label, value] for label, value in report_data['overview_rows']],
        y,
        [300, 160],
        subtitle=report_data['headline_insight'],
    )
    y = draw_table_block(
        "Resultados e conversao",
        ["Indicador", "Valor"],
        [[label, value] for label, value in report_data['outcome_rows']],
        y,
        [300, 160],
    )

    pdf.showPage()
    y = draw_header("Relatorio - Destaques", range_data['period_description'])
    y = draw_table_block(
        "Destaques mais relevantes",
        ["Leitura", "Destaque", "Nota"],
        [[label, value, note] for label, value, note in report_data['highlight_rows']],
        y,
        [160, 120, 180],
        right_align_last=False,
    )
    y = draw_table_block(
        "Backlog operacional",
        ["Indicador", "Valor"],
        [[label, value] for label, value in report_data['snapshot_rows']],
        y,
        [300, 160],
    )

    pdf.showPage()
    y = draw_header("Relatorio - Distribuicoes", "Panorama por origem e oferta")
    y = draw_distribution_section("Jovens por distrito", report_data['district_list'], y)
    y = draw_distribution_section("Por nivel de educacao", report_data['level_list'], y)
    y = draw_distribution_section("Por area de formacao", report_data['area_list'], y)
    y = draw_distribution_section("Por tipo de vaga", report_data['job_type_list'], y)

    pdf.save()

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_base_nacional.pdf"'
    return response


@admin_required
def _legacy_api_stats(request):
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
