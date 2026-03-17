"""
Core models para a Base Nacional de Jovens
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import json


class District(models.Model):
    """Distritos de São Tomé e Príncipe"""
    codigo = models.CharField(_('código'), max_length=3, unique=True)
    nome = models.CharField(_('nome'), max_length=100)
    
    class Meta:
        verbose_name = _('distrito')
        verbose_name_plural = _('distritos')
        ordering = ['nome']
    
    def __str__(self):
        return self.nome


class Skill(models.Model):
    """Skills/Competências disponíveis"""
    
    TIPO_CHOICES = [
        ('TEC', _('Técnica')),
        ('TRA', _('Transversal')),
    ]
    
    nome = models.CharField(_('nome'), max_length=100)
    tipo = models.CharField(_('tipo'), max_length=3, choices=TIPO_CHOICES, default='TEC')
    aprovada = models.BooleanField(_('aprovada'), default=False)
    descricao = models.TextField(_('descrição'), blank=True)
    
    class Meta:
        verbose_name = _('skill')
        verbose_name_plural = _('skills')
        ordering = ['nome']
    
    def __str__(self):
        return self.nome


class AuditLog(models.Model):
    """Logs de auditoria para rastreamento de ações"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('utilizador')
    )
    acao = models.CharField(_('ação'), max_length=255)
    payload = models.JSONField(_('dados'), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(_('endereço IP'), null=True, blank=True)
    created_at = models.DateTimeField(_('data/hora'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('log de auditoria')
        verbose_name_plural = _('logs de auditoria')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.acao} - {self.user} - {self.created_at}"


class Notification(models.Model):
    """Notificações para usuários"""
    
    TIPO_CHOICES = [
        ('INFO', _('Informação')),
        ('SUCESSO', _('Sucesso')),
        ('ALERTA', _('Alerta')),
        ('ERRO', _('Erro')),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('utilizador')
    )
    titulo = models.CharField(_('título'), max_length=255)
    mensagem = models.TextField(_('mensagem'))
    tipo = models.CharField(_('tipo'), max_length=10, choices=TIPO_CHOICES, default='INFO')
    lida = models.BooleanField(_('lida'), default=False)
    created_at = models.DateTimeField(_('criada em'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('notificação')
        verbose_name_plural = _('notificações')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.titulo} - {self.user.nome}"


class SiteConfig(models.Model):
    """Configurações do site"""
    chave = models.CharField(_('chave'), max_length=100, unique=True)
    valor = models.TextField(_('valor'))
    descricao = models.TextField(_('descrição'), blank=True)
    
    class Meta:
        verbose_name = _('configuração')
        verbose_name_plural = _('configurações')
    
    def __str__(self):
        return self.chave
    
    @classmethod
    def get(cls, chave, default=None):
        """Obtém uma configuração pelo valor"""
        try:
            return cls.objects.get(chave=chave).valor
        except cls.DoesNotExist:
            return default
