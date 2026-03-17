"""
Views para autenticação e gestão de usuários
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
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
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        remember_me = form.cleaned_data.get('remember_me', False)
        
        # Tentar autenticar por telefone ou email
        user = None
        if '@' in username:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(
                    self.request,
                    username=user_obj.telefone,
                    password=password
                )
            except User.DoesNotExist:
                pass
        else:
            user = authenticate(
                self.request,
                username=username,
                password=password
            )
        
        if user is not None:
            login(self.request, user)
            
            # Configurar sessão
            if not remember_me:
                self.request.session.set_expiry(0)
            
            messages.success(self.request, _('Bem-vindo, {}!').format(user.nome))
            
            # Redirecionar conforme o perfil
            return self.get_success_url_for_user(user)
        else:
            form.add_error(None, _('Telemóvel/Email ou palavra-passe incorretos.'))
            return self.form_invalid(form)
    
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
        telefone = form.cleaned_data['telefone']
        
        try:
            user = User.objects.get(telefone=telefone)
            
            # Gerar código de 6 dígitos
            code = str(random.randint(100000, 999999))
            
            # Salvar código
            PasswordResetCode.objects.create(user=user, code=code)
            
            # Aqui enviaria SMS/WhatsApp (simulação)
            # Em produção, integrar com serviço de SMS
            messages.info(
                self.request,
                _('Código de recuperação: {} (em produção seria enviado por SMS)').format(code)
            )
            
            # Redirecionar para confirmação
            self.request.session['reset_telefone'] = telefone
            return redirect('accounts:password_reset_confirm')
            
        except User.DoesNotExist:
            messages.error(self.request, _('Não existe conta com este telemóvel.'))
            return self.form_invalid(form)


class PasswordResetConfirmView(FormView):
    """View para confirmar recuperação de senha"""
    template_name = 'accounts/password_reset_confirm.html'
    form_class = PasswordResetConfirmForm
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        telefone = self.request.session.get('reset_telefone')
        code = form.cleaned_data['code']
        new_password = form.cleaned_data['new_password']
        
        if not telefone:
            messages.error(self.request, _('Sessão expirada. Solicite novo código.'))
            return redirect('accounts:password_reset_request')
        
        try:
            user = User.objects.get(telefone=telefone)
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
                del self.request.session['reset_telefone']
                
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
    }
    
    if user.is_jovem and user.has_youth_profile():
        context['youth_profile'] = user.youth_profile
    elif user.is_empresa and user.has_company_profile():
        context['company_profile'] = user.company_profile
    
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
    
    # Marcar como lidas
    unread = notifications.filter(lida=False)
    unread.update(lida=True)
    
    context = {
        'notifications': notifications[:50],
        'unread_count': 0
    }
    
    return render(request, 'accounts/notifications.html', context)


@login_required
def mark_notification_read(request, pk):
    """Marcar notificação como lida"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.lida = True
    notification.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('accounts:notifications')


def check_phone_exists(request):
    """API para verificar se telefone já existe"""
    telefone = request.GET.get('telefone', '')
    exists = User.objects.filter(telefone=telefone).exists()
    return JsonResponse({'exists': exists})
