"""
Models para perfis de jovens
Base Nacional de Jovens
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class YouthProfile(models.Model):
    """Perfil completo do jovem"""
    
    SEXO_CHOICES = [
        ('M', _('Masculino')),
        ('F', _('Feminino')),
        ('O', _('Outro')),
        ('N', _('Prefiro não dizer')),
    ]
    
    SITUACAO_CHOICES = [
        ('EMP', _('Empregado')),
        ('DES', _('Desempregado')),
        ('PEM', _('Primeiro Emprego')),
    ]
    
    DISPONIBILIDADE_CHOICES = [
        ('SIM', _('Sim')),
        ('NAO', _('Não')),
        ('EM_BREVE', _('Em breve')),
    ]
    
    OPORTUNIDADE_CHOICES = [
        ('EST', _('Estágio')),
        ('EMP', _('Emprego')),
        ('FOR', _('Formação de Curta Duração')),
        ('EMPRE', _('Empreendedorismo')),
    ]
    
    # Relação com User
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='youth_profile',
        verbose_name=_('utilizador')
    )
    
    # Dados pessoais
    data_nascimento = models.DateField(_('data de nascimento'), null=True, blank=True)
    sexo = models.CharField(_('sexo'), max_length=1, choices=SEXO_CHOICES, blank=True)
    localidade = models.CharField(_('localidade'), max_length=255, blank=True)
    
    # Situação atual
    situacao_atual = models.CharField(
        _('situação atual'),
        max_length=3,
        choices=SITUACAO_CHOICES,
        default='DES'
    )
    disponibilidade = models.CharField(
        _('disponibilidade imediata'),
        max_length=10,
        choices=DISPONIBILIDADE_CHOICES,
        default='SIM'
    )
    
    # Interesses
    interesse_setorial = models.CharField(
        _('setor de interesse'),
        max_length=3,
        choices=settings.AREAS_FORMACAO,
        blank=True
    )
    preferencia_oportunidade = models.CharField(
        _('preferência de oportunidade'),
        max_length=5,
        choices=OPORTUNIDADE_CHOICES,
        default='EMP'
    )
    
    # Sobre
    sobre = models.TextField(_('sobre mim'), blank=True, help_text=_('Breve descrição sobre ti'))
    
    # Foto de perfil do jovem
    photo = models.ImageField(
        _('foto de perfil'),
        upload_to='youth_avatars/',
        null=True,
        blank=True
    )
    
    # Status
    completo = models.BooleanField(_('perfil completo'), default=False)
    validado = models.BooleanField(_('validado'), default=False)
    visivel = models.BooleanField(_('visível para empresas'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('atualizado em'), auto_now=True)
    
    # Campos de wizard
    wizard_step = models.IntegerField(_('passo do wizard'), default=1)
    wizard_data = models.JSONField(_('dados temporários do wizard'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('perfil de jovem')
        verbose_name_plural = _('perfis de jovens')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Perfil de {self.user.nome}"
    
    @property
    def idade(self):
        """Calcula a idade do jovem"""
        if self.data_nascimento:
            from datetime import date
            today = date.today()
            return today.year - self.data_nascimento.year - (
                (today.month, today.day) < (self.data_nascimento.month, self.data_nascimento.day)
            )
        return None
    
    @property
    def nome_completo(self):
        return self.user.nome
    
    @property
    def telefone(self):
        return self.user.telefone
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def distrito(self):
        return self.user.distrito
    
    def get_skills(self):
        """Retorna todas as skills do jovem"""
        return self.skills.all()
    
    def get_education(self):
        """Retorna toda a formação do jovem"""
        return self.education.all().order_by('-ano')
    
    def get_experience(self):
        """Retorna toda a experiência do jovem"""
        return self.experiences.all().order_by('-inicio')
    
    def get_documents(self):
        """Retorna todos os documentos do jovem"""
        return self.documents.all()
    
    def completar_perfil(self):
        """Marca o perfil como completo"""
        self.completo = True
        self.save(update_fields=['completo'])


class Education(models.Model):
    """Formação/Educação do jovem"""
    
    NIVEL_CHOICES = [
        ('BAS', _('Básico')),
        ('SEC', _('Secundário')),
        ('TEC', _('Técnico')),
        ('SUP', _('Superior')),
    ]
    
    profile = models.ForeignKey(
        YouthProfile,
        on_delete=models.CASCADE,
        related_name='education',
        verbose_name=_('perfil')
    )
    nivel = models.CharField(_('nível'), max_length=3, choices=NIVEL_CHOICES)
    area_formacao = models.CharField(
        _('área de formação'),
        max_length=3,
        choices=settings.AREAS_FORMACAO
    )
    instituicao = models.CharField(_('instituição'), max_length=255)
    ano = models.IntegerField(_('ano de conclusão'), null=True, blank=True)
    curso = models.CharField(_('curso/especialidade'), max_length=255, blank=True)
    
    class Meta:
        verbose_name = _('formação')
        verbose_name_plural = _('formações')
        ordering = ['-ano']
    
    def __str__(self):
        return f"{self.get_nivel_display()} - {self.instituicao}"


class Experience(models.Model):
    """Experiência profissional do jovem"""
    
    profile = models.ForeignKey(
        YouthProfile,
        on_delete=models.CASCADE,
        related_name='experiences',
        verbose_name=_('perfil')
    )
    entidade = models.CharField(_('entidade/empresa'), max_length=255)
    cargo = models.CharField(_('cargo/função'), max_length=255)
    inicio = models.DateField(_('data de início'))
    fim = models.DateField(_('data de fim'), null=True, blank=True)
    atual = models.BooleanField(_('trabalho atual'), default=False)
    descricao = models.TextField(_('descrição das atividades'), blank=True)
    
    class Meta:
        verbose_name = _('experiência')
        verbose_name_plural = _('experiências')
        ordering = ['-inicio']
    
    def __str__(self):
        return f"{self.cargo} - {self.entidade}"
    
    @property
    def duracao(self):
        """Calcula a duração da experiência"""
        fim = self.fim or timezone.now().date()
        dias = (fim - self.inicio).days
        meses = dias // 30
        anos = meses // 12
        if anos > 0:
            return f"{anos} ano{'s' if anos > 1 else ''}"
        elif meses > 0:
            return f"{meses} mês{'es' if meses > 1 else ''}"
        else:
            return f"{dias} dia{'s' if dias > 1 else ''}"


class Document(models.Model):
    """Documentos do jovem (CV, certificados, BI)"""
    
    TIPO_CHOICES = [
        ('CV', _('Curriculum Vitae')),
        ('CERT', _('Certificado')),
        ('BI', _('Bilhete de Identidade')),
        ('OUTRO', _('Outro')),
    ]
    
    profile = models.ForeignKey(
        YouthProfile,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('perfil')
    )
    tipo = models.CharField(_('tipo'), max_length=10, choices=TIPO_CHOICES)
    nome = models.CharField(_('nome do documento'), max_length=255)
    arquivo = models.FileField(_('arquivo'), upload_to='documents/%Y/%m/')
    verificado = models.BooleanField(_('verificado'), default=False)
    created_at = models.DateTimeField(_('enviado em'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('documento')
        verbose_name_plural = _('documentos')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class YouthSkill(models.Model):
    """Relação many-to-many entre YouthProfile e Skill com nível"""
    
    NIVEL_CHOICES = [
        (1, _('Básico')),
        (2, _('Intermédio')),
        (3, _('Avançado')),
        (4, _('Especialista')),
    ]
    
    profile = models.ForeignKey(
        YouthProfile,
        on_delete=models.CASCADE,
        related_name='youth_skills',
        verbose_name=_('perfil')
    )
    skill = models.ForeignKey(
        'core.Skill',
        on_delete=models.CASCADE,
        verbose_name=_('skill')
    )
    nivel = models.IntegerField(_('nível'), choices=NIVEL_CHOICES, default=1)
    
    class Meta:
        verbose_name = _('skill do jovem')
        verbose_name_plural = _('skills dos jovens')
        unique_together = ['profile', 'skill']
    
    def __str__(self):
        return f"{self.skill.nome} - {self.get_nivel_display()}"
