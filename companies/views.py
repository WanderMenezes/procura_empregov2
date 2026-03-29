"""
Views para empresas
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse
import csv

from .models import Company, JobPost, Application, ContactRequest, ApplicationMessage
from .forms import CompanyProfileForm, JobPostForm, ContactRequestForm, YouthSearchForm
from profiles.models import YouthProfile, Education
from core.models import District, Notification
from core.notifications import notify_admins
from django.core.paginator import Paginator


def _close_job_if_full(job):
    if not job.tem_vagas_disponiveis and job.estado != 'FECHADA':
        job.estado = 'FECHADA'
        job.save(update_fields=['estado'])


def _notify_admins_about_placement(application):
    if application.estado != 'ACEITE' or application.job.tipo != 'EMP':
        return

    notify_admins(
        _('Nova colocacao em emprego'),
        _('A candidatura de %(jovem)s para a vaga "%(vaga)s" da empresa "%(empresa)s" foi aceite e conta como colocacao.') % {
            'jovem': application.youth.user.nome,
            'vaga': application.job.titulo,
            'empresa': application.job.company.nome,
        },
        tipo='SUCESSO',
    )


def _sync_company_identity(user, company):
    """Mantém os dados base da conta em sintonia com o perfil da empresa."""
    update_fields = []
    company_name = company.nome or user.nome_empresa or user.nome
    company_nif = company.nif or ''
    company_setores = company.setores_display

    if user.nome != company_name:
        user.nome = company_name
        update_fields.append('nome')

    if user.nome_empresa != company_name:
        user.nome_empresa = company_name
        update_fields.append('nome_empresa')

    if user.nif != company_nif:
        user.nif = company_nif
        update_fields.append('nif')

    if user.setor_empresa != company_setores:
        user.setor_empresa = company_setores
        update_fields.append('setor_empresa')

    if update_fields:
        user.save(update_fields=update_fields)


def _company_visible_profiles(profiles):
    visible_profiles = []
    for profile in profiles:
        if profile.is_visible_to_companies:
            visible_profiles.append(profile)
    return visible_profiles


@login_required
def complete_company_profile(request):
    """View para completar perfil da empresa"""
    if not request.user.is_empresa:
        messages.error(request, _('Apenas empresas podem aceder.'))
        return redirect('home')
    
    # Verificar se já tem perfil
    if request.user.has_company_profile():
        return redirect('companies:dashboard')
    
    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save(commit=False)
            company.user = request.user
            # processar logo para manter consistência com o form.save
            logo = form.cleaned_data.get('logo')
            if logo:
                try:
                    content, name = form._process_logo_file(logo)
                    company.logo.save(name, content, save=False)
                except Exception:
                    # se processamento falhar, prosseguir e salvar sem imagem
                    pass
            company.save()
            _sync_company_identity(request.user, company)
            
            # Notificação
            Notification.objects.create(
                user=request.user,
                titulo=_('Perfil da empresa criado!'),
                mensagem=_('O perfil da empresa foi criado com sucesso. Já pode publicar vagas e pesquisar jovens.'),
                tipo='SUCESSO'
            )
            
            messages.success(request, _('Perfil da empresa criado com sucesso!'))
            return redirect('companies:dashboard')
    else:
        form = CompanyProfileForm(initial={
            'nome': request.user.nome_empresa or request.user.nome,
            'nif': request.user.nif,
            'telefone': request.user.telefone,
            'email': request.user.email,
        })
    
    return render(request, 'companies/complete_profile.html', {
        'form': form,
        'draft_company_name': request.user.nome_empresa or request.user.nome,
    })


@login_required
def company_dashboard(request):
    """Dashboard da empresa"""
    if not request.user.is_empresa:
        messages.error(request, _('Apenas empresas podem aceder.'))
        return redirect('home')
    
    if not request.user.has_company_profile():
        return redirect('companies:complete_profile')
    
    company = request.user.company_profile
    total_visualizacoes = company.job_posts.aggregate(total=Sum('visualizacoes'))['total'] or 0
    pedidos_recentes = company.contact_requests.select_related('youth', 'youth__user').order_by('-created_at')[:5]

    company_profile_complete = all([
        company.nome,
        company.setor,
        company.telefone,
        company.email,
        company.distrito_id,
        company.endereco,
        company.descricao,
    ])

    context = {
        'company': company,
        'vagas': company.job_posts.all()[:5],
        'pedidos': pedidos_recentes,
        'company_profile_complete': company_profile_complete,
        'stats': {
            'vagas_ativas': company.vagas_ativas,
            'total_vagas': company.total_vagas,
            'candidaturas': company.total_candidaturas,
            'visualizacoes': total_visualizacoes,
            'pedidos_total': company.contact_requests.count(),
            'pedidos_pendentes': company.contact_requests.filter(estado='PENDENTE').count(),
        }
    }
    
    return render(request, 'companies/dashboard.html', context)


@login_required
def company_profile_edit(request):
    """Editar perfil da empresa"""
    if not request.user.is_empresa or not request.user.has_company_profile():
        messages.error(request, _('Perfil não encontrado.'))
        return redirect('home')
    
    company = request.user.company_profile
    
    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            company = form.save()
            _sync_company_identity(request.user, company)
            messages.success(request, _('Perfil atualizado com sucesso!'))
            return redirect('companies:dashboard')
    else:
        form = CompanyProfileForm(instance=company)
    
    company_profile_complete = all([
        company.nome,
        company.setor,
        company.telefone,
        company.email,
        company.distrito_id,
        company.endereco,
        company.descricao,
    ])

    return render(request, 'companies/profile_edit.html', {
        'form': form,
        'company': company,
        'company_profile_complete': company_profile_complete
    })


# Views para Vagas
@login_required
def job_list(request):
    """Lista de vagas da empresa"""
    if not request.user.is_empresa or not request.user.has_company_profile():
        messages.error(request, _('Acesso negado.'))
        return redirect('home')
    
    company = request.user.company_profile
    vagas = company.job_posts.all()
    total_visualizacoes = vagas.aggregate(total=Sum('visualizacoes'))['total'] or 0
    
    context = {
        'vagas': vagas,
        'company': company,
        'job_stats': {
            'total': vagas.count(),
            'ativas': vagas.filter(estado='ATIVA').count(),
            'pausadas': vagas.filter(estado='PAUSADA').count(),
            'fechadas': vagas.filter(estado='FECHADA').count(),
            'candidaturas': company.total_candidaturas,
            'visualizacoes': total_visualizacoes,
        }
    }
    
    return render(request, 'companies/job_list_page.html', context)


@login_required
def job_create(request):
    """Criar nova vaga"""
    if not request.user.is_empresa or not request.user.has_company_profile():
        messages.error(request, _('Acesso negado.'))
        return redirect('home')

    company = request.user.company_profile

    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.company = company
            job.save()
            
            messages.success(request, _('Vaga publicada com sucesso!'))
            return redirect('companies:job_list')
    else:
        form = JobPostForm()

    return render(request, 'companies/job_form.html', {
        'form': form,
        'action': 'Criar',
        'company': company,
        'job': None,
    })


@login_required
def job_edit(request, pk):
    """Editar vaga"""
    job = get_object_or_404(JobPost, pk=pk, company__user=request.user)
    company = job.company
    
    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, _('Vaga atualizada com sucesso!'))
            return redirect('companies:job_list')
    else:
        form = JobPostForm(instance=job)

    return render(request, 'companies/job_form.html', {
        'form': form,
        'action': 'Editar',
        'job': job,
        'company': company,
    })


@login_required
def job_close(request, pk):
    """Fechar vaga"""
    job = get_object_or_404(JobPost, pk=pk, company__user=request.user)
    job.estado = 'FECHADA'
    job.save()
    messages.success(request, _('Vaga fechada com sucesso!'))
    return redirect('companies:job_list')


@login_required
def job_applications(request, pk):
    """Ver candidaturas de uma vaga"""
    job = get_object_or_404(
        JobPost.objects.select_related('company', 'distrito'),
        pk=pk,
        company__user=request.user
    )
    
    candidaturas = (
        job.applications
        .select_related('youth', 'youth__user', 'youth__user__distrito')
        .prefetch_related('messages', 'youth__documents')
        .all()
    )
    
    context = {
        'company': job.company,
        'job': job,
        'candidaturas': candidaturas,
        'applications': candidaturas,
        'application_summary': {
            'total': candidaturas.count(),
            'pending': candidaturas.filter(estado='PENDENTE').count(),
            'analysis': candidaturas.filter(estado='EM_ANALISE').count(),
            'accepted': candidaturas.filter(estado='ACEITE').count(),
            'rejected': candidaturas.filter(estado='REJEITADA').count(),
            'with_documents': candidaturas.filter(youth__documents__isnull=False).distinct().count(),
        }
    }
    
    return render(request, 'companies/job_applications.html', context)


@login_required
def job_apply(request, pk):
    """Candidatar-se a uma vaga (jovens)"""
    if not request.user.is_jovem:
        messages.error(request, _('Apenas jovens podem candidatar-se.'))
        return redirect('home')

    if not request.user.has_youth_profile():
        return redirect('profiles:wizard')

    if request.method != 'POST':
        return redirect('profiles:detail')

    profile = request.user.youth_profile
    if not profile.can_apply_to_jobs:
        messages.warning(
            request,
            profile.company_visibility_status_message
        )
        return redirect('profiles:available_jobs')

    job = get_object_or_404(JobPost, pk=pk, estado='ATIVA')
    if not job.tem_vagas_disponiveis:
        messages.error(request, _('Esta vaga já não tem vagas disponíveis.'))
        return redirect('profiles:available_jobs')
    application, created = Application.objects.get_or_create(job=job, youth=profile)
    if created:
        Notification.objects.create(
            user=job.company.user,
            titulo=_('Nova candidatura'),
            mensagem=_('{} candidatou-se à vaga "{}".').format(profile.nome_completo, job.titulo),
            tipo='INFO'
        )
        messages.success(request, _('Candidatura enviada com sucesso!'))
    else:
        messages.info(request, _('Já te candidataste a esta vaga.'))

    return redirect('profiles:detail')


@login_required
def application_update(request, pk, estado):
    """Atualizar estado de candidatura"""
    application = get_object_or_404(
        Application.objects.select_related(
            'job',
            'job__company',
            'job__distrito',
            'youth',
            'youth__user',
            'youth__user__distrito',
        ),
        pk=pk,
        job__company__user=request.user
    )
    
    if estado in ['PENDENTE', 'EM_ANALISE', 'ACEITE', 'REJEITADA']:
        was_accepted = application.estado == 'ACEITE'
        if estado == 'ACEITE' and application.estado != 'ACEITE' and not application.job.tem_vagas_disponiveis:
            messages.error(request, _('Esta vaga já não tem vagas disponíveis.'))
            return redirect('companies:job_applications', pk=application.job.pk)

        application.estado = estado
        application.save()

        if estado == 'ACEITE':
            _close_job_if_full(application.job)
            if not was_accepted:
                _notify_admins_about_placement(application)
        
        # Notificar jovem
        Notification.objects.create(
            user=application.youth.user,
            titulo=_('Atualização de candidatura'),
            mensagem=_('A tua candidatura para "{}" foi atualizada para: {}').format(
                application.job.titulo,
                application.get_estado_display()
            ),
            tipo='INFO'
        )
        
        messages.success(request, _('Estado atualizado com sucesso!'))
    
    return redirect('companies:job_applications', pk=application.job.pk)


@login_required
def application_manage(request, pk):
    """Atualizar estado e mensagem para o candidato"""
    application = get_object_or_404(Application, pk=pk, job__company__user=request.user)

    if request.method == 'POST':
        estado = request.POST.get('estado')
        mensagem = (request.POST.get('resposta_empresa') or '').strip()

        if estado in ['PENDENTE', 'EM_ANALISE', 'ACEITE', 'REJEITADA']:
            was_accepted = application.estado == 'ACEITE'
            if estado == 'ACEITE' and application.estado != 'ACEITE' and not application.job.tem_vagas_disponiveis:
                messages.error(request, _('Esta vaga já não tem vagas disponíveis.'))
                return redirect('companies:job_applications', pk=application.job.pk)
            application.estado = estado
        if mensagem:
            application.resposta_empresa = mensagem
            ApplicationMessage.objects.create(
                application=application,
                sender='EMP',
                message=mensagem
            )
        application.save()
        if estado == 'ACEITE':
            _close_job_if_full(application.job)
            if not was_accepted:
                _notify_admins_about_placement(application)

        # Notificar jovem
        notif_msg = _('A tua candidatura para "{}" foi atualizada para: {}.').format(
            application.job.titulo,
            application.get_estado_display()
        )
        if mensagem:
            notif_msg += ' ' + _('Mensagem da empresa: {}').format(mensagem)

        Notification.objects.create(
            user=application.youth.user,
            titulo=_('Atualização de candidatura'),
            mensagem=notif_msg,
            tipo='INFO'
        )

        messages.success(request, _('Candidatura atualizada com sucesso!'))

    return redirect('companies:job_applications', pk=application.job.pk)


@login_required
def application_messages(request, pk):
    """Histórico de mensagens de uma candidatura (empresa)"""
    application = get_object_or_404(Application, pk=pk, job__company__user=request.user)
    if not application.youth.is_visible_to_companies:
        application.youth.user.telefone = ''
        application.youth.user.email = ''
    messages_qs = application.messages.all().order_by('-created_at')
    paginator = Paginator(messages_qs, 10)
    page_number = request.GET.get('page') or 1
    messages_page = paginator.get_page(page_number)

    context = {
        'company': application.job.company,
        'application': application,
        'messages_page': messages_page,
        'message_summary': {
            'total': messages_qs.count(),
            'system': messages_qs.filter(sender='SYS').count(),
            'company': messages_qs.filter(sender='EMP').count(),
        }
    }

    return render(request, 'companies/application_messages.html', context)


# Pesquisa de Jovens
@login_required
def search_youth(request):
    'Pesquisar jovens com páginação e filtros adicionais'
    if not (request.user.is_empresa and request.user.has_company_profile()):
        messages.error(request, _('Acesso negado.'))
        return redirect('home')

    company = request.user.company_profile
    form = YouthSearchForm(request.GET or None)
    minimum_birth_date = YouthProfile.minimum_validation_birth_date()

    # Lista inicial: últimos jovens visíveis e completos
    base_qs = (
        YouthProfile.objects
        .filter(
            completo=True,
            validado=True,
            data_nascimento__isnull=False,
            data_nascimento__lte=minimum_birth_date,
        )
        .select_related('user', 'user__distrito')
        .prefetch_related('youth_skills__skill', 'education', 'experiences', 'documents')
        .order_by('-created_at')
    )

    base_profiles = _company_visible_profiles(base_qs)
    total_pool = len(base_profiles)
    available_now = sum(1 for profile in base_profiles if profile.disponibilidade == 'SIM')
    with_experience = sum(1 for profile in base_profiles if profile.experiences.all())

    results_qs = base_qs
    active_filters = 0

    if request.GET and form.is_valid():
        data = form.cleaned_data
        active_filters = sum(
            1 for value in data.values()
            if value not in (None, '', [], (), False)
        )

        if data.get('q'):
            q = data['q']
            results_qs = results_qs.filter(
                Q(user__nome__icontains=q) |
                Q(sobre__icontains=q) |
                Q(localidade__icontains=q)
            )

        if data.get('distrito'):
            results_qs = results_qs.filter(user__distrito=data['distrito'])

        if data.get('nivel'):
            results_qs = results_qs.filter(education__nivel=data['nivel'])

        if data.get('area'):
            results_qs = results_qs.filter(education__area_formacao=data['area'])

        if data.get('disponibilidade'):
            results_qs = results_qs.filter(disponibilidade=data['disponibilidade'])

        if data.get('com_experiencia'):
            results_qs = results_qs.filter(experiences__isnull=False)

        skills = data.get('skills')
        if skills:
            results_qs = results_qs.filter(youth_skills__skill=skills)

        profissao = data.get('profissao')
        if profissao:
            results_qs = results_qs.filter(experiences__cargo__icontains=profissao)

        results_qs = results_qs.distinct()

    # Paginação
    filtered_profiles = _company_visible_profiles(results_qs)
    paginator = Paginator(filtered_profiles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'company': company,
        'form': form,
        'results': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'total': paginator.count,
        'search_summary': {
            'base_total': total_pool,
            'available_now': available_now,
            'with_experience': with_experience,
            'active_filters': active_filters,
        }
    }

    # Se pedido AJAX, retornar apenas o fragmento de resultados
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'companies/_search_results.html', context)

    return render(request, 'companies/search_youth.html', context)


@login_required
def youth_detail(request, pk):
    """Ver detalhes de um jovem"""
    if not (request.user.is_empresa and request.user.has_company_profile()):
        messages.error(request, _('Acesso negado.'))
        return redirect('home')
    
    company = request.user.company_profile
    minimum_birth_date = YouthProfile.minimum_validation_birth_date()
    profile = get_object_or_404(
        YouthProfile.objects.select_related('user', 'user__distrito').prefetch_related(
            'youth_skills__skill',
            'education',
            'experiences',
            'documents',
        ),
        pk=pk,
        completo=True,
    )
    
    # Incrementar visualizações (se implementado)
    
    # Verificar se já existe pedido de contacto
    existing_request = ContactRequest.objects.filter(
        company=company,
        youth=profile
    ).first()
    is_profile_available = bool(
        profile.data_nascimento and
        profile.data_nascimento <= minimum_birth_date and
        profile.is_visible_to_companies
    )

    if not is_profile_available and not existing_request:
        messages.warning(request, _('Este perfil ja nao esta disponivel para empresas. As empresas so podem ver perfis aprovados pelo admin e com pelo menos 80% do perfil preenchido.'))
        return redirect('companies:search_youth')
    
    context = {
        'company': company,
        'profile': profile,
        'education': profile.get_education(),
        'experiences': profile.get_experience(),
        'skills': profile.youth_skills.select_related('skill').all(),
        'existing_request': existing_request,
        'documents': profile.get_documents(),
        'can_view_contact': bool(existing_request and existing_request.estado == 'APROVADO' and is_profile_available),
        'profile_available_to_companies': is_profile_available,
    }
    
    return render(request, 'companies/youth_detail.html', context)


# Pedidos de Contacto
@login_required
def contact_request_create(request, youth_pk):
    """Criar pedido de contacto"""
    if not (request.user.is_empresa and request.user.has_company_profile()):
        messages.error(request, _('Acesso negado.'))
        return redirect('home')
    
    company = request.user.company_profile
    minimum_birth_date = YouthProfile.minimum_validation_birth_date()
    youth = get_object_or_404(
        YouthProfile.objects.select_related('user', 'user__distrito').prefetch_related(
            'youth_skills__skill',
            'documents',
            'education',
            'experiences',
        ),
        pk=youth_pk,
        completo=True,
    )

    is_profile_available = bool(
        youth.data_nascimento and
        youth.data_nascimento <= minimum_birth_date and
        youth.is_visible_to_companies
    )
    if not is_profile_available:
        messages.warning(request, _('Este perfil ja nao esta disponivel para novos pedidos de contacto. As empresas so podem ver perfis aprovados pelo admin e com pelo menos 80% do perfil preenchido.'))
        return redirect('companies:search_youth')
    
    # Verificar se já existe pedido
    if ContactRequest.objects.filter(
        company=company,
        youth=youth
    ).exists():
        messages.warning(request, _('Já existe um pedido de contacto para este jovem.'))
        return redirect('companies:youth_detail', pk=youth_pk)
    
    if request.method == 'POST':
        form = ContactRequestForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.company = company
            contact.youth = youth
            contact.save()
            
            # Notificar jovem
            Notification.objects.create(
                user=youth.user,
                titulo=_('Novo pedido de contacto'),
                mensagem=_('A empresa "{}" solicitou contacto contigo.').format(
                    company.nome
                ),
                tipo='INFO'
            )

            notify_admins(
                _('Novo pedido de contacto'),
                _('A empresa "%(empresa)s" solicitou contacto com %(jovem)s.') % {
                    'empresa': company.nome,
                    'jovem': youth.user.nome,
                },
                tipo='INFO',
            )
            
            messages.success(request, _('Pedido de contacto enviado! Aguarda aprovação do administrador.'))
            return redirect('companies:youth_detail', pk=youth_pk)
    else:
        form = ContactRequestForm()
    
    context = {
        'form': form,
        'company': company,
        'youth': youth,
        'skills': youth.youth_skills.select_related('skill').all(),
        'documents': youth.get_documents(),
        'education': youth.get_education(),
        'experiences': youth.get_experience(),
    }
    
    return render(request, 'companies/contact_request_form.html', context)


@login_required
def contact_request_bulk_create(request):
    """Criar pedidos de contacto em massa a partir da página de pesquisa de jovens."""
    if not (request.user.is_empresa and request.user.has_company_profile()):
        messages.error(request, _('Acesso negado.'))
        return redirect('home')

    if request.method != 'POST':
        return redirect('companies:search_youth')

    youth_ids = request.POST.getlist('youth_ids')
    motivo = request.POST.get('motivo', '').strip() or _('A empresa demonstrou interesse. Por favor verifique o seu perfil.')
    company = request.user.company_profile
    minimum_birth_date = YouthProfile.minimum_validation_birth_date()

    created = 0
    skipped = 0
    for yid in youth_ids:
        try:
            youth = YouthProfile.objects.get(
                pk=int(yid),
                completo=True,
                validado=True,
                data_nascimento__isnull=False,
                data_nascimento__lte=minimum_birth_date,
            )
        except (YouthProfile.DoesNotExist, ValueError):
            skipped += 1
            continue

        if not youth.is_visible_to_companies:
            skipped += 1
            continue

        # Evitar duplicados
        if ContactRequest.objects.filter(company=company, youth=youth).exists():
            skipped += 1
            continue

        ContactRequest.objects.create(
            company=company,
            youth=youth,
            motivo=motivo,
            estado='PENDENTE'
        )

        # Notificar jovem
        Notification.objects.create(
            user=youth.user,
            titulo=_('Novo pedido de contacto'),
            mensagem=_('A empresa "%(empresa)s" solicitou contacto consigo.') % {'empresa': company.nome},
            tipo='INFO'
        )

        created += 1

    if created:
        messages.success(request, _('%(n)d pedido(s) de contacto criado(s).') % {'n': created})
    if skipped:
        messages.warning(request, _('%(n)d jovem(s) ignorado(s) (já tinha pedido ou inválido).') % {'n': skipped})

    if created:
        notify_admins(
            _('Novos pedidos de contacto'),
            _('A empresa "%(empresa)s" criou %(n)d pedido(s) de contacto.') % {
                'empresa': company.nome,
                'n': created,
            },
            tipo='INFO',
        )

    return redirect('companies:search_youth')


@login_required
def contact_request_list(request):
    """Lista de pedidos de contacto da empresa"""
    if not (request.user.is_empresa and request.user.has_company_profile()):
        messages.error(request, _('Acesso negado.'))
        return redirect('home')

    company = request.user.company_profile
    pedidos = company.contact_requests.select_related(
        'youth',
        'youth__user',
        'youth__user__distrito',
    ).all()

    context = {
        'company': company,
        'pedidos': pedidos,
        'contact_summary': {
            'total': pedidos.count(),
            'pending': pedidos.filter(estado='PENDENTE').count(),
            'approved': pedidos.filter(estado='APROVADO').count(),
            'disabled': pedidos.filter(estado='DESATIVADO').count(),
            'rejected': pedidos.filter(estado='REJEITADO').count(),
            'responded': pedidos.exclude(responded_at__isnull=True).count(),
        }
    }

    return render(request, 'companies/contact_request_page.html', context)


# Exportação
@login_required
def export_youth_csv(request):
    """Exportar jovens para CSV (apenas admin)"""
    if not request.user.is_admin:
        messages.error(request, _('Acesso negado.'))
        return redirect('home')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="jovens_base_nacional.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Nome', 'Telefone', 'Email', 'Distrito', 'Idade', 'Sexo',
        'Situação', 'Disponibilidade', 'Nível Educação', 'Área Formação',
        'Setor Interesse', 'Preferência', 'Completo', 'Validado', 'Data Registo'
    ])
    
    for profile in YouthProfile.objects.all():
        educacao = profile.get_education().first()
        writer.writerow([
            profile.id,
            profile.nome_completo,
            profile.telefone,
            profile.email or '',
            profile.distrito.nome if profile.distrito else '',
            profile.idade or '',
            profile.get_sexo_display(),
            profile.get_situacao_atual_display(),
            profile.get_disponibilidade_display(),
            educacao.get_nivel_display() if educacao else '',
            educacao.area_formacao_display if educacao else '',
            profile.interesses_setoriais_display,
            profile.get_preferencia_oportunidade_display(),
            'Sim' if profile.completo else 'Não',
            'Sim' if profile.validado else 'Não',
            profile.created_at.strftime('%d/%m/%Y')
        ])
    
    return response
