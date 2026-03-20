"""
URLs para o app dashboard
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboards
    path('admin/', views.admin_dashboard, name='admin'),
    path('tecnico/', views.tecnico_dashboard, name='tecnico'),
    
    # Gestão de utilizadores
    path('utilizadores/', views.user_list, name='user_list'),
    path('utilizadores/<int:pk>/editar/', views.user_edit, name='user_edit'),
    path('utilizadores/<int:pk>/toggle/', views.user_toggle_active, name='user_toggle'),
    
    # Validação de perfis
    path('validar-perfis/', views.validate_profiles, name='validate_profiles'),
    path('validar-perfis/<int:pk>/<str:action>/', views.validate_profile, name='validate_profile'),
    
    # Gestão de pedidos de contacto
    path('pedidos-contacto/', views.manage_contact_requests, name='manage_contact_requests'),
    path('pedidos-contacto/<int:pk>/<str:action>/', views.contact_request_action, name='contact_request_action'),
    
    # Relatórios
    path('relatorios/', views.reports, name='reports'),
    path('relatorios/exportar-csv/', views.export_report_csv, name='export_report_csv'),
    path('relatorios/exportar-pdf/', views.export_report_pdf, name='export_report_pdf'),
    path('registos-offline/', views.offline_registrations, name='offline_registrations'),
    path('registos-offline/gerar/', views.offline_registration_export, name='offline_registration_export'),
    path('registos-offline/importar/', views.offline_registration_import, name='offline_registration_import'),
    
    # API
    path('api/estatisticas/', views.api_stats, name='api_stats'),
]
