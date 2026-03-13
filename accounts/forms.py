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
    
    PERFIL_CHOICES = [
        ('JO', _('Jovem (Procuro oportunidades)')),
        ('EMP', _('Empresa (Quero publicar vagas)')),
    ]
    
    perfil = forms.ChoiceField(
        choices=PERFIL_CHOICES,
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
        fields = ['perfil', 'nome', 'telefone', 'email', 'password1', 'password2',
                  'consentimento_dados', 'consentimento_contacto']
    
    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if User.objects.filter(telefone=telefone).exists():
            raise forms.ValidationError(_('Este telemóvel já está registado.'))
        return telefone
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.perfil = self.cleaned_data['perfil']
        user.consentimento_dados = self.cleaned_data['consentimento_dados']
        user.consentimento_contacto = self.cleaned_data['consentimento_contacto']
        
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
    
    telefone = forms.CharField(
        max_length=20,
        label=_('Telemóvel'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Seu telemóvel registado')
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
