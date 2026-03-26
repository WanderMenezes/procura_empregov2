"""
Views para dashboards (Admin e Técnico)
"""

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
from companies.models import Company, JobPost, Application, ContactRequest
from core.models import AuditLog, District, Notification


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
                    _make_field('Visivel para empresas', youth_profile.visivel, keep_empty=True),
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
