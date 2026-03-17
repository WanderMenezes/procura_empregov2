"""
URLs para o app companies
"""

from django.urls import path
from . import views

app_name = 'companies'

urlpatterns = [
    # Perfil da empresa
    path('completar-perfil/', views.complete_company_profile, name='complete_profile'),
    path('painel/', views.company_dashboard, name='dashboard'),
    path('perfil/editar/', views.company_profile_edit, name='profile_edit'),
    
    # Vagas
    path('vagas/', views.job_list, name='job_list'),
    path('vagas/criar/', views.job_create, name='job_create'),
    path('vagas/<int:pk>/editar/', views.job_edit, name='job_edit'),
    path('vagas/<int:pk>/fechar/', views.job_close, name='job_close'),
    path('vagas/<int:pk>/candidaturas/', views.job_applications, name='job_applications'),
    path('vagas/<int:pk>/candidatar/', views.job_apply, name='job_apply'),
    
    # Candidaturas
    path('candidaturas/<int:pk>/estado/<str:estado>/', views.application_update, name='application_update'),
    path('candidaturas/<int:pk>/atualizar/', views.application_manage, name='application_manage'),
    path('candidaturas/<int:pk>/mensagens/', views.application_messages, name='application_messages'),
    
    # Pesquisa de jovens
    path('pesquisar-jovens/', views.search_youth, name='search_youth'),
    path('jovens/<int:pk>/', views.youth_detail, name='youth_detail'),
    
    # Pedidos de contacto
    path('jovens/<int:youth_pk>/solicitar-contacto/', views.contact_request_create, name='contact_request_create'),
    path('pedidos-contacto/bulk/', views.contact_request_bulk_create, name='contact_request_bulk_create'),
    path('pedidos-contacto/', views.contact_request_list, name='contact_request_list'),
    
    # Exportação
    path('exportar/jovens-csv/', views.export_youth_csv, name='export_youth_csv'),
]
