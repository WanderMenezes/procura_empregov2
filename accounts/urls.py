"""
URLs para o app accounts
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Autenticação
    path('registar/', views.RegisterView.as_view(), name='register'),
    path('entrar/', views.LoginView.as_view(), name='login'),
    path('sair/', views.LogoutView.as_view(), name='logout'),
    
    # Recuperação de senha
    path('recuperar-senha/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('recuperar-senha/confirmar/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Perfil
    path('perfil/', views.profile_view, name='profile'),
    path('perfil/editar/', views.profile_edit, name='profile_edit'),
    path('notificacoes/', views.notifications_view, name='notifications'),
    path('notificacoes/<int:pk>/ler/', views.mark_notification_read, name='mark_notification_read'),
    path('confirmar-telemovel/', views.phone_confirm, name='phone_confirm'),
    
    # API
    path('api/verificar-telefone/', views.check_phone_exists, name='check_phone'),
]
