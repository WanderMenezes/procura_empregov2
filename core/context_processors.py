"""
Context processors para a Base Nacional de Jovens
"""

from .models import District, Notification


CNJ_CONTACT = {
    'email': 'cnjstp2023@gmail.com',
    'phones_display': '+239 9903424 / +239 9982220',
    'primary_phone': '+2399903424',
    'address': 'Palácio dos Pioneiros Sala Nº 08 - Bairro da Quinta de Sto. António - S. Tomé - STP',
}


def user_profile(request):
    """Adiciona informações do perfil ao contexto"""
    context = {
        'user_has_profile': False,
        'user_profile_type': None,
        'unread_notifications_count': 0,
        'districts': District.objects.all(),
        'cnj_contact': CNJ_CONTACT,
    }
    
    if request.user.is_authenticated:
        user = request.user
        context['user_profile_type'] = user.perfil
        
        # Verificar se tem perfil completo
        if user.is_jovem:
            context['user_has_profile'] = user.has_youth_profile()
        elif user.is_empresa:
            context['user_has_profile'] = user.has_company_profile()
        
        # Notificações não lidas
        context['unread_notifications_count'] = Notification.objects.filter(
            user=user, lida=False
        ).count()
    
    return context
