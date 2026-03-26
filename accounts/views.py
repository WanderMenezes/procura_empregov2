"""
Views para autenticação e gestão de usuários
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, FormView, View
from django.urls import reverse_lazy
from django.http import JsonResponse
import random

from .forms import (
    UserRegistrationForm, UserLoginForm,
    PasswordResetRequestForm, PasswordResetConfirmForm,
    UserProfileForm
)
from .models import User, PasswordResetCode
from core.models import Notification
from profiles.models import YouthProfile
from django.shortcuts import HttpResponse
from django.utils import timezone


class RegisterView(CreateView):
    """View para registo de novos usuários"""
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        user = form.save()
        # Se for jovem, criar perfil de jovem e guardar foto opcional
        try:
            if user.is_jovem:
                photo = self.request.FILES.get('photo')
                if not user.has_youth_profile():
                    profile = YouthProfile.objects.create(user=user)
                else:
                    profile = user.youth_profile
                if photo:
                    profile.photo = photo
                    profile.save()
        except Exception:
            # Não falhar o registo apenas por problemas na criação do perfil
            pass
        
        # Criar notificação de boas-vindas
        Notification.objects.create(
            user=user,
            titulo=_('Bem-vindo à Base Nacional de Jovens!'),
            mensagem=_('O seu registo foi realizado com sucesso. Complete o seu perfil para começar a receber oportunidades.'),
            tipo='SUCESSO'
        )
        
        messages.success(
            self.request,
            _('Registo realizado com sucesso! Faça login para continuar.')
        )
        return super().form_valid(form)


class LoginView(FormView):
    """View para login de usuários"""
    template_name = 'accounts/login.html'
    form_class = UserLoginForm
    
    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me', False)
        user = form.get_user()
        
        login(self.request, user)
        

            
            # Configurar sessão
        if not remember_me:
            self.request.session.set_expiry(0)

        messages.success(self.request, _('Bem-vindo, {}!').format(user.nome))

        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return redirect(next_url)
            
        # Redirecionar conforme o perfil
        return self.get_success_url_for_user(user)
    
    def get_success_url_for_user(self, user):
        """Redireciona o usuário conforme seu perfil"""
        if user.is_jovem:
            if not user.has_youth_profile():
                return redirect('profiles:wizard')
            return redirect('profiles:detail')
        elif user.is_empresa:
            if not user.has_company_profile():
                return redirect('companies:complete_profile')
            return redirect('companies:dashboard')
        elif user.is_operador:
            return redirect('profiles:assisted_register')
        elif user.is_admin:
            return redirect('dashboard:admin')
        elif user.is_tecnico:
            return redirect('dashboard:tecnico')
        return redirect('home')


class LogoutView(View):
    """View para logout"""
    
    def get(self, request):
        logout(request)
        messages.success(request, _('Sessão terminada com sucesso.'))
        return redirect('home')


@login_required
def phone_confirm(request):
    """Confirmar alteração de telemóvel com código"""
    user = request.user
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        from .models import PhoneChange
        try:
            pc = PhoneChange.objects.filter(user=user, used=False).latest('created_at')
        except PhoneChange.DoesNotExist:
            messages.error(request, _('Nenhuma alteração de telemóvel pendente.'))
            return redirect('accounts:profile')

        if not pc.is_valid():
            messages.error(request, _('O código expirou. Solicite uma nova alteração.'))
            return redirect('accounts:profile')

        if code == pc.code:
            user.telefone = pc.new_phone
            user.is_verified = True
            user.save()
            pc.used = True
            pc.save()
            messages.success(request, _('Telemóvel confirmado e atualizado com sucesso.'))
            return redirect('accounts:profile')
        else:
            messages.error(request, _('Código inválido.'))
            return redirect('accounts:phone_confirm')

    return render(request, 'accounts/phone_confirm.html')


class PasswordResetRequestView(FormView):
    """View para solicitar código de recuperação de senha"""
    template_name = 'accounts/password_reset_request.html'
    form_class = PasswordResetRequestForm
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        
        try:
            user = User.objects.get(email__iexact=email)
            
            # Gerar código de 6 dígitos
            code = str(random.randint(100000, 999999))
            
            # Salvar código
            reset_code = PasswordResetCode.objects.create(user=user, code=code)

            subject = _('Código de recuperação de senha')
            message = _('O teu código de recuperação é: {}').format(code)
            try:
                email_sent = send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False
                )
            except Exception:
                email_sent = 0

            if not email_sent:
                reset_code.delete()
                messages.error(self.request, _('Não foi possível enviar o email. Tenta novamente.'))
                return self.form_invalid(form)

            messages.success(self.request, _('Enviámos um código de recuperação por email.'))
            
            # Redirecionar para confirmação
            self.request.session['reset_email'] = user.email
            return redirect('accounts:password_reset_confirm')
            
        except User.DoesNotExist:
            messages.error(self.request, _('Não existe conta com este email.'))
            return self.form_invalid(form)


class PasswordResetConfirmView(FormView):
    """View para confirmar recuperação de senha"""
    template_name = 'accounts/password_reset_confirm.html'
    form_class = PasswordResetConfirmForm
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        email = self.request.session.get('reset_email')
        code = form.cleaned_data['code']
        new_password = form.cleaned_data['new_password']
        
        if not email:
            messages.error(self.request, _('Sessão expirada. Solicite novo código.'))
            return redirect('accounts:password_reset_request')
        
        try:
            user = User.objects.get(email__iexact=email)
            reset_code = PasswordResetCode.objects.filter(
                user=user,
                code=code,
                used=False
            ).latest('created_at')
            
            if reset_code.is_valid():
                # Atualizar senha
                user.set_password(new_password)
                user.save()
                
                # Marcar código como usado
                reset_code.used = True
                reset_code.save()
                
                # Limpar sessão
                del self.request.session['reset_email']
                
                messages.success(
                    self.request,
                    _('Palavra-passe alterada com sucesso! Faça login com a nova senha.')
                )
                return super().form_valid(form)
            else:
                messages.error(self.request, _('Código expirado. Solicite novo código.'))
                return self.form_invalid(form)
                
        except (User.DoesNotExist, PasswordResetCode.DoesNotExist):
            messages.error(self.request, _('Código inválido.'))
            return self.form_invalid(form)


@login_required
def profile_view(request):
    """View para visualizar perfil do usuário"""
    user = request.user
    
    context = {
        'user': user,
        'recent_notifications': user.notifications.all()[:4],
        'unread_notifications': user.notifications.filter(lida=False).count(),
    }
    
    if user.is_jovem and user.has_youth_profile():
        profile = user.youth_profile
        education = profile.get_education()
        experiences = profile.get_experience()
        documents = profile.get_documents()
        skills = profile.youth_skills.select_related('skill').all()
        checkpoints = [
            bool(user.nome),
            bool(user.email),
            bool(user.telefone),
            bool(user.distrito_id or profile.localidade),
            bool(profile.data_nascimento),
            bool(profile.sexo),
            bool(profile.localidade),
            bool(profile.situacao_atual),
            bool(profile.disponibilidade),
            bool(profile.preferencia_oportunidade),
            bool(profile.sobre),
            bool(profile.interesse_setorial),
            education.exists(),
            experiences.exists(),
            documents.exists(),
            skills.exists(),
        ]
        profile_strength = int((sum(1 for item in checkpoints if item) / len(checkpoints)) * 100) if checkpoints else 0
        context.update({
            'youth_profile': profile,
            'education': education,
            'experiences': experiences,
            'documents': documents,
            'skills': skills,
            'profile_strength': profile_strength,
            'youth_stats': {
                'education': education.count(),
                'experiences': experiences.count(),
                'documents': documents.count(),
                'skills': skills.count(),
            },
        })
    elif user.is_empresa and user.has_company_profile():
        company = user.company_profile
        jobs = company.job_posts.all()
        company_checks = [
            bool(company.nome),
            bool(company.setor_codes),
            bool(company.telefone),
            bool(company.email),
            bool(company.descricao),
            bool(company.distrito_id),
            bool(company.website),
            bool(company.logo),
        ]
        company_strength = int((sum(1 for item in company_checks if item) / len(company_checks)) * 100) if company_checks else 0
        context.update({
            'company_profile': company,
            'company_strength': company_strength,
            'company_stats': {
                'jobs_total': jobs.count(),
                'jobs_active': jobs.filter(estado='ATIVA').count(),
                'applications': company.total_candidaturas,
                'contact_requests': company.contact_requests.count(),
            },
            'recent_jobs': jobs.order_by('-data_publicacao')[:3],
        })
    
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    """Editar dados da conta e palavra-passe"""
    user = request.user
    profile_form = UserProfileForm(instance=user)
    password_form = PasswordChangeForm(user=user)

    if request.method == 'POST':
        if 'save_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, _('Dados da conta atualizados com sucesso.'))
                return redirect('accounts:profile')
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                updated_user = password_form.save()
                update_session_auth_hash(request, updated_user)
                messages.success(request, _('Palavra-passe alterada com sucesso.'))
                return redirect('accounts:profile_edit')

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
    }

    return render(request, 'accounts/profile_edit.html', context)


@login_required
def notifications_view(request):
    """View para listar notificações do usuário"""
    notifications = request.user.notifications.all()
    
    context = {
        'notifications': notifications[:50],
        'unread_count': notifications.filter(lida=False).count(),
        'notification_summary': {
            'total': notifications.count(),
            'info': notifications.filter(tipo='INFO').count(),
            'success': notifications.filter(tipo='SUCESSO').count(),
            'alert': notifications.filter(tipo='ALERTA').count(),
            'error': notifications.filter(tipo='ERRO').count(),
        }
    }
    
    return render(request, 'accounts/notifications.html', context)


@login_required
def mark_all_notifications_read(request):
    'Marcar todas as notificações do utilizador como lidas'
    if request.method != 'POST':
        return redirect('accounts:notifications')

    updated = request.user.notifications.filter(lida=False).update(lida=True)
    if updated:
        messages.success(request, _('Todas as notificações foram marcadas como lidas.'))
    else:
        messages.info(request, _('Não havia notificações por ler.'))
    return redirect('accounts:notifications')


@login_required
def mark_notification_read(request, pk):
    """Marcar notificação como lida"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.lida = True
    notification.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('accounts:notifications')


@login_required
def delete_notification(request, pk):
    """Eliminar notificação"""
    if request.method != 'POST':
        return redirect('accounts:notifications')
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.delete()
    messages.success(request, _('NotificaÃ§Ã£o eliminada.'))
    return redirect('accounts:notifications')


def check_phone_exists(request):
    """API para verificar se telefone já existe"""
    telefone = request.GET.get('telefone', '')
    exists = User.objects.filter(telefone=telefone).exists()
    return JsonResponse({'exists': exists})
