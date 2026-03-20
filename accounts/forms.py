"""
Forms para autenticação e gestão de usuários
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """Formulário de registo de usuário"""
    
    PERFIL_CHOICES_PUBLIC = [
        ('JO', _('Jovem (Procuro oportunidades)')),
        ('EMP', _('Empresa (Quero publicar vagas)')),
    ]

    PERFIL_CHOICES_ADMIN = [
        ('JO', _('Jovem (Procuro oportunidades)')),
        ('EMP', _('Empresa (Quero publicar vagas)')),
        ('OP', _('Operador Distrital')),
        ('TEC', _('Técnico PNUD')),
    ]
    
    perfil = forms.ChoiceField(
        choices=PERFIL_CHOICES_PUBLIC,
        widget=forms.RadioSelect,
        label=_('Tipo de perfil')
    )
    
    nome = forms.CharField(
        max_length=255,
        label=_('Nome completo'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Seu nome completo')
        })
    )
    
    telefone = forms.CharField(
        max_length=20,
        label=_('Telemóvel'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ex: +239 123 4567')
        })
    )
    
    email = forms.EmailField(
        required=False,
        label=_('Email (opcional)'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('seu@email.com')
        })
    )

    nif = forms.CharField(
        max_length=20,
        required=False,
        label=_('NIF'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('NIF da empresa')
        })
    )

    bi_numero = forms.CharField(
        max_length=50,
        required=False,
        label=_('Número do BI'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Número do Bilhete de Identidade')
        })
    )

    photo = forms.ImageField(
        required=False,
        label=_('Foto (opcional)'),
        widget=forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'})
    )
    
    consentimento_dados = forms.BooleanField(
        required=True,
        label=_('Autorizo o uso dos meus dados para fins de empregabilidade'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    consentimento_contacto = forms.BooleanField(
        required=True,
        label=_('Autorizo ser contactado por SMS/WhatsApp/email'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    password1 = forms.CharField(
        label=_('Palavra-passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Mínimo 8 caracteres')
        })
    )
    
    password2 = forms.CharField(
        label=_('Confirmar palavra-passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Repita a palavra-passe')
        })
    )
    
    class Meta:
        model = User
        fields = ['perfil', 'nome', 'telefone', 'email', 'nif', 'bi_numero', 'password1', 'password2',
                  'consentimento_dados', 'consentimento_contacto']
    
    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.request_user and getattr(self.request_user, 'is_admin', False):
            self.fields['perfil'].choices = self.PERFIL_CHOICES_ADMIN
        else:
            self.fields['perfil'].choices = self.PERFIL_CHOICES_PUBLIC

        perfil_data = self.data.get('perfil') if self.is_bound else None
        if self.request_user and getattr(self.request_user, 'is_admin', False) and perfil_data in {'OP', 'TEC'}:
            self.fields['consentimento_dados'].required = False
            self.fields['consentimento_contacto'].required = False

    def clean_perfil(self):
        perfil = self.cleaned_data.get('perfil')
        if self.request_user and getattr(self.request_user, 'is_admin', False):
            allowed = {choice[0] for choice in self.PERFIL_CHOICES_ADMIN}
        else:
            allowed = {choice[0] for choice in self.PERFIL_CHOICES_PUBLIC}
        if perfil not in allowed:
            raise forms.ValidationError(_('Tipo de perfil inválido.'))
        return perfil

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if User.objects.filter(telefone=telefone).exists():
            raise forms.ValidationError(_('Este telemóvel já está registado.'))
        return telefone

    def clean_nif(self):
        nif = (self.cleaned_data.get('nif') or '').strip()
        if nif and User.objects.filter(nif__iexact=nif).exists():
            raise forms.ValidationError(_('Este NIF já está registado.'))
        return nif

    def clean_bi_numero(self):
        bi_numero = (self.cleaned_data.get('bi_numero') or '').strip()
        if bi_numero and User.objects.filter(bi_numero__iexact=bi_numero).exists():
            raise forms.ValidationError(_('Este número de BI já está registado.'))
        return bi_numero

    def clean(self):
        cleaned_data = super().clean()
        perfil = cleaned_data.get('perfil')
        nif = (cleaned_data.get('nif') or '').strip()
        bi_numero = (cleaned_data.get('bi_numero') or '').strip()

        if perfil == 'EMP' and not nif:
            self.add_error('nif', _('O NIF é obrigatório para empresas.'))

        if perfil == 'JO' and not bi_numero:
            self.add_error('bi_numero', _('O número do BI é obrigatório para candidatos.'))

        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        perfil = self.cleaned_data['perfil']
        nome = (self.cleaned_data.get('nome') or '').strip()

        user.nome = nome
        user.perfil = perfil
        user.consentimento_dados = self.cleaned_data.get('consentimento_dados', False)
        user.consentimento_contacto = self.cleaned_data.get('consentimento_contacto', False)
        user.nome_empresa = ''
        user.nif = ''
        user.bi_numero = ''

        if perfil == 'EMP':
            user.nome_empresa = nome
            user.nif = self.cleaned_data.get('nif', '')
        elif perfil == 'JO':
            user.bi_numero = self.cleaned_data.get('bi_numero', '')
        
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    """Formulário de login"""
    
    username = forms.CharField(
        label=_('Telemóvel ou Email'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Seu telemóvel ou email')
        })
    )
    
    password = forms.CharField(
        label=_('Palavra-passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Sua palavra-passe')
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        label=_('Lembrar-me'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class PasswordResetRequestForm(forms.Form):
    """Formulário para solicitar recuperação de senha"""
    
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Seu email registado')
        })
    )


class PasswordResetConfirmForm(forms.Form):
    """Formulário para confirmar recuperação de senha"""
    
    code = forms.CharField(
        max_length=6,
        label=_('Código de verificação'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('6 dígitos')
        })
    )
    
    new_password = forms.CharField(
        label=_('Nova palavra-passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Mínimo 8 caracteres')
        })
    )
    
    confirm_password = forms.CharField(
        label=_('Confirmar palavra-passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Repita a palavra-passe')
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError(_('As palavras-passe não coincidem.'))
        
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    """Formulário para editar perfil do usuário"""
    
    class Meta:
        model = User
        fields = ['nome', 'email', 'telefone', 'distrito']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'distrito': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if not telefone:
            return telefone
        qs = User.objects.filter(telefone=telefone)
        if self.instance and getattr(self.instance, 'pk', None):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('Este telemóvel já está registado.'))
        return telefone


class AdminUserUpdateForm(forms.ModelForm):
    'Formulário do admin para editar dados principais de um utilizador.'

    nif = forms.CharField(
        max_length=20,
        required=False,
        label=_('NIF'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    bi_numero = forms.CharField(
        max_length=50,
        required=False,
        label=_('Número do BI'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    consentimento_dados = forms.BooleanField(
        required=False,
        label=_('Autorizo o uso dos meus dados para fins de empregabilidade'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    consentimento_contacto = forms.BooleanField(
        required=False,
        label=_('Autorizo ser contactado por SMS/WhatsApp/email'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = [
            'nome',
            'telefone',
            'email',
            'distrito',
            'nif',
            'bi_numero',
            'consentimento_dados',
            'consentimento_contacto',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'distrito': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_telefone(self):
        telefone = (self.cleaned_data.get('telefone') or '').strip()
        qs = User.objects.filter(telefone=telefone)
        if self.instance and getattr(self.instance, 'pk', None):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('Este telemóvel já esta registado.'))
        return telefone

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return None
        qs = User.objects.filter(email__iexact=email)
        if self.instance and getattr(self.instance, 'pk', None):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('Este email já esta registado.'))
        return email

    def clean_nif(self):
        nif = (self.cleaned_data.get('nif') or '').strip()
        if not nif:
            return ''
        qs = User.objects.filter(nif__iexact=nif)
        if self.instance and getattr(self.instance, 'pk', None):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('Este NIF já esta registado.'))
        return nif

    def clean_bi_numero(self):
        bi_numero = (self.cleaned_data.get('bi_numero') or '').strip()
        if not bi_numero:
            return ''
        qs = User.objects.filter(bi_numero__iexact=bi_numero)
        if self.instance and getattr(self.instance, 'pk', None):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('Este número de BI já esta registado.'))
        return bi_numero

    def clean(self):
        cleaned_data = super().clean()
        perfil = self.instance.perfil
        nif = (cleaned_data.get('nif') or '').strip()
        bi_numero = (cleaned_data.get('bi_numero') or '').strip()

        if perfil == User.ProfileType.EMPRESA and not nif:
            self.add_error('nif', _('O NIF é obrigatório para empresas.'))

        if perfil == User.ProfileType.JOVEM and not bi_numero:
            self.add_error('bi_numero', _('O número do BI é obrigatório para candidatos.'))

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.nome = (self.cleaned_data.get('nome') or '').strip()
        user.telefone = (self.cleaned_data.get('telefone') or '').strip()
        user.email = self.cleaned_data.get('email') or None
        user.consentimento_dados = self.cleaned_data.get('consentimento_dados', False)
        user.consentimento_contacto = self.cleaned_data.get('consentimento_contacto', False)

        if user.is_empresa:
            user.nome_empresa = user.nome
            user.nif = self.cleaned_data.get('nif', '')
            user.bi_numero = ''
        elif user.is_jovem:
            user.nome_empresa = ''
            user.nif = ''
            user.bi_numero = self.cleaned_data.get('bi_numero', '')
        else:
            user.nome_empresa = ''
            user.nif = ''
            user.bi_numero = ''

        if commit:
            user.save()
            if user.is_empresa:
                from companies.models import Company

                if user.has_company_profile():
                    company = user.company_profile
                    company.nome = user.nome
                    company.nif = user.nif
                    company.telefone = user.telefone or ''
                    company.email = user.email or ''
                    company.distrito = user.distrito
                    company.save()
                else:
                    company = Company.objects.create(
                        user=user,
                        nome=user.nome,
                        nif=user.nif,
                        setor=[],
                        telefone=user.telefone or '',
                        email=user.email or '',
                        distrito=user.distrito,
                    )
                setores_display = company.setores_display
                if user.setor_empresa != setores_display:
                    user.setor_empresa = setores_display
                    user.save(update_fields=['setor_empresa'])
        return user

class OperadorRegistrationForm(UserCreationForm):
    """Formulário para registar operador distrital (apenas admin)"""
    
    nome = forms.CharField(max_length=255, label=_('Nome completo'))
    telefone = forms.CharField(max_length=20, label=_('Telemóvel'))
    email = forms.EmailField(required=False, label=_('Email'))
    associacao_parceira = forms.CharField(
        max_length=255,
        label=_('Associação/Parceiro'),
        required=False
    )
    distrito = forms.ModelChoiceField(
        queryset=None,
        label=_('Distrito'),
        required=False
    )
    
    class Meta:
        model = User
        fields = ['nome', 'telefone', 'email', 'associacao_parceira', 'distrito',
                  'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import District
        self.fields['distrito'].queryset = District.objects.all()
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.perfil = 'OP'
        user.associacao_parceira = self.cleaned_data.get('associacao_parceira')
        if commit:
            user.save()
        return user
