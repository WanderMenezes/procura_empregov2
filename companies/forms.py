"""
Forms para empresas
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Company, JobPost, ContactRequest
from core.models import District, Skill
from django.core.exceptions import ValidationError
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
import os
from django.conf import settings


class CompanyProfileForm(forms.ModelForm):
    """Formulário para completar perfil da empresa"""
    
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
    
    nome = forms.CharField(
        label=_('Nome da empresa'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Nome da empresa')
        })
    )
    
    nif = forms.CharField(
        label=_('NIF (opcional)'),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Número de identificação fiscal')
        })
    )
    
    setor = forms.MultipleChoiceField(
        label=_('Setores de atividade'),
        choices=Company.SETOR_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        help_text=_('Pode selecionar mais do que um setor.')
    )
    
    descricao = forms.CharField(
        label=_('Descrição da empresa'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Descreva a sua empresa...')
        })
    )
    
    telefone = forms.CharField(
        label=_('Telefone de contacto'),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Telefone para contacto')
        })
    )
    
    email = forms.EmailField(
        label=_('Email de contacto'),
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('email@empresa.com')
        })
    )
    
    website = forms.URLField(
        label=_('Website (opcional)'),
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': _('https://www.empresa.com')
        })
    )
    
    distrito = forms.ModelChoiceField(
        label=_('Distrito'),
        queryset=District.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    endereco = forms.CharField(
        label=_('Endereço'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': _('Endereço da empresa')
        })
    )

    logo = forms.ImageField(
        label=_('Logo (opcional)'),
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'})
    )
    
    class Meta:
        model = Company
        fields = [
            'nome', 'nif', 'setor', 'descricao',
            'telefone', 'email', 'website',
            'distrito', 'endereco', 'logo'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setor_value = self.initial.get('setor')
        if setor_value is None and getattr(self.instance, 'pk', None):
            setor_value = self.instance.setor

        if isinstance(setor_value, str):
            self.initial['setor'] = [setor_value] if setor_value else []
        elif setor_value is None:
            self.initial['setor'] = []

    def clean_setor(self):
        setores = self.cleaned_data.get('setor') or []
        if not setores:
            raise ValidationError(_('Selecione pelo menos um setor de atividade.'))
        return list(dict.fromkeys(setores))

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo:
            # tamanho máximo configurável em MB
            max_size = getattr(settings, 'COMPANY_LOGO_MAX_SIZE_MB', 2) * 1024 * 1024
            if logo.size > max_size:
                raise ValidationError(_('A imagem é demasiado grande (máx. %(mb)dMB).') % {'mb': getattr(settings, 'COMPANY_LOGO_MAX_SIZE_MB', 2)})

            # tipos permitidos
            content_type = getattr(logo, 'content_type', '')
            if not content_type.startswith('image/'):
                raise ValidationError(_('Formato inválido. Envie uma imagem PNG/JPEG/GIF.'))

        return logo

    def _process_logo_file(self, uploaded_file, max_size=None):
        try:
            image = Image.open(uploaded_file)
        except Exception:
            raise ValidationError(_('Não foi possível processar a imagem.'))

        # Converter para RGB se necessário (para salvar como JPEG)
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        else:
            image = image.convert('RGB')

        if max_size is None:
            max_size = getattr(settings, 'COMPANY_LOGO_MAX_DIM', (512, 512))

        # escolher filtro de redimensionamento compatível com várias versões do Pillow
        if hasattr(Image, 'Resampling'):
            resample = Image.Resampling.LANCZOS
        elif hasattr(Image, 'LANCZOS'):
            resample = Image.LANCZOS
        else:
            resample = Image.BICUBIC

        image.thumbnail(max_size, resample)

        buffer = BytesIO()
        quality = getattr(settings, 'COMPANY_LOGO_QUALITY', 85)
        image.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)

        base_name = os.path.splitext(uploaded_file.name)[0]
        new_name = f"{base_name}.jpg"
        return ContentFile(buffer.read()), new_name

    def save(self, commit=True):
        instance = super().save(commit=False)

        logo = self.cleaned_data.get('logo')
        if logo:
            content, name = self._process_logo_file(logo)
            instance.logo.save(name, content, save=False)

        if commit:
            instance.save()

        return instance


class JobPostForm(forms.ModelForm):
    """Formulário para publicar vaga"""
    
    TIPO_CHOICES = [
        ('EST', _('Estágio')),
        ('EMP', _('Emprego')),
        ('FOR', _('Formação')),
    ]
    
    NIVEL_CHOICES = [
        ('', _('Qualquer')),
        ('BAS', _('Básico')),
        ('SEC', _('Secundário')),
        ('TEC', _('Técnico')),
        ('SUP', _('Superior')),
    ]
    
    AREA_CHOICES = [
        ('', _('Qualquer')),
        ('AGR', _('Agricultura')),
        ('TUR', _('Turismo')),
        ('TIC', _('Tecnologias de Informação')),
        ('IND', _('Indústria')),
        ('SER', _('Serviços')),
        ('ENE', _('Energias Renováveis')),
        ('ADM', _('Administração')),
        ('SAU', _('Saúde')),
        ('EDU', _('Educação')),
        ('CON', _('Construção')),
        ('ELE', _('Eletricidade')),
        ('CAN', _('Canalização')),
        ('INF', _('Informática')),
        ('OUT', _('Outra')),
    ]
    
    titulo = forms.CharField(
        label=_('Título da vaga'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ex: Técnico de Informática')
        })
    )
    
    descricao = forms.CharField(
        label=_('Descrição'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': _('Descreva a vaga, responsabilidades, ambiente de trabalho...')
        })
    )
    
    requisitos = forms.CharField(
        label=_('Requisitos'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Liste os requisitos necessários...')
        })
    )
    
    tipo = forms.ChoiceField(
        label=_('Tipo de oportunidade'),
        choices=TIPO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    numero_vagas = forms.IntegerField(
        label=_('Número de vagas'),
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 999
        })
    )
    
    distrito = forms.ModelChoiceField(
        label=_('Distrito'),
        queryset=District.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    local_trabalho = forms.CharField(
        label=_('Local de trabalho'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ex: São Tomé, Neves...')
        })
    )
    
    nivel_educacao = forms.ChoiceField(
        label=_('Nível de educação requerido'),
        choices=NIVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    area_formacao = forms.ChoiceField(
        label=_('Área de formação'),
        choices=AREA_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    experiencia_minima = forms.IntegerField(
        label=_('Experiência mínima (anos)'),
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'max': 50
        })
    )
    
    salario = forms.CharField(
        label=_('Salário/Remuneração (opcional)'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ex: A combinar, 5000 Dobra/mês...')
        })
    )
    
    beneficios = forms.CharField(
        label=_('Benefícios (opcional)'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Liste os benefícios oferecidos...')
        })
    )
    
    data_fecho = forms.DateField(
        label=_('Data de fecho (opcional)'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    class Meta:
        model = JobPost
        fields = [
            'titulo', 'descricao', 'requisitos', 'tipo', 'numero_vagas',
            'distrito', 'local_trabalho', 'nivel_educacao',
            'area_formacao', 'experiencia_minima',
            'salario', 'beneficios', 'data_fecho'
        ]


class ContactRequestForm(forms.ModelForm):
    """Formulário para solicitar contacto de jovem"""
    
    motivo = forms.CharField(
        label=_('Motivo do contacto'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Explique o motivo do contacto, tipo de oportunidade, etc...')
        })
    )
    
    class Meta:
        model = ContactRequest
        fields = ['motivo']


class YouthSearchForm(forms.Form):
    """Formulário de pesquisa de jovens"""
    
    NIVEL_CHOICES = [
        ('', _('Todos')),
        ('BAS', _('Básico')),
        ('SEC', _('Secundário')),
        ('TEC', _('Técnico')),
        ('SUP', _('Superior')),
    ]
    
    AREA_CHOICES = [
        ('', _('Todas')),
        ('AGR', _('Agricultura')),
        ('TUR', _('Turismo')),
        ('TIC', _('Tecnologias de Informação')),
        ('IND', _('Indústria')),
        ('SER', _('Serviços')),
        ('ENE', _('Energias Renováveis')),
        ('ADM', _('Administração')),
        ('SAU', _('Saúde')),
        ('EDU', _('Educação')),
        ('CON', _('Construção')),
        ('ELE', _('Eletricidade')),
        ('CAN', _('Canalização')),
        ('INF', _('Informática')),
        ('OUT', _('Outra')),
    ]
    
    DISPONIBILIDADE_CHOICES = [
        ('', _('Todas')),
        ('SIM', _('Sim')),
        ('NAO', _('Não')),
        ('EM_BREVE', _('Em breve')),
    ]
    
    q = forms.CharField(
        label=_('Palavra-chave'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Nome, skill, localidade...')
        })
    )
    profissao = forms.CharField(
        label=_('Profissão / Cargo'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Ex: Técnico, Carpinteiro')})
    )

    skills = forms.ModelChoiceField(
        label=_('Skill'),
        queryset=Skill.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    distrito = forms.ModelChoiceField(
        label=_('Distrito'),
        queryset=District.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    distrito = forms.ModelChoiceField(
        label=_('Distrito'),
        queryset=District.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    nivel = forms.ChoiceField(
        label=_('Nível de educação'),
        choices=NIVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    area = forms.ChoiceField(
        label=_('Área de formação'),
        choices=AREA_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    disponibilidade = forms.ChoiceField(
        label=_('Disponibilidade'),
        choices=DISPONIBILIDADE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    com_experiencia = forms.BooleanField(
        label=_('Apenas com experiência'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].queryset = Skill.objects.filter(aprovada=True).order_by('nome')
