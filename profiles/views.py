"""
Views para perfis de jovens
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.views.generic import View, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse, FileResponse, Http404
from django.db.models import Q, Count, F
from django.core.paginator import Paginator
from datetime import timedelta
from django.conf import settings
from django import forms as django_forms

from accounts.sms import send_sms

from .models import YouthProfile, Education, Experience, Document, YouthSkill
from companies.models import JobPost, Application, ContactRequest
from .forms import (
    YouthProfileStep1Form, YouthProfileStep2Form,
    YouthProfileStep3Form, YouthProfileStep4Form,
    AssistedRegistrationForm, YouthProfileEditForm, YouthSkillsForm,
    EducationForm, ExperienceForm, DocumentForm,
    build_idioma_initial_data, parse_idioma_payload
)
from core.models import District, Skill, Notification, AuditLog
from accounts.models import User
import random
from accounts.models import PhoneChange
from accounts.forms import UserProfileForm
import mimetypes
import os


def get_or_create_skill_by_name(nome, tipo):
    nome = (nome or '').strip()
    if not nome:
        return None
    existing = Skill.objects.filter(nome__iexact=nome).first()
    if existing:
        return existing
    valid_tipos = {choice[0] for choice in Skill.TIPO_CHOICES}
    if tipo not in valid_tipos:
        tipo = 'TEC'
    return Skill.objects.create(nome=nome, tipo=tipo, aprovada=False)


def compute_profile_step_progress(profile: YouthProfile) -> dict:
    """Compute per-step filled/total counts for an existing profile instance.

    Returns dict like {'1': {'filled': int, 'total': int}, ...}
    """
    # expected fields per step (mirror wizard)
    expected = {
        '1': ['nome', 'telefone', 'email', 'contacto_alternativo', 'distrito', 'data_nascimento', 'sexo', 'localidade'],
        '2': ['nivel', 'area_formacao', 'instituicao', 'ano', 'curso', 'skills', 'idiomas'],
        '3': ['situacao_atual', 'disponibilidade', 'interesse_setorial', 'preferencia_oportunidade', 'sobre'],
        '4': ['cv', 'certificado', 'bi', 'visivel', 'consentimento_sms', 'consentimento_whatsapp', 'consentimento_email']
    }

    result = {}

    # helper to fetch education fields
    edu = Education.objects.filter(profile=profile).first()
    docs = Document.objects.filter(profile=profile)
    skills_qs = YouthSkill.objects.filter(profile=profile)

    always_count_bool = {
        'visivel',
        'consentimento_sms',
        'consentimento_whatsapp',
        'consentimento_email',
    }

    for step, fields in expected.items():
        total = len(fields)
        filled = 0
        for f in fields:
            val = None
            if step == '1':
                if f == 'nome':
                    val = getattr(profile.user, 'nome', '')
                elif f == 'telefone':
                    val = getattr(profile.user, 'telefone', '')
                elif f == 'email':
                    val = getattr(profile.user, 'email', '')
                elif f == 'distrito':
                    val = getattr(profile.user, 'distrito', None)
                elif f == 'data_nascimento':
                    val = getattr(profile, 'data_nascimento', None)
                elif f == 'sexo':
                    val = getattr(profile, 'sexo', '')
                elif f == 'localidade':
                    val = getattr(profile, 'localidade', '')
                elif f == 'contacto_alternativo':
                    val = getattr(profile, 'contacto_alternativo', '')
            elif step == '2':
                if f == 'skills':
                    val = skills_qs.exists()
                elif f == 'idiomas':
                    val = bool(profile.idiomas_detalhados)
                else:
                    if edu:
                        val = getattr(edu, f, None)
                    else:
                        val = None
            elif step == '3':
                val = getattr(profile, f, None)
            elif step == '4':
                if f == 'cv':
                    val = docs.filter(tipo='CV').exists()
                elif f == 'certificado':
                    val = docs.filter(tipo='CERT').exists()
                elif f == 'bi':
                    val = docs.filter(tipo='BI').exists()
                elif f == 'visivel':
                    val = getattr(profile, 'visivel', False)
                elif f == 'consentimento_sms':
                    val = getattr(profile, 'consentimento_sms', False)
                elif f == 'consentimento_whatsapp':
                    val = getattr(profile, 'consentimento_whatsapp', False)
                elif f == 'consentimento_email':
                    val = getattr(profile, 'consentimento_email', False)

            if isinstance(val, bool):
                if f in always_count_bool:
                    # For consent/visibility toggles, any choice counts as answered.
                    filled += 1
                elif val:
                    filled += 1
            elif isinstance(val, (list, tuple)):
                if len(val) > 0:
                    filled += 1
            elif val not in (None, '', False):
                filled += 1

        missing = total - filled
        if missing < 0:
            missing = 0

        result[step] = {'filled': filled, 'total': total, 'missing': missing}

    return result


class ProfileWizardView(View):
    """Wizard de 4 passos para criar perfil do jovem"""
    
    template_name = 'profiles/wizard.html'
    STEP_META = {
        1: {'title': 'Dados Pessoais', 'icon': 'bi-person'},
        2: {'title': 'Educação, Skills e Idiomas', 'icon': 'bi-book'},
        3: {'title': 'Experiência e Interesses', 'icon': 'bi-briefcase'},
        4: {'title': 'Documentos e Consentimentos', 'icon': 'bi-file-earmark'},
    }

    def _build_context(self, request, form, step, progress, step_stats, step_map):
        step_meta = self._get_step_meta(step)
        wizard_steps = []
        for number in range(1, 5):
            item_stats = step_map.get(str(number), {'filled': 0, 'total': 0})
            wizard_steps.append({
                'number': number,
                'title': self.STEP_META.get(number, {}).get('title', ''),
                'icon': self.STEP_META.get(number, {}).get('icon', ''),
                'filled': item_stats['filled'],
                'total': item_stats['total'],
                'active': step == number,
                'completed': step > number,
            })

        return {
            'form': form,
            'step': step,
            'progress': progress,
            'total_steps': 4,
            'step_stats': step_stats,
            'step_title': step_meta['title'],
            'step_icon': step_meta['icon'],
            'wizard_steps': wizard_steps,
            'is_editing_profile': request.user.has_youth_profile(),
        }

    def _get_step_meta(self, step: int) -> dict:
        return self.STEP_META.get(step, {'title': '', 'icon': ''})

    def _profile_to_wizard_data(self, profile: YouthProfile) -> dict:
        user = profile.user
        edu = Education.objects.filter(profile=profile).order_by('-ano').first()
        exp = Experience.objects.filter(profile=profile).order_by('-inicio').first()
        skills_ids = list(YouthSkill.objects.filter(profile=profile).values_list('skill_id', flat=True))
        docs = Document.objects.filter(profile=profile)

        def to_date(value):
            if not value:
                return ''
            return value.isoformat() if hasattr(value, 'isoformat') else str(value)

        interesse = profile.interesse_setorial or []
        if isinstance(interesse, str):
            interesse = [interesse]

        step1 = {
            'nome': user.nome or '',
            'telefone': user.telefone or '',
            'email': user.email or '',
            'distrito': user.distrito_id or '',
            'data_nascimento': to_date(profile.data_nascimento),
            'sexo': profile.sexo or '',
            'localidade': profile.localidade or '',
            'contacto_alternativo': profile.contacto_alternativo or '',
        }

        step2 = {
            'nivel': edu.nivel if edu else '',
            'area_formacao': edu.area_formacao if edu else '',
            'instituicao': edu.instituicao if edu else '',
            'ano': edu.ano if edu else '',
            'curso': edu.curso if edu else '',
            'skills': skills_ids,
            'outra_skill_nome': '',
            'outra_skill_tipo': ''
        }
        step2.update(build_idioma_initial_data(profile.idiomas))

        step3 = {
            'situacao_atual': profile.situacao_atual or '',
            'disponibilidade': profile.disponibilidade or '',
            'interesse_setorial': interesse,
            'preferencia_oportunidade': profile.preferencia_oportunidade or '',
            'sobre': profile.sobre or '',
            'tem_experiencia': bool(exp),
            'exp_entidade': exp.entidade if exp else '',
            'exp_cargo': exp.cargo if exp else '',
            'exp_descricao': exp.descricao if exp else '',
            'exp_inicio': to_date(exp.inicio) if exp else '',
            'exp_fim': to_date(exp.fim) if exp and exp.fim else '',
            'exp_atual': exp.atual if exp else False,
        }

        step4 = {
            'visivel': profile.visivel,
            'consentimento_sms': profile.consentimento_sms,
            'consentimento_whatsapp': profile.consentimento_whatsapp,
            'consentimento_email': profile.consentimento_email,
        }
        if docs.filter(tipo='CV').exists():
            step4['cv'] = True
        if docs.filter(tipo='CERT').exists():
            step4['certificado'] = True
        if docs.filter(tipo='BI').exists():
            step4['bi'] = True

        return {'1': step1, '2': step2, '3': step3, '4': step4}
    
    def get(self, request, step=1):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if not request.user.is_jovem:
            messages.error(request, _('Apenas jovens podem criar perfil.'))
            return redirect('home')
        
        profile = request.user.youth_profile if request.user.has_youth_profile() else None
        wizard_data = request.session.get('wizard_data', {})
        if profile and (not wizard_data or request.GET.get('reset') == '1'):
            wizard_data = self._profile_to_wizard_data(profile)
            request.session['wizard_data'] = wizard_data
        
        step = int(step)
        if step < 1 or step > 4:
            step = 1
        
        # Carregar dados salvos do wizard + defaults do utilizador
        initial = {}
        if step == 1:
            initial = {
                'nome': request.user.nome,
                'telefone': request.user.telefone,
                'email': request.user.email,
                'distrito': request.user.distrito_id,
            }
        elif step == 4:
            initial = {
                'visivel': request.user.consentimento_dados,
                'consentimento_sms': request.user.consentimento_contacto,
                'consentimento_whatsapp': request.user.consentimento_contacto,
                'consentimento_email': request.user.consentimento_contacto,
            }
        if str(step) in wizard_data:
            initial.update(wizard_data[str(step)])

        form = self.get_form_for_step(step, initial=initial if initial else None)
        
        # calcular progresso real com base nos dados guardados na sessão
        wizard_data = request.session.get('wizard_data', {})
        progress = self.compute_progress(wizard_data)

        step_map = self.compute_step_progress(wizard_data)
        step_stats = step_map.get(str(step), {'filled': 0, 'total': 0})
        context = self._build_context(request, form, step, progress, step_stats, step_map)
        
        return render(request, self.template_name, context)
    
    def post(self, request, step=1):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        step = int(step)
        form = self.get_form_for_step(step, data=request.POST, files=request.FILES)

        is_autosave = 'autosave' in request.POST
        if is_autosave:
            wizard_data = request.session.get('wizard_data', {})
            if form.is_valid():
                wizard_data[str(step)] = self.get_form_data(form)
            else:
                wizard_data[str(step)] = self.get_raw_form_data(form, request)
            request.session['wizard_data'] = wizard_data
            progress = self.compute_progress(wizard_data)
            step_stats = self.compute_step_progress(wizard_data).get(str(step), {'filled': 0, 'total': 0})
            return JsonResponse({
                'saved': True,
                'progress': progress,
                'step_filled': step_stats['filled'],
                'step_total': step_stats['total']
            })

        if form.is_valid():
            # Salvar dados na sessão
            wizard_data = request.session.get('wizard_data', {})
            wizard_data[str(step)] = self.get_form_data(form)
            request.session['wizard_data'] = wizard_data
            
            if 'next' in request.POST and step < 4:
                return redirect('profiles:wizard_step', step=step + 1)
            elif 'prev' in request.POST and step > 1:
                return redirect('profiles:wizard_step', step=step - 1)
            elif 'save' in request.POST:
                # Salvar rascunho
                messages.success(request, _('Progresso guardado! Podes continuar depois.'))
                return redirect('home')
            elif 'submit' in request.POST and step == 4:
                # Submeter perfil completo
                return self.submit_profile(request)
        
        wizard_data = request.session.get('wizard_data', {})
        progress = self.compute_progress(wizard_data)

        step_map = self.compute_step_progress(wizard_data)
        step_stats = step_map.get(str(step), {'filled': 0, 'total': 0})
        context = self._build_context(request, form, step, progress, step_stats, step_map)
        
        return render(request, self.template_name, context)
    
    def get_form_for_step(self, step, data=None, files=None, initial=None):
        """Retorna o formulário apropriado para cada passo"""
        forms = {
            1: YouthProfileStep1Form,
            2: YouthProfileStep2Form,
            3: YouthProfileStep3Form,
            4: YouthProfileStep4Form
        }
        
        form_class = forms.get(step, YouthProfileStep1Form)
        
        if data:
            return form_class(data, files)
        elif initial:
            return form_class(initial=initial)
        return form_class()
    
    def get_form_data(self, form):
        """Extrai dados limpos do formulário"""
        data = {}
        for field_name, field in form.fields.items():
            value = form.cleaned_data.get(field_name)
            if value is not None:
                # Converter objetos para IDs serializáveis
                if isinstance(value, bool):
                    data[field_name] = value
                elif isinstance(value, (list, tuple)):
                    data[field_name] = list(value)
                elif hasattr(value, 'pk'):
                    data[field_name] = value.pk
                elif hasattr(value, 'all'):  # ManyToMany
                    data[field_name] = [item.pk for item in value.all()]
                else:
                    data[field_name] = str(value) if value else ''
        return data

    def get_raw_form_data(self, form, request):
        """Extrai dados brutos do POST para autosave, mesmo com validação incompleta."""
        data = {}
        for field_name, field in form.fields.items():
            if field_name in request.FILES:
                continue
            if isinstance(field, (django_forms.ModelMultipleChoiceField, django_forms.MultipleChoiceField)):
                data[field_name] = request.POST.getlist(field_name)
            elif isinstance(field, django_forms.BooleanField):
                data[field_name] = 'on' if field_name in request.POST else ''
            else:
                data[field_name] = request.POST.get(field_name, '')
        return data

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, int):
            return value == 1
        return str(value).lower() in ('1', 'true', 'sim', 'yes', 'on')

    def compute_progress(self, wizard_data: dict) -> int:
        """Calcular percentagem de conclusão com base nos campos preenchidos no wizard."""
        step_map = self.compute_step_progress(wizard_data)
        total = sum(s.get('total', 0) for s in step_map.values())
        filled = sum(s.get('filled', 0) for s in step_map.values())

        if total == 0:
            return 0
        return int((filled / total) * 100)

    def compute_step_progress(self, wizard_data: dict) -> dict:
        """Return a dict mapping step -> {'filled': int, 'total': int} based on expected fields."""
        expected = {
            '1': ['nome', 'telefone', 'email', 'contacto_alternativo', 'distrito', 'data_nascimento', 'sexo', 'localidade'],
            '2': ['nivel', 'area_formacao', 'instituicao', 'ano', 'curso', 'skills', 'idiomas'],
            '3': ['situacao_atual', 'disponibilidade', 'interesse_setorial', 'preferencia_oportunidade', 'sobre'],
            '4': ['cv', 'certificado', 'bi', 'visivel', 'consentimento_sms', 'consentimento_whatsapp', 'consentimento_email']
        }

        always_count_bool = {
            'visivel',
            'consentimento_sms',
            'consentimento_whatsapp',
            'consentimento_email',
        }

        result = {}
        for step, fields in expected.items():
            total = len(fields)
            filled = 0
            step_data = wizard_data.get(step, {})
            for f in fields:
                if f == 'idiomas':
                    payload = parse_idioma_payload(step_data.get('idiomas_data'))
                    if payload:
                        filled += 1
                        continue
                    has_partial_idioma = any(
                        step_data.get(f'idioma_{index}_nome') or step_data.get(f'idioma_{index}_dominio')
                        for index in range(1, 5)
                    )
                    if has_partial_idioma:
                        filled += 1
                    continue
                val = step_data.get(f)
                if isinstance(val, bool):
                    if f in always_count_bool:
                        filled += 1
                    elif val:
                        filled += 1
                elif isinstance(val, list):
                    if len(val) > 0:
                        filled += 1
                elif val not in (None, '', False):
                    filled += 1
            result[step] = {'filled': filled, 'total': total}
        return result
    
    def submit_profile(self, request):
        """Cria o perfil completo do jovem"""
        wizard_data = request.session.get('wizard_data', {})
        
        try:
            step1 = wizard_data.get('1', {})
            step2 = wizard_data.get('2', {})
            step3 = wizard_data.get('3', {})
            step4 = wizard_data.get('4', {})
            idiomas = parse_idioma_payload(step2.get('idiomas_data'))

            visivel = self._to_bool(step4.get('visivel', True))
            consentimento_sms = self._to_bool(step4.get('consentimento_sms'))
            consentimento_whatsapp = self._to_bool(step4.get('consentimento_whatsapp'))
            consentimento_email = self._to_bool(step4.get('consentimento_email'))

            # Atualizar dados do utilizador
            user = request.user
            if step1.get('nome'):
                user.nome = step1.get('nome')
            if 'email' in step1:
                user.email = step1.get('email') or ''
            if 'distrito' in step1:
                user.distrito_id = step1.get('distrito') or None
            user.consentimento_dados = visivel
            user.consentimento_contacto = consentimento_sms or consentimento_whatsapp or consentimento_email
            if user.consentimento_dados or user.consentimento_contacto:
                user.data_consentimento = timezone.now()
            user.save()

            profile = user.youth_profile if user.has_youth_profile() else None
            editing = profile is not None
            validation_revoked_for_age = False
            disabled_company_contacts = 0

            if editing:
                was_validated = profile.validado
                if was_validated:
                    disabled_company_contacts = profile.contact_requests.filter(estado='APROVADO').count()
                profile.data_nascimento = step1.get('data_nascimento')
                profile.sexo = step1.get('sexo') or ''
                profile.localidade = step1.get('localidade') or ''
                profile.contacto_alternativo = step1.get('contacto_alternativo', '') or ''
                profile.situacao_atual = step3.get('situacao_atual', profile.situacao_atual)
                profile.disponibilidade = step3.get('disponibilidade', profile.disponibilidade)
                profile.interesse_setorial = step3.get('interesse_setorial')
                profile.preferencia_oportunidade = step3.get('preferencia_oportunidade', profile.preferencia_oportunidade)
                profile.sobre = step3.get('sobre', '') or ''
                profile.idiomas = idiomas
                profile.visivel = visivel
                profile.consentimento_sms = consentimento_sms
                profile.consentimento_whatsapp = consentimento_whatsapp
                profile.consentimento_email = consentimento_email
                profile.completo = True
                profile.wizard_step = 4
                profile.save()

                if was_validated:
                    profile.refresh_from_db()
                    if profile.is_underage_for_validation:
                        validation_revoked_for_age = True
            else:
                profile = YouthProfile.objects.create(
                    user=user,
                    data_nascimento=step1.get('data_nascimento'),
                    sexo=step1.get('sexo'),
                    localidade=step1.get('localidade'),
                    contacto_alternativo=step1.get('contacto_alternativo', ''),
                    situacao_atual=step3.get('situacao_atual', 'DES'),
                    disponibilidade=step3.get('disponibilidade', 'SIM'),
                    interesse_setorial=step3.get('interesse_setorial'),
                    preferencia_oportunidade=step3.get('preferencia_oportunidade', 'EMP'),
                    sobre=step3.get('sobre', ''),
                    idiomas=idiomas,
                    visivel=visivel,
                    consentimento_sms=consentimento_sms,
                    consentimento_whatsapp=consentimento_whatsapp,
                    consentimento_email=consentimento_email,
                    completo=True,
                    wizard_step=4
                )

            # Educação (atualiza ou cria)
            edu_fields = ['nivel', 'area_formacao', 'instituicao', 'ano', 'curso']
            edu_data_present = any(step2.get(f) for f in edu_fields)
            edu = Education.objects.filter(profile=profile).order_by('-ano').first()
            if edu_data_present:
                if edu:
                    if step2.get('nivel'):
                        edu.nivel = step2.get('nivel')
                    if 'area_formacao' in step2:
                        edu.area_formacao = step2.get('area_formacao') or edu.area_formacao
                    if step2.get('instituicao'):
                        edu.instituicao = step2.get('instituicao')
                    if step2.get('ano'):
                        edu.ano = step2.get('ano')
                    if 'curso' in step2:
                        edu.curso = step2.get('curso') or ''
                    edu.save()
                elif step2.get('nivel') and step2.get('instituicao'):
                    Education.objects.create(
                        profile=profile,
                        nivel=step2['nivel'],
                        area_formacao=step2.get('area_formacao', ''),
                        instituicao=step2['instituicao'],
                        ano=step2.get('ano'),
                        curso=step2.get('curso', '')
                    )

            # Skills (sincronizar selecao)
            skills_ids = step2.get('skills', []) or []
            if isinstance(skills_ids, str):
                skills_ids = [skills_ids]
            selected_ids = set()
            for sid in skills_ids:
                try:
                    selected_ids.add(int(sid))
                except (TypeError, ValueError):
                    continue

            existing_skills = YouthSkill.objects.filter(profile=profile)
            existing_ids = set(existing_skills.values_list('skill_id', flat=True))
            to_remove = existing_ids - selected_ids
            if to_remove:
                existing_skills.filter(skill_id__in=to_remove).delete()
            to_add = selected_ids - existing_ids
            for skill_id in to_add:
                try:
                    skill = Skill.objects.get(pk=skill_id)
                    YouthSkill.objects.create(profile=profile, skill=skill, nivel=1)
                except Skill.DoesNotExist:
                    pass

            outra_skill_nome = step2.get('outra_skill_nome', '')
            outra_skill_tipo = step2.get('outra_skill_tipo')
            nova_skill = get_or_create_skill_by_name(outra_skill_nome, outra_skill_tipo)
            if nova_skill:
                YouthSkill.objects.get_or_create(profile=profile, skill=nova_skill, defaults={'nivel': 1})

            # Experiência (atualiza ou cria)
            if self._to_bool(step3.get('tem_experiencia')) and step3.get('exp_entidade') and step3.get('exp_inicio'):
                exp_atual = self._to_bool(step3.get('exp_atual'))
                exp_fim = step3.get('exp_fim') if not exp_atual else None
                exp = Experience.objects.filter(profile=profile).order_by('-inicio').first()
                if exp:
                    exp.entidade = step3['exp_entidade']
                    exp.cargo = step3.get('exp_cargo', '')
                    exp.descricao = step3.get('exp_descricao', '')
                    exp.inicio = step3.get('exp_inicio')
                    exp.fim = exp_fim
                    exp.atual = exp_atual
                    exp.save()
                else:
                    Experience.objects.create(
                        profile=profile,
                        entidade=step3['exp_entidade'],
                        cargo=step3.get('exp_cargo', ''),
                        descricao=step3.get('exp_descricao', ''),
                        inicio=step3.get('exp_inicio'),
                        fim=exp_fim,
                        atual=exp_atual
                    )

            # Processar documentos (substituir se existir)
            def upsert_doc(tipo, nome, file_key):
                if file_key not in request.FILES:
                    return
                doc = Document.objects.filter(profile=profile, tipo=tipo).order_by('-created_at').first()
                if doc:
                    doc.arquivo = request.FILES[file_key]
                    doc.nome = nome
                    doc.verificado = False
                    doc.save()
                else:
                    Document.objects.create(
                        profile=profile,
                        tipo=tipo,
                        nome=nome,
                        arquivo=request.FILES[file_key]
                    )

            upsert_doc('CV', 'Curriculum Vitae', 'cv')
            upsert_doc('CERT', 'Certificado', 'certificado')
            upsert_doc('BI', 'Bilhete de Identidade', 'bi')
            
            # Limpar sessão
            if 'wizard_data' in request.session:
                del request.session['wizard_data']
            
            # Notificação
            if profile.is_underage_for_validation:
                if validation_revoked_for_age:
                    title = _('Validacao removida por idade')
                    message = str(_('O teu perfil foi atualizado, mas a validacao anterior foi removida automaticamente. ')) + profile.validation_age_message
                    if disabled_company_contacts == 1:
                        message += str(_(' Tambem desativamos 1 acesso de empresa ao teu contacto.'))
                    elif disabled_company_contacts > 1:
                        message += str(_(' Tambem desativamos %(count)s acessos de empresas ao teu contacto.')) % {
                            'count': disabled_company_contacts,
                        }
                elif editing:
                    title = _('Perfil atualizado com restricao de idade')
                    message = str(_('O teu perfil foi atualizado. ')) + profile.validation_age_message
                else:
                    title = _('Perfil criado com restricao de idade')
                    message = str(_('O teu perfil foi criado. ')) + profile.validation_age_message

                Notification.objects.create(
                    user=request.user,
                    titulo=title,
                    mensagem=message,
                    tipo='ALERTA'
                )
                messages.warning(request, message)
            elif editing:
                Notification.objects.create(
                    user=request.user,
                    titulo=_('Perfil atualizado com sucesso!'),
                    mensagem=_('O teu perfil foi atualizado e está pronto para novas oportunidades.'),
                    tipo='SUCESSO'
                )
                messages.success(request, _('Perfil atualizado com sucesso!'))
            else:
                Notification.objects.create(
                    user=request.user,
                    titulo=_('Perfil criado com sucesso!'),
                    mensagem=_('O teu perfil está completo e visível para empresas. Boa sorte nas oportunidades!'),
                    tipo='SUCESSO'
                )
                messages.success(request, _('Perfil criado com sucesso!'))
            return redirect('profiles:detail')
            
        except Exception as e:
            messages.error(request, _('Erro ao guardar perfil: {}').format(str(e)))
            return redirect('profiles:wizard_step', step=4)


@login_required
def profile_detail(request):
    """View para visualizar perfil do jovem"""
    if not request.user.is_jovem:
        messages.error(request, _('Apenas jovens têm este tipo de perfil.'))
        return redirect('home')
    
    if not request.user.has_youth_profile():
        return redirect('profiles:wizard')
    
    profile = request.user.youth_profile
    
    # compute progress and per-step stats
    step_stats = compute_profile_step_progress(profile)
    total_filled = sum(s['filled'] for s in step_stats.values())
    total_slots = sum(s['total'] for s in step_stats.values())
    progress = int((total_filled / total_slots) * 100) if total_slots else 0

    # document-only stats for sidebar display
    docs_qs = Document.objects.filter(profile=profile)
    doc_filled = 0
    if docs_qs.filter(tipo='CV').exists():
        doc_filled += 1
    if docs_qs.filter(tipo='CERT').exists():
        doc_filled += 1
    if docs_qs.filter(tipo='BI').exists():
        doc_filled += 1
    doc_total = 3
    doc_missing = doc_total - doc_filled
    if doc_missing < 0:
        doc_missing = 0
    doc_stats = {
        'filled': doc_filled,
        'total': doc_total,
        'missing': doc_missing,
        'total_all': docs_qs.count()
    }

    # vagas disponíveis para candidatura (com filtros e paginação)
    vagas_qs = JobPost.objects.filter(
        estado='ATIVA'
    ).select_related('company', 'distrito').order_by('-data_publicacao')

    q = (request.GET.get('q') or '').strip()
    q = (request.GET.get('q') or '').strip()
    q = (request.GET.get('q') or '').strip()
    q = (request.GET.get('q') or '').strip()
    q = (request.GET.get('q') or '').strip()
    tipo = request.GET.get('tipo')
    distrito = request.GET.get('distrito')
    area = request.GET.get('area')

    valid_tipos = {choice[0] for choice in JobPost.TIPO_CHOICES}
    valid_areas = {choice[0] for choice in settings.AREAS_FORMACAO}

    if q:
        vagas_qs = vagas_qs.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q))
    if q:
        vagas_qs = vagas_qs.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q))
    if q:
        vagas_qs = vagas_qs.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q))
    if q:
        vagas_qs = vagas_qs.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q))
    if q:
        vagas_qs = vagas_qs.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q))
    if tipo in valid_tipos:
        vagas_qs = vagas_qs.filter(tipo=tipo)
    if distrito and distrito.isdigit():
        vagas_qs = vagas_qs.filter(distrito_id=int(distrito))
    if area in valid_areas:
        vagas_qs = vagas_qs.filter(area_formacao=area)

    vagas_qs = vagas_qs.annotate(
        aceites=Count('applications', filter=Q(applications__estado='ACEITE'), distinct=True)
    ).filter(aceites__lt=F('numero_vagas'))

    paginator = Paginator(vagas_qs, 6)
    page_number = request.GET.get('page') or 1
    vagas_page = paginator.get_page(page_number)

    applications = Application.objects.filter(youth=profile).select_related('job')
    candidaturas_ids = list(applications.values_list('job_id', flat=True))
    candidaturas_map = {app.job_id: app.get_estado_display() for app in applications}
    candidaturas_state = {app.job_id: app.estado for app in applications}

    filters = request.GET.copy()
    if 'page' in filters:
        del filters['page']
    filters_qs = filters.urlencode()

    applications = Application.objects.filter(
        youth=profile
    ).select_related('job', 'job__company').prefetch_related('messages').order_by('-created_at')

    context = {
        'profile': profile,
        'education': profile.get_education(),
        'experiences': profile.get_experience(),
        'documents': profile.get_documents(),
        'skills': profile.youth_skills.select_related('skill').all(),
        'progress': progress,
        'step_stats': step_stats,
        'doc_stats': doc_stats,
        'applications': applications,
        'vagas_page': vagas_page,
        'candidaturas_ids': candidaturas_ids,
        'candidaturas_map': candidaturas_map,
        'candidaturas_state': candidaturas_state,
        'tipo_choices': JobPost.TIPO_CHOICES,
        'areas_formacao': settings.AREAS_FORMACAO,
        'filters_qs': filters_qs,
        'selected_tipo': tipo or '',
        'selected_distrito': distrito or '',
        'selected_area': area or '',
        'selected_query': q
    }
    
    return render(request, 'profiles/detail.html', context)


@login_required
def available_jobs(request):
    """Página de vagas disponíveis para jovens"""
    if not request.user.is_jovem:
        messages.error(request, _('Apenas jovens podem aceder.'))
        return redirect('home')

    if not request.user.has_youth_profile():
        return redirect('profiles:wizard')

    profile = request.user.youth_profile
    area_mapping = dict(settings.AREAS_FORMACAO)
    valid_tipos = {choice[0] for choice in JobPost.TIPO_CHOICES}
    valid_areas = {choice[0] for choice in settings.AREAS_FORMACAO}

    interests = profile.interesse_setorial or []
    if isinstance(interests, str):
        interests = [interests] if interests else []
    elif not isinstance(interests, list):
        interests = list(interests)

    preferred_tipo = profile.preferencia_oportunidade if profile.preferencia_oportunidade in valid_tipos else ''
    latest_education = Education.objects.filter(profile=profile).order_by('-ano', '-id').first()
    education_area = latest_education.area_formacao if latest_education else ''
    district_id = request.user.distrito_id
    now = timezone.now()
    today = timezone.localdate()

    available_jobs_qs = JobPost.objects.filter(
        estado='ATIVA'
    ).select_related('company', 'company__distrito', 'distrito').annotate(
        aceites=Count('applications', filter=Q(applications__estado='ACEITE'), distinct=True)
    ).filter(aceites__lt=F('numero_vagas')).order_by('-data_publicacao')

    vagas_qs = available_jobs_qs

    q = (request.GET.get('q') or '').strip()
    tipo = request.GET.get('tipo')
    distrito = request.GET.get('distrito')
    area = request.GET.get('area')

    if q:
        vagas_qs = vagas_qs.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q))
    if tipo in valid_tipos:
        vagas_qs = vagas_qs.filter(tipo=tipo)
    if distrito and distrito.isdigit():
        vagas_qs = vagas_qs.filter(distrito_id=int(distrito))
    if area in valid_areas:
        vagas_qs = vagas_qs.filter(area_formacao=area)

    paginator = Paginator(vagas_qs, 9)
    page_number = request.GET.get('page') or 1
    vagas_page = paginator.get_page(page_number)

    applications = Application.objects.filter(youth=profile).select_related('job', 'job__company')
    candidaturas_ids = list(applications.values_list('job_id', flat=True))
    candidaturas_map = {app.job_id: app.get_estado_display() for app in applications}
    candidaturas_state = {app.job_id: app.estado for app in applications}

    filters = request.GET.copy()
    if 'page' in filters:
        del filters['page']
    filters_qs = filters.urlencode()

    recommended_query = Q()
    if district_id:
        recommended_query |= Q(distrito_id=district_id)
    if preferred_tipo:
        recommended_query |= Q(tipo=preferred_tipo)
    if interests:
        recommended_query |= Q(area_formacao__in=interests)
    elif education_area:
        recommended_query |= Q(area_formacao=education_area)

    active_filter_count = sum(
        1 for value in [
            q,
            tipo if tipo in valid_tipos else '',
            distrito if distrito and distrito.isdigit() else '',
            area if area in valid_areas else '',
        ] if value
    )

    total_available_jobs = available_jobs_qs.count()
    filtered_jobs_count = vagas_qs.count()
    recommended_jobs_count = available_jobs_qs.filter(recommended_query).distinct().count() if recommended_query else total_available_jobs
    local_jobs_count = available_jobs_qs.filter(distrito_id=district_id).count() if district_id else 0
    recent_jobs_count = available_jobs_qs.filter(data_publicacao__gte=now - timedelta(days=7)).count()
    closing_soon_count = available_jobs_qs.filter(
        data_fecho__isnull=False,
        data_fecho__gte=today,
        data_fecho__lte=today + timedelta(days=7)
    ).count()

    for vaga in vagas_page.object_list:
        reasons = []
        if district_id and vaga.distrito_id == district_id:
            reasons.append('No teu distrito')
        if preferred_tipo and vaga.tipo == preferred_tipo:
            reasons.append('Combina com a tua preferencia')
        if vaga.area_formacao and vaga.area_formacao in interests:
            reasons.append('Dentro dos teus interesses')
        elif vaga.area_formacao and education_area and vaga.area_formacao == education_area:
            reasons.append('Relacionada com a tua formação')

        vaga.match_reasons = reasons[:3]
        vaga.match_score = len(reasons)
        vaga.is_new = vaga.data_publicacao >= now - timedelta(days=7)
        vaga.area_label = area_mapping.get(vaga.area_formacao, '')
        vaga.company_initials = ''.join(part[0] for part in (vaga.company.nome or '').split()[:2] if part).upper() or 'EM'
        if vaga.data_fecho:
            vaga.days_until_close = (vaga.data_fecho - today).days
            vaga.is_closing_soon = 0 <= vaga.days_until_close <= 7
        else:
            vaga.days_until_close = None
            vaga.is_closing_soon = False

    context = {
        'profile': profile,
        'districts': District.objects.order_by('nome'),
        'vagas_page': vagas_page,
        'candidaturas_ids': candidaturas_ids,
        'candidaturas_map': candidaturas_map,
        'candidaturas_state': candidaturas_state,
        'tipo_choices': JobPost.TIPO_CHOICES,
        'areas_formacao': settings.AREAS_FORMACAO,
        'filters_qs': filters_qs,
        'selected_tipo': tipo or '',
        'selected_distrito': distrito or '',
        'selected_area': area or '',
        'selected_query': q,
        'active_filter_count': active_filter_count,
        'has_active_filters': active_filter_count > 0,
        'total_available_jobs': total_available_jobs,
        'filtered_jobs_count': filtered_jobs_count,
        'applied_jobs_count': applications.count(),
        'recommended_jobs_count': recommended_jobs_count,
        'local_jobs_count': local_jobs_count,
        'recent_jobs_count': recent_jobs_count,
        'closing_soon_count': closing_soon_count,
        'profile_interest_count': len(interests),
        'profile_interests_display': profile.interesses_setoriais_display,
        'preferred_tipo_display': dict(JobPost.TIPO_CHOICES).get(preferred_tipo, ''),
        'education_area_display': area_mapping.get(education_area, ''),
    }

    return render(request, 'profiles/vagas_disponiveis.html', context)


@login_required
def profile_edit(request):
    """View para editar perfil do jovem"""
    if not request.user.is_jovem:
        messages.error(request, _('Apenas jovens podem editar este perfil.'))
        return redirect('home')

    return redirect('profiles:wizard')


@login_required
def application_messages(request, pk):
    """Histórico de mensagens de uma candidatura (jovem)"""
    if not request.user.is_jovem:
        messages.error(request, _('Apenas jovens podem aceder.'))
        return redirect('home')

    if not request.user.has_youth_profile():
        return redirect('profiles:wizard')

    profile = request.user.youth_profile
    application = get_object_or_404(
        Application.objects.select_related('job', 'job__company', 'job__distrito', 'youth__user'),
        pk=pk,
        youth=profile
    )

    messages_qs = application.messages.all().order_by('-created_at')
    paginator = Paginator(messages_qs, 10)
    page_number = request.GET.get('page') or 1
    messages_page = paginator.get_page(page_number)

    message_count = messages_qs.count()
    company_message_count = messages_qs.filter(sender='EMP').count()
    system_message_count = messages_qs.filter(sender='SYS').count()
    latest_message = messages_qs.first()
    oldest_message = messages_qs.order_by('created_at').first()
    application.company_initials = ''.join(
        part[0] for part in (application.job.company.nome or '').split()[:2] if part
    ).upper() or 'EM'

    context = {
        'application': application,
        'messages_page': messages_page,
        'message_count': message_count,
        'company_message_count': company_message_count,
        'system_message_count': system_message_count,
        'latest_message': latest_message,
        'oldest_message': oldest_message,
    }

    return render(request, 'profiles/application_messages.html', context)


# Views para Educação
@login_required
def education_add(request):
    """Adicionar formação"""
    if not request.user.has_youth_profile():
        return redirect('profiles:wizard')
    
    profile = request.user.youth_profile
    education_qs = profile.get_education()
    latest_education = education_qs.first()

    if request.method == 'POST':
        form = EducationForm(request.POST)
        if form.is_valid():
            education = form.save(commit=False)
            education.profile = profile
            education.save()
            messages.success(request, _('Formação adicionada!'))
            return redirect('profiles:detail')
    else:
        form = EducationForm()
    
    return render(request, 'profiles/education_form.html', {
        'form': form,
        'profile': profile,
        'education_count': education_qs.count(),
        'latest_education': latest_education,
    })


@login_required
def education_delete(request, pk):
    """Remover formação"""
    education = get_object_or_404(Education, pk=pk, profile__user=request.user)
    education.delete()
    messages.success(request, _('Formação removida!'))
    return redirect('profiles:detail')


# Views para Experiência
@login_required
def experience_add(request):
    """Adicionar experiência"""
    if not request.user.has_youth_profile():
        return redirect('profiles:wizard')
    
    if request.method == 'POST':
        profile = request.user.youth_profile
        experience_qs = profile.get_experience()
        latest_experience = experience_qs.first()
        form = ExperienceForm(request.POST)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.profile = profile
            experience.save()
            messages.success(request, _('Experiência adicionada!'))
            return redirect('profiles:detail')
    else:
        profile = request.user.youth_profile
        experience_qs = profile.get_experience()
        latest_experience = experience_qs.first()
        form = ExperienceForm()
    
    return render(request, 'profiles/experience_form.html', {
        'form': form,
        'profile': profile,
        'experience_count': experience_qs.count(),
        'latest_experience': latest_experience,
    })


@login_required
def experience_delete(request, pk):
    """Remover experiência"""
    experience = get_object_or_404(Experience, pk=pk, profile__user=request.user)
    experience.delete()
    messages.success(request, _('Experiência removida!'))
    return redirect('profiles:detail')


# Views para Documentos
@login_required
def document_add(request):
    """Adicionar documento"""
    if not request.user.has_youth_profile():
        return redirect('profiles:wizard')
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.profile = request.user.youth_profile
            document.save()
            messages.success(request, _('Documento adicionado!'))
            return redirect('profiles:detail')
    else:
        form = DocumentForm()
    
    return render(request, 'profiles/document_form.html', {'form': form})


@login_required
def document_delete(request, pk):
    """Remover documento"""
    document = get_object_or_404(Document, pk=pk, profile__user=request.user)
    document.delete()
    messages.success(request, _('Documento removido!'))
    return redirect('profiles:detail')


@login_required
def document_view(request, pk):
    """Abrir documento no navegador (inline)"""
    document = get_object_or_404(Document, pk=pk)
    if not _user_can_access_document(request.user, document):
        raise Http404
    if not document.arquivo:
        raise Http404
    file_handle = document.arquivo.open('rb')
    response = FileResponse(file_handle, as_attachment=False)
    mime, _ = mimetypes.guess_type(document.arquivo.name)
    if mime:
        response['Content-Type'] = mime
    filename = os.path.basename(document.arquivo.name)
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def document_download(request, pk):
    """Baixar documento (attachment)"""
    document = get_object_or_404(Document, pk=pk)
    if not _user_can_access_document(request.user, document):
        raise Http404
    if not document.arquivo:
        raise Http404
    file_handle = document.arquivo.open('rb')
    response = FileResponse(file_handle, as_attachment=True)
    mime, _ = mimetypes.guess_type(document.arquivo.name)
    if mime:
        response['Content-Type'] = mime
    filename = os.path.basename(document.arquivo.name)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _user_can_access_document(user, document):
    if not user.is_authenticated:
        return False
    if user.is_staff or getattr(user, 'is_superuser', False) or getattr(user, 'is_admin', False):
        return True
    if user.is_jovem and user.has_youth_profile():
        return document.profile_id == user.youth_profile.id
    if user.is_empresa and user.has_company_profile():
        company = user.company_profile
        if Application.objects.filter(job__company=company, youth=document.profile).exists():
            return True
        if ContactRequest.objects.filter(company=company, youth=document.profile, estado='APROVADO').exists():
            return True
        if document.profile.visivel and document.profile.completo:
            return True
    return False


@login_required
def skills_edit(request):
    """Editar skills do jovem"""
    if not request.user.is_jovem:
        messages.error(request, _('Apenas jovens têm este tipo de perfil.'))
        return redirect('home')

    if not request.user.has_youth_profile():
        return redirect('profiles:wizard')

    profile = request.user.youth_profile
    existing_ids = list(profile.youth_skills.values_list('skill_id', flat=True))
    skills_qs = Skill.objects.filter(aprovada=True)
    if existing_ids:
        skills_qs = skills_qs | Skill.objects.filter(id__in=existing_ids)
    skills_qs = skills_qs.distinct().order_by('nome')

    if request.method == 'POST':
        form = YouthSkillsForm(request.POST, include_skill_ids=existing_ids)
        if form.is_valid():
            selected_ids = list(form.cleaned_data['skills'].values_list('id', flat=True))
            selected_set = set(selected_ids)
            outra_skill_nome = form.cleaned_data.get('outra_skill_nome', '')
            outra_skill_tipo = form.cleaned_data.get('outra_skill_tipo')
            nova_skill = get_or_create_skill_by_name(outra_skill_nome, outra_skill_tipo)
            if nova_skill:
                selected_set.add(nova_skill.id)
            existing_set = set(existing_ids)

            to_add = selected_set - existing_set
            to_remove = existing_set - selected_set

            if to_add:
                YouthSkill.objects.bulk_create([
                    YouthSkill(profile=profile, skill_id=skill_id, nivel=1)
                    for skill_id in to_add
                ])
            if to_remove:
                YouthSkill.objects.filter(profile=profile, skill_id__in=to_remove).delete()

            messages.success(request, _('Skills atualizadas com sucesso!'))
            return redirect('profiles:detail')
        selected_skill_ids = [int(s) for s in request.POST.getlist('skills') if s.isdigit()]
    else:
        form = YouthSkillsForm(initial={'skills': existing_ids}, include_skill_ids=existing_ids)
        selected_skill_ids = existing_ids

    skills_list = list(skills_qs)
    selected_skill_set = set(selected_skill_ids)
    technical_skills = [skill for skill in skills_list if skill.tipo == 'TEC']
    transversal_skills = [skill for skill in skills_list if skill.tipo == 'TRA']

    context = {
        'form': form,
        'profile': profile,
        'skills': skills_qs,
        'technical_skills': technical_skills,
        'transversal_skills': transversal_skills,
        'selected_skill_ids': selected_skill_ids,
        'selected_total_count': len(selected_skill_set),
        'selected_technical_count': sum(1 for skill in technical_skills if skill.id in selected_skill_set),
        'selected_transversal_count': sum(1 for skill in transversal_skills if skill.id in selected_skill_set),
        'available_skill_count': len(skills_list),
    }
    return render(request, 'profiles/skills_form.html', context)


@login_required
def my_applications(request):
    """Lista de candidaturas do jovem"""
    if not request.user.is_jovem:
        messages.error(request, _('Apenas jovens podem aceder.'))
        return redirect('home')

    if not request.user.has_youth_profile():
        return redirect('profiles:wizard')

    profile = request.user.youth_profile
    now = timezone.now()
    valid_states = {choice[0] for choice in Application.ESTADO_CHOICES}
    status_labels = dict(Application.ESTADO_CHOICES)

    base_applications = Application.objects.filter(
        youth=profile
    ).select_related(
        'job', 'job__company', 'job__distrito'
    ).prefetch_related('messages').order_by('-created_at')

    q = (request.GET.get('q') or '').strip()
    estado = request.GET.get('estado') or ''

    applications = base_applications
    if q:
        applications = applications.filter(
            Q(job__titulo__icontains=q) |
            Q(job__company__nome__icontains=q) |
            Q(job__descricao__icontains=q)
        )
    if estado in valid_states:
        applications = applications.filter(estado=estado)

    paginator = Paginator(applications, 8)
    page_number = request.GET.get('page') or 1
    applications_page = paginator.get_page(page_number)

    filters = request.GET.copy()
    if 'page' in filters:
        del filters['page']
    filters_qs = filters.urlencode()

    active_filter_count = sum(1 for value in [q, estado if estado in valid_states else ''] if value)

    total_applications = base_applications.count()
    pending_count = base_applications.filter(estado='PENDENTE').count()
    analysis_count = base_applications.filter(estado='EM_ANALISE').count()
    accepted_count = base_applications.filter(estado='ACEITE').count()
    rejected_count = base_applications.filter(estado='REJEITADA').count()
    with_messages_count = base_applications.filter(messages__isnull=False).distinct().count()
    recent_updates_count = base_applications.filter(
        Q(updated_at__gte=now - timedelta(days=7)) |
        Q(messages__created_at__gte=now - timedelta(days=7))
    ).distinct().count()

    for app in applications_page.object_list:
        messages_list = list(app.messages.all())
        app.latest_message = messages_list[0] if messages_list else None
        app.company_messages_count = sum(1 for item in messages_list if item.sender == 'EMP')
        app.total_messages_count = len(messages_list)
        app.has_messages = bool(messages_list)
        app.company_initials = ''.join(
            part[0] for part in (app.job.company.nome or '').split()[:2] if part
        ).upper() or 'EM'
        app.is_recent = app.created_at >= now - timedelta(days=7)
        app.latest_touch = app.latest_message.created_at if app.latest_message else app.updated_at
        if app.job.data_fecho:
            app.days_until_close = (app.job.data_fecho - timezone.localdate()).days
        else:
            app.days_until_close = None

    return render(request, 'profiles/my_applications.html', {
        'profile': profile,
        'applications_page': applications_page,
        'status_choices': Application.ESTADO_CHOICES,
        'status_labels': status_labels,
        'selected_query': q,
        'selected_estado': estado if estado in valid_states else '',
        'filters_qs': filters_qs,
        'active_filter_count': active_filter_count,
        'has_active_filters': active_filter_count > 0,
        'total_applications': total_applications,
        'filtered_count': applications.count(),
        'pending_count': pending_count,
        'analysis_count': analysis_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
        'with_messages_count': with_messages_count,
        'recent_updates_count': recent_updates_count,
    })


# Registo Assistido (Operador Distrital)
@login_required
def assisted_register(request):
    """View para registo assistido por operador distrital"""
    if not request.user.is_operador:
        messages.error(request, _('Apenas operadores distritais podem aceder.'))
        return redirect('home')
    
    if request.method == 'POST':
        form = AssistedRegistrationForm(request.POST)
        if form.is_valid():
            # Criar usuário jovem
            data = form.cleaned_data
            idiomas = parse_idioma_payload(data.get('idiomas_data'))
            
            # Verificar se telefone já existe
            if User.objects.filter(telefone=data['telefone']).exists():
                messages.error(request, _('Este telemóvel já está registado.'))
                return render(request, 'profiles/assisted_register.html', {'form': form})
            
            # Criar usuário
            user = User.objects.create_user(
                telefone=data['telefone'],
                nome=data['nome'],
                email=data.get('email', ''),
                perfil='JO',
                distrito=data['distrito'],
                consentimento_dados=True,
                consentimento_contacto=True
            )
            
            # Criar perfil
            profile = YouthProfile.objects.create(
                user=user,
                data_nascimento=data.get('data_nascimento'),
                sexo=data.get('sexo', ''),
                localidade=data.get('localidade', ''),
                situacao_atual=data['situacao_atual'],
                disponibilidade=data['disponibilidade'],
                preferencia_oportunidade=data['preferencia_oportunidade'],
                idiomas=idiomas,
                consentimento_sms=True,
                consentimento_whatsapp=True,
                consentimento_email=True,
                completo=True,
                validado=False  # Aguarda validação do admin
            )
            
            # Adicionar educação se fornecida
            if data.get('nivel') and data.get('area_formacao'):
                Education.objects.create(
                    profile=profile,
                    nivel=data['nivel'],
                    area_formacao=data['area_formacao'],
                    instituicao='Não específicado',
                    ano=None
                )
            
            AuditLog.objects.create(
                user=request.user,
                acao='registo_assistido_criado',
                payload={
                    'jovem_id': user.id,
                    'jovem_nome': user.nome,
                    'jovem_telefone': user.telefone,
                    'distrito_id': data['distrito'].id if data.get('distrito') else None,
                    'operador_id': request.user.id,
                    'operador_nome': request.user.nome,
                    'associacao_parceira': request.user.associacao_parceira,
                    'observacoes': data.get('observacoes', ''),
                },
                ip_address=request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
            )

            messages.success(
                request,
                _('Jovem registado com sucesso! O perfil aguarda validação do administrador.')
            )
            return redirect('profiles:assisted_register')
    else:
        form = AssistedRegistrationForm()
    
    return render(request, 'profiles/assisted_register.html', {'form': form})


# API para buscar jovens
@login_required
def search_youth(request):
    """API para buscar jovens (para empresas)"""
    if not (request.user.is_empresa or request.user.is_admin):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    query = request.GET.get('q', '')
    distrito = request.GET.get('distrito', '')
    nivel = request.GET.get('nivel', '')
    area = request.GET.get('area', '')
    
    profiles = YouthProfile.objects.filter(visivel=True, completo=True)
    
    if query:
        profiles = profiles.filter(
            Q(user__nome__icontains=query) |
            Q(sobre__icontains=query) |
            Q(localidade__icontains=query)
        )
    
    if distrito:
        profiles = profiles.filter(user__distrito__codigo=distrito)
    
    if nivel:
        profiles = profiles.filter(education__nivel=nivel)
    
    if area:
        profiles = profiles.filter(education__area_formacao=area)
    
    results = []
    for profile in profiles.distinct()[:50]:
        results.append({
            'id': profile.id,
            'nome': profile.nome_completo,
            'idade': profile.idade,
            'distrito': profile.distrito.nome if profile.distrito else '',
            'situacao': profile.get_situacao_atual_display(),
            'disponibilidade': profile.get_disponibilidade_display(),
        })
    
    return JsonResponse({'results': results})
