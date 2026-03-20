"""
Forms para perfis de jovens
"""

import re
import unicodedata

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .models import YouthProfile, Education, Experience, Document, YouthSkill
from core.models import Skill, District


def _normalize_sector_search_value(value):
    normalized = unicodedata.normalize('NFKD', str(value or '').strip())
    return ''.join(char for char in normalized if not unicodedata.combining(char)).lower()


def _build_sector_lookup():
    lookup = {}
    for code, label in getattr(settings, 'AREAS_FORMACAO', []):
        lookup[_normalize_sector_search_value(code)] = code
        lookup[_normalize_sector_search_value(label)] = code
    return lookup


def normalize_custom_sector_values(raw_value):
    if not raw_value:
        return []

    lookup = _build_sector_lookup()
    values = []
    for item in re.split(r'[\r\n,;]+', str(raw_value)):
        cleaned = ' '.join(item.split()).strip()
        if not cleaned:
            continue
        values.append(lookup.get(_normalize_sector_search_value(cleaned), cleaned))
    return list(dict.fromkeys(values))


def split_known_and_custom_sectors(values):
    valid_codes = {code for code, _label in getattr(settings, 'AREAS_FORMACAO', [])}
    lookup = _build_sector_lookup()
    selected = []
    custom = []

    if isinstance(values, str):
        values = [values]
    elif not values:
        values = []

    for value in values:
        cleaned = ' '.join(str(value or '').split()).strip()
        if not cleaned:
            continue
        mapped_value = lookup.get(_normalize_sector_search_value(cleaned), cleaned)
        if mapped_value in valid_codes:
            selected.append(mapped_value)
        else:
            custom.append(mapped_value)

    return list(dict.fromkeys(selected)), list(dict.fromkeys(custom))


def combine_interest_sector_values(selected_values, raw_custom_values):
    selected = [value for value in (selected_values or []) if value]
    custom = normalize_custom_sector_values(raw_custom_values)
    if custom:
        selected = [value for value in selected if value != 'OUT']
    return list(dict.fromkeys(selected + custom))


