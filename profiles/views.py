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
from django.http import JsonResponse
from django.db.models import Q
from datetime import timedelta
from django.conf import settings
from django import forms as django_forms

from accounts.sms import send_sms

from .models import YouthProfile, Education, Experience, Document, YouthSkill
from .forms import (
    YouthProfileStep1Form, YouthProfileStep2Form,
    YouthProfileStep3Form, YouthProfileStep4Form,
    AssistedRegistrationForm, YouthProfileEditForm, YouthSkillsForm,
    EducationForm, ExperienceForm, DocumentForm
)
from core.models import District, Skill, Notification
from accounts.models import User
import random
from accounts.models import PhoneChange
from accounts.forms import UserProfileForm


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
        '2': ['nivel', 'area_formacao', 'instituicao', 'ano', 'curso', 'skills'],
        '3': ['situacao_atual', 'disponibilidade', 'interesse_setorial', 'preferencia_oportunidade', 'sobre'],
        '4': ['cv', 'certificado', 'bi', 'visivel', 'consentimento_sms', 'consentimento_whatsapp', 'consentimento_email']
    }

    result = {}

    # helper to fetch education fields
    edu = Education.objects.filter(profile=profile).first()
    docs = Document.objects.filter(profile=profile)
    skills_qs = YouthSkill.objects.filter(profile=profile)

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
                if val:
                    filled += 1
            elif isinstance(val, (list, tuple)):
                if len(val) > 0:
                    filled += 1
            elif val not in (None, '', False):
                filled += 1

        result[step] = {'filled': filled, 'total': total}

    return result


class ProfileWizardView(View):
    """Wizard de 4 passos para criar perfil do jovem"""
    
    template_name = 'profiles/wizard.html'
    
    def get(self, request, step=1):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if not request.user.is_jovem:
            messages.error(request, _('Apenas jovens podem criar perfil.'))
            return redirect('home')
        
        # Verificar se já tem perfil
        if request.user.has_youth_profile():
            return redirect('profiles:detail')
        
        step = int(step)
        if step < 1 or step > 4:
            step = 1
        
        # Carregar dados salvos do wizard + defaults do utilizador
        wizard_data = request.session.get('wizard_data', {})
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

        # passo atual stats
        step_stats = self.compute_step_progress(wizard_data).get(str(step), {'filled': 0, 'total': 0})

        context = {
            'form': form,
            'step': step,
            'progress': progress,
            'total_steps': 4,
            'step_stats': step_stats
        }
        
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

        step_stats = self.compute_step_progress(wizard_data).get(str(step), {'filled': 0, 'total': 0})

        context = {
            'form': form,
            'step': step,
            'progress': progress,
            'total_steps': 4,
            'step_stats': step_stats
        }
        
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
                if isinstance(value, (list, tuple)):
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
            '2': ['nivel', 'area_formacao', 'instituicao', 'ano', 'curso', 'skills'],
            '3': ['situacao_atual', 'disponibilidade', 'interesse_setorial', 'preferencia_oportunidade', 'sobre'],
            '4': ['cv', 'certificado', 'bi', 'visivel', 'consentimento_sms', 'consentimento_whatsapp', 'consentimento_email']
        }

        result = {}
        for step, fields in expected.items():
            total = len(fields)
            filled = 0
            step_data = wizard_data.get(step, {})
            for f in fields:
                val = step_data.get(f)
                if isinstance(val, list):
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

            # Criar perfil base
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
                visivel=visivel,
                consentimento_sms=consentimento_sms,
                consentimento_whatsapp=consentimento_whatsapp,
                consentimento_email=consentimento_email,
                completo=True,
                wizard_step=4
            )
            
            # Adicionar educação
            if step2.get('nivel') and step2.get('instituicao'):
                Education.objects.create(
                    profile=profile,
                    nivel=step2['nivel'],
                    area_formacao=step2.get('area_formacao', ''),
                    instituicao=step2['instituicao'],
                    ano=step2.get('ano'),
                    curso=step2.get('curso', '')
                )
            
            # Adicionar skills
            skills_ids = step2.get('skills', [])
            if skills_ids:
                for skill_id in skills_ids:
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
            
            # Adicionar experiência (se fornecida)
            if self._to_bool(step3.get('tem_experiencia')) and step3.get('exp_entidade') and step3.get('exp_inicio'):
                exp_atual = self._to_bool(step3.get('exp_atual'))
                exp_fim = step3.get('exp_fim') if not exp_atual else None
                Experience.objects.create(
                    profile=profile,
                    entidade=step3['exp_entidade'],
                    cargo=step3.get('exp_cargo', ''),
                    descricao=step3.get('exp_descricao', ''),
                    inicio=step3.get('exp_inicio'),
                    fim=exp_fim,
                    atual=exp_atual
                )
            
            # Processar documentos
            if 'cv' in request.FILES:
                Document.objects.create(
                    profile=profile,
                    tipo='CV',
                    nome='Curriculum Vitae',
                    arquivo=request.FILES['cv']
                )
            if 'certificado' in request.FILES:
                Document.objects.create(
                    profile=profile,
                    tipo='CERT',
                    nome='Certificado',
                    arquivo=request.FILES['certificado']
                )
            if 'bi' in request.FILES:
                Document.objects.create(
                    profile=profile,
                    tipo='BI',
                    nome='Bilhete de Identidade',
                    arquivo=request.FILES['bi']
                )
            
            # Limpar sessão
            if 'wizard_data' in request.session:
                del request.session['wizard_data']
            
            # Notificação
            Notification.objects.create(
                user=request.user,
                titulo=_('Perfil criado com sucesso!'),
                mensagem=_('O teu perfil está completo e visível para empresas. Boa sorte nas oportunidades!'),
                tipo='SUCESSO'
            )
            
            messages.success(request, _('Perfil criado com sucesso!'))
            return redirect('profiles:detail')
            
        except Exception as e:
            messages.error(request, _('Erro ao criar perfil: {}').format(str(e)))
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

    context = {
        'profile': profile,
        'education': profile.get_education(),
        'experiences': profile.get_experience(),
        'documents': profile.get_documents(),
        'skills': profile.youth_skills.select_related('skill').all(),
        'progress': progress,
        'step_stats': step_stats
    }
    
    return render(request, 'profiles/detail.html', context)


