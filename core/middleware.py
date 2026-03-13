"""
Middleware para a Base Nacional de Jovens
"""

from .models import AuditLog


class AuditLogMiddleware:
    """Middleware para registrar logs de auditoria"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Registrar ações importantes
        if request.user.is_authenticated:
            path = request.path
            
            # Ações a registrar
            actions_to_log = [
                '/login/', '/register/', '/wizard/', '/submit/',
                '/create/', '/update/', '/delete/', '/approve/', '/reject/'
            ]
            
            should_log = any(action in path for action in actions_to_log)
            
            if should_log and request.method in ['POST', 'PUT', 'DELETE']:
                try:
                    AuditLog.objects.create(
                        user=request.user,
                        acao=f"{request.method} {path}",
                        ip_address=self.get_client_ip(request)
                    )
                except:
                    pass
        
        return response
    
    def get_client_ip(self, request):
        """Obtém o IP do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
