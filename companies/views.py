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
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
import csv

from .models import Company, JobPost, Application, ContactRequest
from .forms import CompanyProfileForm, JobPostForm, ContactRequestForm, YouthSearchForm
from profiles.models import YouthProfile, Education
from core.models import District, Notification
from django.core.paginator import Paginator


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
        form = CompanyProfileForm()
    
    return render(request, 'companies/complete_profile.html', {'form': form})


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

    context = {
        'company': company,
        'vagas': company.job_posts.all()[:5],
        'pedidos': pedidos_recentes,
        'stats': {
            'vagas_ativas': company.vagas_ativas,
            'total_vagas': company.total_vagas,
            'candidaturas': company.total_candidaturas,
            'visualizacoes': total_visualizacoes,
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
            form.save()
            messages.success(request, _('Perfil atualizado com sucesso!'))
            return redirect('companies:dashboard')
    else:
        form = CompanyProfileForm(instance=company)
    
    return render(request, 'companies/profile_edit.html', {'form': form, 'company': company})


# Views para Vagas
@login_required
def job_list(request):
    """Lista de vagas da empresa"""
    if not request.user.is_empresa or not request.user.has_company_profile():
        messages.error(request, _('Acesso negado.'))
        return redirect('home')
    
    company = request.user.company_profile
    vagas = company.job_posts.all()
    
    context = {
        'vagas': vagas,
        'company': company
    }
    
    return render(request, 'companies/job_list_page.html', context)


@login_required
def job_create(request):
    """Criar nova vaga"""
    if not request.user.is_empresa or not request.user.has_company_profile():
        messages.error(request, _('Acesso negado.'))
        return redirect('home')
    
    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.company = request.user.company_profile
            job.save()
            
            messages.success(request, _('Vaga publicada com sucesso!'))
            return redirect('companies:job_list')
    else:
        form = JobPostForm()
    
    return render(request, 'companies/job_form.html', {'form': form, 'action': 'Criar'})


@login_required
def job_edit(request, pk):
    """Editar vaga"""
    job = get_object_or_404(JobPost, pk=pk, company__user=request.user)
    
    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, _('Vaga atualizada com sucesso!'))
            return redirect('companies:job_list')
    else:
        form = JobPostForm(instance=job)
    
    return render(request, 'companies/job_form.html', {'form': form, 'action': 'Editar', 'job': job})


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
    job = get_object_or_404(JobPost, pk=pk, company__user=request.user)
    
    candidaturas = job.applications.select_related('youth', 'youth__user').all()
    
    context = {
        'job': job,
        'candidaturas': candidaturas
    }
    
    return render(request, 'companies/job_applications.html', context)


@login_required
def application_update(request, pk, estado):
    """Atualizar estado de candidatura"""
    application = get_object_or_404(Application, pk=pk, job__company__user=request.user)
    
    if estado in ['PENDENTE', 'EM_ANALISE', 'ACEITE', 'REJEITADA']:
        application.estado = estado
        application.save()
        
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


# Pesquisa de Jovens
@login_required
def search_youth(request):
    """Pesquisar jovens com paginação e filtros adicionais"""
    if not (request.user.is_empresa and request.user.has_company_profile()):
        messages.error(request, _('Acesso negado.'))
        return redirect('home')

    form = YouthSearchForm(request.GET or None)

    # Lista inicial: últimos jovens visíveis e completos
    base_qs = (
        YouthProfile.objects
        .filter(visivel=True, completo=True)
        .select_related('user')
        .prefetch_related('youth_skills__skill', 'education', 'experiences')
        .order_by('-created_at')
    )

    results_qs = base_qs

    if request.GET and form.is_valid():
        data = form.cleaned_data

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
    paginator = Paginator(results_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'results': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'total': paginator.count,
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
    
    profile = get_object_or_404(YouthProfile, pk=pk, visivel=True, completo=True)
    
    # Incrementar visualizações (se implementado)
    
    # Verificar se já existe pedido de contacto
    existing_request = ContactRequest.objects.filter(
        company=request.user.company_profile,
        youth=profile
    ).first()
    
    context = {
        'profile': profile,
        'education': profile.get_education(),
        'experiences': profile.get_experience(),
        'skills': profile.youth_skills.select_related('skill').all(),
        'existing_request': existing_request
    }
    
    return render(request, 'companies/youth_detail.html', context)


# Pedidos de Contacto
@login_required
def contact_request_create(request, youth_pk):
    """Criar pedido de contacto"""
    if not (request.user.is_empresa and request.user.has_company_profile()):
        messages.error(request, _('Acesso negado.'))
        return redirect('home')
    
    youth = get_object_or_404(YouthProfile, pk=youth_pk, visivel=True)
    
    # Verificar se já existe pedido
    if ContactRequest.objects.filter(
        company=request.user.company_profile,
        youth=youth
    ).exists():
        messages.warning(request, _('Já existe um pedido de contacto para este jovem.'))
        return redirect('companies:youth_detail', pk=youth_pk)
    
    if request.method == 'POST':
        form = ContactRequestForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.company = request.user.company_profile
            contact.youth = youth
            contact.save()
            
            # Notificar jovem
            Notification.objects.create(
                user=youth.user,
                titulo=_('Novo pedido de contacto'),
                mensagem=_('A empresa "{}" solicitou contacto contigo.').format(
                    request.user.company_profile.nome
                ),
                tipo='INFO'
            )

            # Notificar administradores
            User = get_user_model()
            admins = User.objects.filter(perfil=User.ProfileType.ADMIN, is_active=True)
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    titulo=_('Novo pedido de contacto'),
                    mensagem=_('A empresa "%(empresa)s" solicitou contacto com %(jovem)s.') % {
                        'empresa': request.user.company_profile.nome,
                        'jovem': youth.user.nome
                    },
                    tipo='INFO'
                )
            
            messages.success(request, _('Pedido de contacto enviado! Aguarda aprovação do administrador.'))
            return redirect('companies:youth_detail', pk=youth_pk)
    else:
        form = ContactRequestForm()
    
    context = {
        'form': form,
        'youth': youth
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

    created = 0
    skipped = 0
    for yid in youth_ids:
        try:
            youth = YouthProfile.objects.get(pk=int(yid), visivel=True, completo=True)
        except (YouthProfile.DoesNotExist, ValueError):
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
        User = get_user_model()
        admins = User.objects.filter(perfil=User.ProfileType.ADMIN, is_active=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                titulo=_('Novos pedidos de contacto'),
                mensagem=_('A empresa "%(empresa)s" criou %(n)d pedido(s) de contacto.') % {
                    'empresa': company.nome,
                    'n': created
                },
                tipo='INFO'
            )

    return redirect('companies:search_youth')


@login_required
def contact_request_list(request):
    """Lista de pedidos de contacto da empresa"""
    if not (request.user.is_empresa and request.user.has_company_profile()):
        messages.error(request, _('Acesso negado.'))
        return redirect('home')
    
    pedidos = request.user.company_profile.contact_requests.select_related('youth', 'youth__user').all()
    
    context = {
        'pedidos': pedidos
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
            educacao.get_area_formacao_display() if educacao else '',
            profile.interesses_setoriais_display,
            profile.get_preferencia_oportunidade_display(),
            'Sim' if profile.completo else 'Não',
            'Sim' if profile.validado else 'Não',
            profile.created_at.strftime('%d/%m/%Y')
        ])
    
    return response
