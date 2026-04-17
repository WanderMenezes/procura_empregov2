"""
Models para autenticação e gestão de usuários
Base Nacional de Jovens
"""

from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de usuário customizado para a Base Nacional de Jovens
    Suporta diferentes perfis: Jovem, Operador Distrital, Empresa, Admin, Técnico PNUD
    """
    
    # Tipos de perfil
    class ProfileType(models.TextChoices):
        JOVEM = 'JO', _('Jovem')
        OPERADOR = 'OP', _('Operador Distrital')
        EMPRESA = 'EMP', _('Empresa')
        ADMIN = 'ADM', _('Administrador')
        TECNICO = 'TEC', _('Técnico PNUD')
    
    email = models.EmailField(_('email address'), unique=True, blank=True, null=True)
    telefone = models.CharField(_('telefone'), max_length=20, unique=True)
    nome = models.CharField(_('nome completo'), max_length=255)
    
    # Tipo de perfil
    perfil = models.CharField(
        _('perfil'),
        max_length=3,
        choices=ProfileType.choices,
        default=ProfileType.JOVEM
    )
    
    # Localização
    distrito = models.ForeignKey(
        'core.District',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('distrito')
    )
    
    # Status
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_active = models.BooleanField(_('active'), default=True)
    is_verified = models.BooleanField(_('verificado'), default=False)
    
    # Consentimentos GDPR
    consentimento_dados = models.BooleanField(
        _('consentimento para uso de dados'),
        default=False,
        help_text=_('Autorizo o uso dos meus dados para fins de empregabilidade')
    )
    consentimento_contacto = models.BooleanField(
        _('consentimento para contacto'),
        default=False,
        help_text=_('Autorizo ser contactado por SMS/WhatsApp/email')
    )
    data_consentimento = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    last_login = models.DateTimeField(_('last login'), null=True, blank=True)
    
    # Campos específicos por perfil
    # Empresa
    nome_empresa = models.CharField(_('nome da empresa'), max_length=255, blank=True)
    nif = models.CharField(_('NIF'), max_length=20, blank=True)
    bi_numero = models.CharField(_('número do BI'), max_length=50, blank=True)
    setor_empresa = models.CharField(_('setor'), max_length=100, blank=True)
    
    # Operador Distrital
    associacao_parceira = models.CharField(_('associação/parceiro'), max_length=255, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'telefone'
    REQUIRED_FIELDS = ['nome']
    
    class Meta:
        verbose_name = _('utilizador')
        verbose_name_plural = _('utilizadores')
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.nome} ({self.get_perfil_display()})"
    
    def get_full_name(self):
        return self.nome
    
    def get_short_name(self):
        return self.nome.split()[0] if self.nome else ''
    
    @property
    def is_jovem(self):
        return self.perfil == self.ProfileType.JOVEM
    
    @property
    def is_operador(self):
        return self.perfil == self.ProfileType.OPERADOR
    
    @property
    def is_empresa(self):
        return self.perfil == self.ProfileType.EMPRESA
    
    @property
    def is_admin(self):
        return self.perfil == self.ProfileType.ADMIN
    
    @property
    def is_tecnico(self):
        return self.perfil == self.ProfileType.TECNICO
    
    def has_youth_profile(self):
        """Verifica se o usuário tem perfil de jovem"""
        return hasattr(self, 'youth_profile')
    
    def has_company_profile(self):
        """Verifica se o usuário tem perfil de empresa"""
        return hasattr(self, 'company_profile')

    def has_security_questions(self):
        return self.security_questions.count() >= 3

    def get_security_questions(self):
        return self.security_questions.order_by('order')[:3]


class PasswordResetCode(models.Model):
    """Códigos de recuperação de senha"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(_('código'), max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('código de recuperação')
        verbose_name_plural = _('códigos de recuperação')
    
    def __str__(self):
        return f"Código para {self.user.telefone}"
    
    def is_valid(self):
        """Verifica se o código ainda é válido (15 minutos)"""
        from datetime import timedelta
        return not self.used and (timezone.now() - self.created_at) < timedelta(minutes=15)


class SecurityQuestion(models.Model):
    """Perguntas de segurança do usuário"""

    QUESTION_CHOICES = [
        ('mother_second_name', _('Qual é o segundo nome da tua mãe?')),
        ('father_second_name', _('Qual é o segundo nome do teu pai?')),
        ('favorite_pet_name', _('Qual é o nome do teu animal preferido?')),
        ('grandparent_name', _('Qual é o nome do teu avô ou avó?')),
        ('favorite_dish', _('Qual é o teu prato favorito?')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='security_questions')
    question_key = models.CharField(_('pergunta'), max_length=50, choices=QUESTION_CHOICES)
    answer_hash = models.CharField(_('resposta criptografada'), max_length=128)
    order = models.PositiveSmallIntegerField(_('ordem'), default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('pergunta de segurança')
        verbose_name_plural = _('perguntas de segurança')
        unique_together = [('user', 'question_key')]
        ordering = ['user', 'order']

    def __str__(self):
        return f"Pergunta de segurança para {self.user.telefone}: {self.get_question_key_display()}"

    def set_answer(self, raw_answer):
        normalized = (raw_answer or '').strip().lower()
        self.answer_hash = make_password(normalized)

    def check_answer(self, raw_answer):
        normalized = (raw_answer or '').strip().lower()
        return check_password(normalized, self.answer_hash)

    @property
    def question_text(self):
        return dict(self.QUESTION_CHOICES).get(self.question_key, '')


class SecurityQuestionAttempt(models.Model):
    """Tentativas de responder às perguntas de segurança"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_question_attempt')
    failed_attempts = models.PositiveSmallIntegerField(_('tentativas falhadas'), default=0)
    blocked_until = models.DateTimeField(_('bloqueado até'), null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('tentativa de perguntas de segurança')
        verbose_name_plural = _('tentativas de perguntas de segurança')

    def is_blocked(self):
        return self.blocked_until and timezone.now() < self.blocked_until

    def record_failure(self):
        self.failed_attempts += 1
        if self.failed_attempts >= 3:
            self.failed_attempts = 0
            self.blocked_until = timezone.now() + timedelta(minutes=10)
        self.save()

    def reset(self):
        self.failed_attempts = 0
        self.blocked_until = None
        self.save()


class PhoneChange(models.Model):
    """Solicitação de alteração de telemóvel com código de confirmação"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    new_phone = models.CharField(_('novo telemóvel'), max_length=20)
    code = models.CharField(_('código'), max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('alteração de telemóvel')
        verbose_name_plural = _('alterações de telemóvel')

    def __str__(self):
        return f"Alteração de telemóvel para {self.new_phone} ({self.user.telefone})"

    def is_valid(self):
        from datetime import timedelta
        return not self.used and (timezone.now() - self.created_at) < timedelta(minutes=15)
