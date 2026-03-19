"""
Models para empresas e vagas
Base Nacional de Jovens
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """Perfil de empresa/instituição"""
    
    SETOR_CHOICES = [
        ('AGR', _('Agricultura')),
        ('TUR', _('Turismo')),
        ('TIC', _('Tecnologias de Informação')),
        ('IND', _('Indústria')),
        ('SER', _('Serviços')),
        ('ENE', _('Energias Renováveis')),
        ('ADM', _('Administração Pública')),
        ('SAU', _('Saúde')),
        ('EDU', _('Educação')),
        ('CON', _('Construção')),
        ('COM', _('Comércio')),
        ('FIN', _('Financeiro')),
        ('OUT', _('Outro')),
    ]
    
    # Relação com User
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_profile',
        verbose_name=_('utilizador')
    )
    
    # Dados da empresa
    nome = models.CharField(_('nome da empresa'), max_length=255)
    nif = models.CharField(_('NIF'), max_length=20, blank=True)
    setor = models.JSONField(_('setores de atividade'), default=list, blank=True)
    descricao = models.TextField(_('descrição'), blank=True)
    
    # Contactos
    telefone = models.CharField(_('telefone'), max_length=20, blank=True)
    email = models.EmailField(_('email'), blank=True)
    website = models.URLField(_('website'), blank=True)
    
    # Localização
    distrito = models.ForeignKey(
        'core.District',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('distrito')
    )
    endereco = models.TextField(_('endereço'), blank=True)
    
    # Status
    ativa = models.BooleanField(_('ativa'), default=True)
    verificada = models.BooleanField(_('verificada'), default=False)
    
    # Logo / imagem de perfil da empresa
    logo = models.ImageField(
        _('logo'),
        upload_to='company_logos/',
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(_('registada em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('atualizada em'), auto_now=True)
    
    class Meta:
        verbose_name = _('empresa')
        verbose_name_plural = _('empresas')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.nome

    @classmethod
    def get_setor_mapping(cls):
        return dict(cls.SETOR_CHOICES)

    @property
    def setor_codes(self):
        codes = self.setor or []
        if isinstance(codes, str):
            codes = [codes] if codes else []
        elif isinstance(codes, (tuple, set)):
            codes = list(codes)
        elif not isinstance(codes, list):
            codes = [str(codes)] if codes else []

        normalized = []
        for code in codes:
            value = str(code).strip()
            if value and value not in normalized:
                normalized.append(value)
        return normalized

    @property
    def setores_display(self):
        mapping = self.get_setor_mapping()
        labels = [str(mapping.get(code, code)) for code in self.setor_codes]
        return ', '.join(labels)

    def get_setor_display(self):
        return self.setores_display

    def save(self, *args, **kwargs):
        self.setor = self.setor_codes
        super().save(*args, **kwargs)
    
    @property
    def total_vagas(self):
        """Retorna o total de vagas publicadas"""
        return self.job_posts.count()
    
    @property
    def vagas_ativas(self):
        """Retorna o número de vagas ativas"""
        return self.job_posts.filter(estado='ATIVA').count()
    
    @property
    def total_candidaturas(self):
        """Retorna o total de candidaturas recebidas"""
        return Application.objects.filter(job__company=self).count()


class JobPost(models.Model):
    """Vagas de emprego/estágio/formação"""
    
    TIPO_CHOICES = [
        ('EST', _('Estágio')),
        ('EMP', _('Emprego')),
        ('FOR', _('Formação')),
    ]
    
    ESTADO_CHOICES = [
        ('ATIVA', _('Ativa')),
        ('FECHADA', _('Fechada')),
        ('PAUSADA', _('Pausada')),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='job_posts',
        verbose_name=_('empresa')
    )
    
    titulo = models.CharField(_('título'), max_length=255)
    descricao = models.TextField(_('descrição'))
    requisitos = models.TextField(_('requisitos'))
    tipo = models.CharField(_('tipo'), max_length=3, choices=TIPO_CHOICES)

    numero_vagas = models.PositiveIntegerField(
        _('número de vagas'),
        default=1
    )
    
    # Localização
    distrito = models.ForeignKey(
        'core.District',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('distrito')
    )
    local_trabalho = models.CharField(_('local de trabalho'), max_length=255, blank=True)
    
    # Requisitos específicos
    nivel_educacao = models.CharField(
        _('nível de educação requerido'),
        max_length=3,
        choices=settings.EDUCATION_LEVELS,
        blank=True
    )
    area_formacao = models.CharField(
        _('área de formação'),
        max_length=3,
        choices=settings.AREAS_FORMACAO,
        blank=True
    )
    experiencia_minima = models.IntegerField(
        _('experiência mínima (anos)'),
        default=0
    )
    
    # Detalhes
    salario = models.CharField(_('salário/remuneração'), max_length=255, blank=True)
    beneficios = models.TextField(_('benefícios'), blank=True)
    
    # Status
    estado = models.CharField(
        _('estado'),
        max_length=10,
        choices=ESTADO_CHOICES,
        default='ATIVA'
    )
    
    # Datas
    data_publicacao = models.DateTimeField(_('publicada em'), auto_now_add=True)
    data_fecho = models.DateField(_('data de fecho'), null=True, blank=True)
    
    # Contadores
    visualizacoes = models.PositiveIntegerField(_('visualizações'), default=0)
    
    class Meta:
        verbose_name = _('vaga')
        verbose_name_plural = _('vagas')
        ordering = ['-data_publicacao']
    
    def __str__(self):
        return f"{self.titulo} - {self.company.nome}"
    
    @property
    def total_candidaturas(self):
        """Retorna o total de candidaturas para esta vaga"""
        return self.applications.count()

    @property
    def vagas_preenchidas(self):
        """Retorna o número de candidaturas aceites"""
        if hasattr(self, 'aceites'):
            return self.aceites
        return self.applications.filter(estado='ACEITE').count()

    @property
    def vagas_restantes(self):
        """Retorna o número de vagas ainda disponíveis"""
        return max(self.numero_vagas - self.vagas_preenchidas, 0)

    @property
    def tem_vagas_disponiveis(self):
        """Indica se ainda há vagas disponíveis"""
        return self.vagas_restantes > 0
    
    def incrementar_visualizacoes(self):
        """Incrementa o contador de visualizações"""
        self.visualizacoes += 1
        self.save(update_fields=['visualizacoes'])


class Application(models.Model):
    """Candidaturas a vagas"""
    
    ESTADO_CHOICES = [
        ('PENDENTE', _('Pendente')),
        ('EM_ANALISE', _('Em Análise')),
        ('ACEITE', _('Aceite')),
        ('REJEITADA', _('Rejeitada')),
    ]
    
    job = models.ForeignKey(
        JobPost,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name=_('vaga')
    )
    youth = models.ForeignKey(
        'profiles.YouthProfile',
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name=_('jovem')
    )
    
    estado = models.CharField(
        _('estado'),
        max_length=15,
        choices=ESTADO_CHOICES,
        default='PENDENTE'
    )
    
    mensagem = models.TextField(_('mensagem/motivação'), blank=True)
    resposta_empresa = models.TextField(_('mensagem da empresa'), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('candidatou-se em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('atualizado em'), auto_now=True)
    
    class Meta:
        verbose_name = _('candidatura')
        verbose_name_plural = _('candidaturas')
        ordering = ['-created_at']
        unique_together = ['job', 'youth']
    
    def __str__(self):
        return f"{self.youth.user.nome} - {self.job.titulo}"


class ApplicationMessage(models.Model):
    """Mensagens trocadas na candidatura"""

    SENDER_CHOICES = [
        ('EMP', _('Empresa')),
        ('SYS', _('Sistema')),
    ]

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('candidatura')
    )
    sender = models.CharField(_('remetente'), max_length=3, choices=SENDER_CHOICES, default='EMP')
    message = models.TextField(_('mensagem'))
    created_at = models.DateTimeField(_('enviada em'), auto_now_add=True)

    class Meta:
        verbose_name = _('mensagem de candidatura')
        verbose_name_plural = _('mensagens de candidatura')
        ordering = ['-created_at']

    def __str__(self):
        return f"Mensagem {self.id} - {self.application}"


class ContactRequest(models.Model):
    """Pedidos de contacto de empresas para jovens"""
    
    ESTADO_CHOICES = [
        ('PENDENTE', _('Pendente')),
        ('APROVADO', _('Aprovado')),
        ('REJEITADO', _('Rejeitado')),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='contact_requests',
        verbose_name=_('empresa')
    )
    youth = models.ForeignKey(
        'profiles.YouthProfile',
        on_delete=models.CASCADE,
        related_name='contact_requests',
        verbose_name=_('jovem')
    )
    
    motivo = models.TextField(_('motivo do contacto'))
    estado = models.CharField(
        _('estado'),
        max_length=10,
        choices=ESTADO_CHOICES,
        default='PENDENTE'
    )
    
    # Resposta do admin
    resposta_admin = models.TextField(_('resposta do admin'), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('solicitado em'), auto_now_add=True)
    responded_at = models.DateTimeField(_('respondido em'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('pedido de contacto')
        verbose_name_plural = _('pedidos de contacto')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.nome} → {self.youth.user.nome}"
