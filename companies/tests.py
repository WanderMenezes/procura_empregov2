from django.contrib.auth import get_user_model
from django.test import TestCase

from companies.forms import CompanyProfileForm
from companies.models import Company


User = get_user_model()


class CompanySectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            telefone='+2399000001',
            nome='Empresa Teste',
            perfil=User.ProfileType.EMPRESA,
        )

    def test_company_normalizes_single_sector_string(self):
        company = Company.objects.create(
            user=self.user,
            nome='Empresa Teste',
            setor='TIC',
        )

        company.refresh_from_db()

        self.assertEqual(company.setor, ['TIC'])
        self.assertEqual(
            company.get_setor_display(),
            str(Company.get_setor_mapping()['TIC']),
        )

    def test_company_profile_form_saves_multiple_sectors(self):
        form = CompanyProfileForm(data={
            'nome': 'Empresa Teste',
            'nif': '12345',
            'setor': ['TIC', 'COM'],
            'descricao': 'Descricao curta',
            'telefone': '',
            'email': '',
            'website': '',
            'distrito': '',
            'endereco': '',
        })

        self.assertTrue(form.is_valid(), form.errors)

        company = form.save(commit=False)
        company.user = self.user
        company.save()

        self.assertEqual(company.setor, ['TIC', 'COM'])
        self.assertEqual(
            company.get_setor_display(),
            '{}, {}'.format(
                Company.get_setor_mapping()['TIC'],
                Company.get_setor_mapping()['COM'],
            ),
        )
