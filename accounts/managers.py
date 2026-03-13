"""
Custom User Manager para a Base Nacional de Jovens
"""

from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Manager para o modelo User customizado"""
    
    def create_user(self, telefone, nome, password=None, **extra_fields):
        """Cria e salva um usuário comum"""
        if not telefone:
            raise ValueError(_('O telefone é obrigatório'))
        if not nome:
            raise ValueError(_('O nome é obrigatório'))
        
        user = self.model(
            telefone=telefone,
            nome=nome,
            **extra_fields
        )
        
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, telefone, nome, password=None, **extra_fields):
        """Cria e salva um superusuário (admin)"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('perfil', 'ADM')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(telefone, nome, password, **extra_fields)
    
    def create_jovem(self, telefone, nome, password=None, **extra_fields):
        """Cria um usuário do tipo Jovem"""
        extra_fields.setdefault('perfil', 'JO')
        return self.create_user(telefone, nome, password, **extra_fields)
    
    def create_operador(self, telefone, nome, password=None, **extra_fields):
        """Cria um usuário do tipo Operador Distrital"""
        extra_fields.setdefault('perfil', 'OP')
        return self.create_user(telefone, nome, password, **extra_fields)
    
    def create_empresa(self, telefone, nome, nome_empresa, password=None, **extra_fields):
        """Cria um usuário do tipo Empresa"""
        extra_fields.setdefault('perfil', 'EMP')
        extra_fields['nome_empresa'] = nome_empresa
        return self.create_user(telefone, nome, password, **extra_fields)
    
    def create_tecnico(self, telefone, nome, password=None, **extra_fields):
        """Cria um usuário do tipo Técnico PNUD"""
        extra_fields.setdefault('perfil', 'TEC')
        return self.create_user(telefone, nome, password, **extra_fields)