class YouthProfileStep1Form(forms.ModelForm):
    """Passo 1: Dados Pessoais"""

    nome = forms.CharField(
        label=_('Nome completo'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Seu nome completo')
        })
    )

    telefone = forms.CharField(
        label=_('Telemóvel'),
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ex: +239 123 4567'),
            'readonly': 'readonly'
        })
    )

    email = forms.EmailField(
        label=_('Email'),
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('email@exemplo.com')
        })
    )

    contacto_alternativo = forms.CharField(
        label=_('Contacto alternativo'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ex: contacto de familiar, vizinho ou outro')
        })
    )

    distrito = forms.ModelChoiceField(
        label=_('Distrito'),
        queryset=District.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_('Selecione...'),
        required=True
    )
    
    data_nascimento = forms.DateField(
        label=_('Data de nascimento'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=True
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
        fields = ['data_nascimento', 'sexo', 'localidade', 'contacto_alternativo']


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
        queryset=Skill.objects.none(),
        label=_('Skills/Competências'),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    outra_skill_nome = forms.CharField(
        label=_('Outra skill'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Escreve uma skill que não estejá na lista')
        })
    )

    outra_skill_tipo = forms.ChoiceField(
        choices=[('', _('Selecione...'))] + list(Skill.TIPO_CHOICES),
        label=_('Tipo de skill'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = YouthProfile
        fields = ['nivel', 'area_formacao', 'instituicao', 'ano', 'curso', 'skills', 'outra_skill_nome', 'outra_skill_tipo']



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].queryset = Skill.objects.filter(aprovada=True).order_by('nome')


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
    
    interesse_setorial = forms.MultipleChoiceField(
        choices=getattr(settings, 'AREAS_FORMACAO', []),
        label=_('Setores de interesse'),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    outros_setores_interesse = forms.CharField(
        label=_('Outro setor de interesse'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Se não encontrares na lista, escreve um ou mais setores separados por virgulas')
        })
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

    exp_inicio = forms.DateField(
        label=_('Data de início'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    exp_fim = forms.DateField(
        label=_('Data de fim'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    exp_atual = forms.BooleanField(
        label=_('Trabalho atual'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = YouthProfile
        fields = [
            'situacao_atual', 'disponibilidade', 'interesse_setorial',
            'preferencia_oportunidade', 'sobre'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_values = self.initial.get('interesse_setorial')
        if current_values is None and getattr(self.instance, 'pk', None):
            current_values = self.instance.interesse_setorial

        selected, custom = split_known_and_custom_sectors(current_values)
        self.initial['interesse_setorial'] = selected
        self.initial['outros_setores_interesse'] = ', '.join(custom)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['interesse_setorial'] = combine_interest_sector_values(
            cleaned_data.get('interesse_setorial'),
            cleaned_data.get('outros_setores_interesse'),
        )
        tem_experiencia = cleaned_data.get('tem_experiencia')
        if tem_experiencia:
            exp_entidade = cleaned_data.get('exp_entidade')
            exp_cargo = cleaned_data.get('exp_cargo')
            exp_inicio = cleaned_data.get('exp_inicio')
            exp_fim = cleaned_data.get('exp_fim')
            exp_atual = cleaned_data.get('exp_atual')

            if not exp_entidade:
                self.add_error('exp_entidade', _('Indica a entidade/empresa.'))
            if not exp_cargo:
                self.add_error('exp_cargo', _('Indica o cargo/função.'))
            if not exp_inicio:
                self.add_error('exp_inicio', _('Indica a data de início.'))
            if not exp_atual and not exp_fim:
                self.add_error('exp_fim', _('Indica a data de fim ou marca como trabalho atual.'))
            if exp_inicio and exp_fim and exp_fim < exp_inicio:
                self.add_error('exp_fim', _('A data de fim deve ser igual ou posterior à data de início.'))

        return cleaned_data


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
        label=_('Autorizo a partilha do meu perfil com empresas'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        initial=True,
        required=False
    )

    consentimento_sms = forms.BooleanField(
        label=_('Autorizo contacto por SMS'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )

    consentimento_whatsapp = forms.BooleanField(
        label=_('Autorizo contacto por WhatsApp'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )

    consentimento_email = forms.BooleanField(
        label=_('Autorizo contacto por Email'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    class Meta:
        model = YouthProfile
        fields = ['visivel', 'consentimento_sms', 'consentimento_whatsapp', 'consentimento_email']


class YouthSkillsForm(forms.Form):
    """Formulário para editar skills do jovem"""
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.none(),
        label=_('Skills/Competências'),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    outra_skill_nome = forms.CharField(
        label=_('Outra skill'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Escreve uma skill que não estejá na lista')
        })
    )
    outra_skill_tipo = forms.ChoiceField(
        choices=[('', _('Selecione...'))] + list(Skill.TIPO_CHOICES),
        label=_('Tipo de skill'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, include_skill_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Skill.objects.filter(aprovada=True)
        if include_skill_ids:
            qs = qs | Skill.objects.filter(id__in=include_skill_ids)
        self.fields['skills'].queryset = qs.distinct().order_by('nome')



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

    interesse_setorial = forms.MultipleChoiceField(
        choices=getattr(settings, 'AREAS_FORMACAO', []),
        label=_('Setores de interesse'),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    outros_setores_interesse = forms.CharField(
        label=_('Outro setor de interesse'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Se não encontrares na lista, escreve um ou mais setores separados por virgulas')
        })
    )
    
    class Meta:
        model = YouthProfile
        fields = [
            'data_nascimento', 'sexo', 'localidade', 'contacto_alternativo',
            'photo',
            'situacao_atual', 'disponibilidade',
            'interesse_setorial', 'preferencia_oportunidade',
            'sobre', 'visivel', 'consentimento_sms', 'consentimento_whatsapp', 'consentimento_email'
        ]
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'localidade': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto_alternativo': forms.TextInput(attrs={'class': 'form-control'}),
            'situacao_atual': forms.Select(attrs={'class': 'form-select'}),
            'disponibilidade': forms.Select(attrs={'class': 'form-select'}),
            'interesse_setorial': forms.CheckboxSelectMultiple,
            'preferencia_oportunidade': forms.Select(attrs={'class': 'form-select'}),
            'sobre': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'visivel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'consentimento_sms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'consentimento_whatsapp': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'consentimento_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_values = self.initial.get('interesse_setorial')
        if current_values is None and getattr(self.instance, 'pk', None):
            current_values = self.instance.interesse_setorial

        selected, custom = split_known_and_custom_sectors(current_values)
        self.initial['interesse_setorial'] = selected
        self.initial['outros_setores_interesse'] = ', '.join(custom)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['interesse_setorial'] = combine_interest_sector_values(
            cleaned_data.get('interesse_setorial'),
            cleaned_data.get('outros_setores_interesse'),
        )
        return cleaned_data


class EducationForm(forms.ModelForm):
    """Formulário para adicionar formação"""
    
    class Meta:
        model = Education
        fields = ['nivel', 'area_formacao', 'instituicao', 'ano', 'curso']
        widgets = {
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'area_formacao': forms.Select(attrs={'class': 'form-select'}),
            'instituicao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Nome da escola, centro ou instituição')}),
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': 1950, 'max': 2030, 'placeholder': _('Ex: 2024')}),
            'curso': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Curso, especialidade ou área principal')}),
        }


class ExperienceForm(forms.ModelForm):
    """Formulário para adicionar experiência"""
    
    class Meta:
        model = Experience
        fields = ['entidade', 'cargo', 'inicio', 'fim', 'atual', 'descricao']
        widgets = {
            'entidade': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Nome da empresa, oficina, projeto ou instituição')}),
            'cargo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Cargo, função ou papel desempenhado')}),
            'inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'atual': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': _('Resume as principais tarefas, responsabilidades e resultados desta experiência')}),
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
