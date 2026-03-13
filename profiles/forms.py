"""
Forms para perfis de jovens
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import YouthProfile, Education, Experience, Document, YouthSkill
from core.models import Skill


class YouthProfileStep1Form(forms.ModelForm):
    """Passo 1: Dados Pessoais"""
    
    data_nascimento = forms.DateField(
        label=_('Data de nascimento'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
    
    sexo = forms.ChoiceField(
        choices=YouthProfile.SEXO_CHOICES,
        label=_('Sexo'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    localidade = forms.CharField(
        label=_('Localidade'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Sua localidade')
        }),
        required=False
    )
    
    class Meta:
        model = YouthProfile
        fields = ['data_nascimento', 'sexo', 'localidade']


class YouthProfileStep2Form(forms.ModelForm):
    """Passo 2: Educação e Skills"""
    
    # Educação
    nivel = forms.ChoiceField(
        choices=Education.NIVEL_CHOICES,
        label=_('Nível de educação'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    area_formacao = forms.ChoiceField(
        choices=[('', _('Selecione...'))] + list(forms.fields.ChoiceField(
            choices=[
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
        ).choices),
        label=_('Área de formação'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    instituicao = forms.CharField(
        label=_('Instituição'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Nome da escola/instituição')
        }),
        required=False
    )
    
    ano = forms.IntegerField(
        label=_('Ano de conclusão'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ex: 2023'),
            'min': 1950,
            'max': 2030
        }),
        required=False
    )
    
    curso = forms.CharField(
        label=_('Curso/Especialidade'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Nome do curso')
        }),
        required=False
    )
    
    # Skills (múltipla escolha)
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        label=_('Skills/Competências'),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = YouthProfile
        fields = ['nivel', 'area_formacao', 'instituicao', 'ano', 'curso', 'skills']


class YouthProfileStep3Form(forms.ModelForm):
    """Passo 3: Experiência e Interesses"""
    
    situacao_atual = forms.ChoiceField(
        choices=YouthProfile.SITUACAO_CHOICES,
        label=_('Situação atual'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    disponibilidade = forms.ChoiceField(
        choices=YouthProfile.DISPONIBILIDADE_CHOICES,
        label=_('Disponibilidade imediata'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    interesse_setorial = forms.ChoiceField(
        choices=[('', _('Selecione...'))] + list(forms.fields.ChoiceField(
            choices=[
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
                ('OUT', _('Outro')),
            ]
        ).choices),
        label=_('Setor de interesse'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    preferencia_oportunidade = forms.ChoiceField(
        choices=YouthProfile.OPORTUNIDADE_CHOICES,
        label=_('Tipo de oportunidade preferida'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sobre = forms.CharField(
        label=_('Sobre mim'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Fale um pouco sobre ti, tuas aspirações e objetivos profissionais...')
        }),
        required=False
    )
    
    # Experiência (opcional)
    tem_experiencia = forms.BooleanField(
        label=_('Tenho experiência profissional'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    exp_entidade = forms.CharField(
        label=_('Empresa/Entidade'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Nome da empresa')
        }),
        required=False
    )
    
    exp_cargo = forms.CharField(
        label=_('Cargo/Função'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Seu cargo')
        }),
        required=False
    )
    
    exp_descricao = forms.CharField(
        label=_('Descrição das atividades'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Descreve as tuas principais atividades...')
        }),
        required=False
    )
    
    class Meta:
        model = YouthProfile
        fields = [
            'situacao_atual', 'disponibilidade', 'interesse_setorial',
            'preferencia_oportunidade', 'sobre'
        ]


class YouthProfileStep4Form(forms.ModelForm):
    """Passo 4: Documentos e Consentimentos"""
    
    # Documentos
    cv = forms.FileField(
        label=_('Curriculum Vitae (PDF)'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf'
        }),
        required=False
    )
    
    certificado = forms.FileField(
        label=_('Certificado (PDF ou imagem)'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        required=False
    )
    
    bi = forms.FileField(
        label=_('Bilhete de Identidade (opcional)'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        required=False
    )
    
    # Consentimentos
    visivel = forms.BooleanField(
        label=_('Tornar o meu perfil visível para empresas'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        initial=True,
        required=False
    )
    
    class Meta:
        model = YouthProfile
        fields = ['visivel']


class AssistedRegistrationForm(forms.Form):
    """Formulário simplificado para registo assistido (Operador Distrital)"""
    
    # Dados do jovem
    nome = forms.CharField(
        label=_('Nome completo'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Nome completo do jovem')
        })
    )
    
    telefone = forms.CharField(
        label=_('Telemóvel'),
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ex: +239 123 4567')
        })
    )
    
    email = forms.EmailField(
        label=_('Email (opcional)'),
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('email@exemplo.com')
        })
    )
    
    data_nascimento = forms.DateField(
        label=_('Data de nascimento'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    sexo = forms.ChoiceField(
        label=_('Sexo'),
        choices=YouthProfile.SEXO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    distrito = forms.ModelChoiceField(
        label=_('Distrito'),
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    localidade = forms.CharField(
        label=_('Localidade'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Localidade')
        })
    )
    
    # Educação
    nivel = forms.ChoiceField(
        label=_('Nível de educação'),
        choices=Education.NIVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    area_formacao = forms.ChoiceField(
        label=_('Área de formação'),
        choices=[
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
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    situacao_atual = forms.ChoiceField(
        label=_('Situação atual'),
        choices=YouthProfile.SITUACAO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    disponibilidade = forms.ChoiceField(
        label=_('Disponibilidade'),
        choices=YouthProfile.DISPONIBILIDADE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    preferencia_oportunidade = forms.ChoiceField(
        label=_('Tipo de oportunidade preferida'),
        choices=YouthProfile.OPORTUNIDADE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    observacoes = forms.CharField(
        label=_('Observações'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Observações adicionais...')
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import District
        self.fields['distrito'].queryset = District.objects.all()


class YouthProfileEditForm(forms.ModelForm):
    """Formulário para editar perfil do jovem"""
    
    class Meta:
        model = YouthProfile
        fields = [
            'data_nascimento', 'sexo', 'localidade',
            'photo',
            'situacao_atual', 'disponibilidade',
            'interesse_setorial', 'preferencia_oportunidade',
            'sobre', 'visivel'
        ]
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'localidade': forms.TextInput(attrs={'class': 'form-control'}),
            'situacao_atual': forms.Select(attrs={'class': 'form-select'}),
            'disponibilidade': forms.Select(attrs={'class': 'form-select'}),
            'interesse_setorial': forms.Select(attrs={'class': 'form-select'}),
            'preferencia_oportunidade': forms.Select(attrs={'class': 'form-select'}),
            'sobre': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'visivel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
        }


class EducationForm(forms.ModelForm):
    """Formulário para adicionar formação"""
    
    class Meta:
        model = Education
        fields = ['nivel', 'area_formacao', 'instituicao', 'ano', 'curso']
        widgets = {
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'area_formacao': forms.Select(attrs={'class': 'form-select'}),
            'instituicao': forms.TextInput(attrs={'class': 'form-control'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': 1950, 'max': 2030}),
            'curso': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ExperienceForm(forms.ModelForm):
    """Formulário para adicionar experiência"""
    
    class Meta:
        model = Experience
        fields = ['entidade', 'cargo', 'inicio', 'fim', 'atual', 'descricao']
        widgets = {
            'entidade': forms.TextInput(attrs={'class': 'form-control'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'atual': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DocumentForm(forms.ModelForm):
    """Formulário para adicionar documento"""
    
    class Meta:
        model = Document
        fields = ['tipo', 'nome', 'arquivo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control'}),
        }
