from django import forms
from django.utils.translation import gettext_lazy as _

class OfflineRegistrationExportForm(forms.Form):
    PROFILE_CHOICES = [
        ('JO', _('Jovem')),
        ('EMP', _('Empresa')),
    ]

    profile_type = forms.ChoiceField(
        choices=PROFILE_CHOICES,
        label=_('Tipo de registo offline'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class OfflineRegistrationImportForm(forms.Form):
    file = forms.FileField(
        label=_('Ficheiro de importacao gerado pelo formulario offline'),
        widget=forms.ClearableFileInput(
            attrs={
                'class': 'form-control',
                'accept': '.json,application/json',
            }
        ),
    )

    def clean_file(self):
        uploaded = self.cleaned_data['file']
        if uploaded.size > 1024 * 1024:
            raise forms.ValidationError(_('O ficheiro offline nao pode ultrapassar 1 MB.'))
        if not uploaded.name.lower().endswith('.json'):
            raise forms.ValidationError(_('Importe o ficheiro JSON gerado pelo formulario offline.'))
        return uploaded
