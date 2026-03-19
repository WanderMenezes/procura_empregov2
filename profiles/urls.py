"""
URLs para o app profiles
"""

from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    # Wizard de registo
    path('completar-perfil/', views.ProfileWizardView.as_view(), name='wizard'),
    path('completar-perfil/passo/<int:step>/', views.ProfileWizardView.as_view(), name='wizard_step'),
    
    # Perfil
    path('meu-perfil/', views.profile_detail, name='detail'),
    path('meu-perfil/editar/', views.profile_edit, name='edit'),
    path('candidaturas/<int:pk>/mensagens/', views.application_messages, name='application_messages'),
    path('minhas-candidaturas/', views.my_applications, name='my_applications'),

    # Vagas disponíveis
    path('vagas-disponiveis/', views.available_jobs, name='available_jobs'),
    
    # Educação
    path('educacao/adicionar/', views.education_add, name='education_add'),
    path('educacao/<int:pk>/remover/', views.education_delete, name='education_delete'),
    
    # Experiência
    path('experiencia/adicionar/', views.experience_add, name='experience_add'),
    path('experiencia/<int:pk>/remover/', views.experience_delete, name='experience_delete'),
    
    # Documentos
    path('documentos/adicionar/', views.document_add, name='document_add'),
    path('documentos/<int:pk>/ver/', views.document_view, name='document_view'),
    path('documentos/<int:pk>/download/', views.document_download, name='document_download'),
    path('documentos/<int:pk>/remover/', views.document_delete, name='document_delete'),

    # Skills
    path('skills/editar/', views.skills_edit, name='skills_edit'),
    
    # Registo assistido
    path('registo-assistido/', views.assisted_register, name='assisted_register'),
    
    # API
    path('api/buscar-jovens/', views.search_youth, name='search_youth'),
]
