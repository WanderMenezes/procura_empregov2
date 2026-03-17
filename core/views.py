"""
Views para o app core
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q, F
from django.http import JsonResponse

from profiles.models import YouthProfile
from companies.models import JobPost
from core.models import District


def home(request):
    """Página inicial"""
    
    # Estatísticas para exibir
    stats = {
        'total_jovens': YouthProfile.objects.filter(completo=True).count(),
        'total_vagas': JobPost.objects.filter(estado='ATIVA').count(),
        'total_empresas': YouthProfile.objects.filter(
            user__company_profile__isnull=False
        ).count(),
    }
    
    # Vagas recentes
    vagas_recentes = JobPost.objects.filter(
        estado='ATIVA'
    ).select_related('company').annotate(
        aceites=Count('applications', filter=Q(applications__estado='ACEITE'), distinct=True)
    ).filter(
        aceites__lt=F('numero_vagas')
    ).order_by('-data_publicacao')[:6]
    
    context = {
        'stats': stats,
        'vagas_recentes': vagas_recentes,
    }
    
    return render(request, 'core/home.html', context)


def about(request):
    """Página sobre"""
    return render(request, 'core/about.html')


def help_page(request):
    """Página de ajuda"""
    return render(request, 'core/help.html')


def privacy(request):
    """Página de privacidade"""
    return render(request, 'core/privacy.html')


def terms(request):
    """Página de termos de uso"""
    return render(request, 'core/terms.html')


def api_stats_public(request):
    """API pública para estatísticas"""
    
    stats = {
        'jovens_registados': YouthProfile.objects.filter(completo=True).count(),
        'vagas_ativas': JobPost.objects.filter(estado='ATIVA').count(),
    }
    
    return JsonResponse(stats)
