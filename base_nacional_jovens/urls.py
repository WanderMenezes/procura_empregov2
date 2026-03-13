"""
URL configuration for base_nacional_jovens project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Apps
    path('accounts/', include('accounts.urls')),
    path('profiles/', include('profiles.urls')),
    path('companies/', include('companies.urls')),
    path('dashboard/', include('dashboard.urls')),
    
    # Páginas principais
    path('', core_views.home, name='home'),
    path('sobre/', core_views.about, name='about'),
    path('ajuda/', core_views.help_page, name='help'),
    path('privacidade/', core_views.privacy, name='privacy'),
    path('termos/', core_views.terms, name='terms'),
    
    # API pública
    path('api/estatisticas/', core_views.api_stats_public, name='api_stats_public'),
]

# Servir arquivos de mídia e estáticos em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