@login_required
def profile_edit(request):
    """View para editar perfil do jovem"""
    if not request.user.is_jovem or not request.user.has_youth_profile():
        messages.error(request, _('Perfil não encontrado.'))
        return redirect('home')
    
    profile = request.user.youth_profile
    
    if request.method == 'POST':
        profile_form = YouthProfileEditForm(request.POST, request.FILES, instance=profile)
        user_form = UserProfileForm(request.POST, instance=request.user)
        if profile_form.is_valid() and user_form.is_valid():
            profile_form.save()

            # Atualizar campos do User, mas tratar alteração de telefone com confirmação
            new_phone = user_form.cleaned_data.get('telefone')
            user = request.user
            user.nome = user_form.cleaned_data.get('nome')
            user.email = user_form.cleaned_data.get('email')
            user.distrito = user_form.cleaned_data.get('distrito')

            consent_sms = profile_form.cleaned_data.get('consentimento_sms')
            consent_whatsapp = profile_form.cleaned_data.get('consentimento_whatsapp')
            consent_email = profile_form.cleaned_data.get('consentimento_email')
            user.consentimento_dados = profile_form.cleaned_data.get('visivel', user.consentimento_dados)
            user.consentimento_contacto = bool(consent_sms or consent_whatsapp or consent_email)
            if user.consentimento_dados or user.consentimento_contacto:
                user.data_consentimento = timezone.now()

            if new_phone and new_phone != user.telefone:
                from accounts.models import PhoneChange
                now = timezone.now()
                min_interval = getattr(settings, 'PHONE_CHANGE_MIN_INTERVAL_SECONDS', 300)
                limit_day = getattr(settings, 'PHONE_CHANGE_LIMIT_PER_DAY', 3)

                recent = PhoneChange.objects.filter(user=request.user, created_at__gte=now - timedelta(seconds=min_interval))
                if recent.exists():
                    wait = min_interval
                    messages.error(request, f'Aguarde {wait} segundos antes de pedir novo código.')
                    return redirect('profiles:edit')

                created_today = PhoneChange.objects.filter(user=request.user, created_at__gte=now - timedelta(days=1)).count()
                if created_today >= limit_day:
                    messages.error(request, 'Número máximo de pedidos de confirmação atingido nas últimas 24 horas.')
                    return redirect('profiles:edit')

                pc = PhoneChange.objects.create(user=request.user, new_telephone=new_phone)
                sms_ok = send_sms(pc.new_telephone, f'Seu código de confirmação: {pc.code}')
                if sms_ok:
                    messages.success(request, 'Código de confirmação enviado por SMS.')
                else:
                    messages.error(request, 'Falha ao enviar SMS. Tente novamente mais tarde.')
            else:
                user.telefone = new_phone

            user.save()

            messages.success(request, _('Perfil atualizado com sucesso!'))
            return redirect('profiles:detail')
    else:
        profile_form = YouthProfileEditForm(instance=profile)
        user_form = UserProfileForm(instance=request.user)

    context = {
        'form': profile_form,
        'user_form': user_form,
        'profile': profile
    }

    return render(request, 'profiles/edit.html', context)


# Views para Educação
@login_required
def education_add(request):
    """Adicionar formação"""
    if not request.user.has_youth_profile():
        return redirect('profiles:wizard')
    
    if request.method == 'POST':
        form = EducationForm(request.POST)
        if form.is_valid():
            education = form.save(commit=False)
            education.profile = request.user.youth_profile
            education.save()
            messages.success(request, _('Formação adicionada!'))
            return redirect('profiles:detail')
    else:
        form = EducationForm()
    
    return render(request, 'profiles/education_form.html', {'form': form})


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
        form = ExperienceForm(request.POST)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.profile = request.user.youth_profile
            experience.save()
            messages.success(request, _('Experiência adicionada!'))
            return redirect('profiles:detail')
    else:
        form = ExperienceForm()
    
    return render(request, 'profiles/experience_form.html', {'form': form})


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

    context = {
        'form': form,
        'skills': skills_qs,
        'selected_skill_ids': selected_skill_ids
    }
    return render(request, 'profiles/skills_form.html', context)


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
                    instituicao='Não especificado',
                    ano=None
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
