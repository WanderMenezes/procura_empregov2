from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from companies.forms import CompanyProfileForm
from companies.models import Company
from core.models import District
from profiles.models import YouthProfile


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


class CompanyYouthVisibilityTests(TestCase):
    def setUp(self):
        self.district, _ = District.objects.get_or_create(
            codigo='AGU',
            defaults={'nome': 'Agua Grande'},
        )
        self.company_user = User.objects.create_user(
            telefone='+2399110001',
            nome='Empresa Visibilidade',
            perfil=User.ProfileType.EMPRESA,
            distrito=self.district,
        )
        self.company = Company.objects.create(
            user=self.company_user,
            nome='Empresa Visibilidade',
            ativa=True,
        )
        self.validated_user = User.objects.create_user(
            telefone='+2399110002',
            nome='Jovem Validado',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
        )
        self.unvalidated_user = User.objects.create_user(
            telefone='+2399110003',
            nome='Jovem Pendente',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
        )
        self.validated_profile = YouthProfile.objects.create(
            user=self.validated_user,
            visivel=True,
            completo=True,
            validado=True,
        )
        self.unvalidated_profile = YouthProfile.objects.create(
            user=self.unvalidated_user,
            visivel=True,
            completo=True,
            validado=False,
        )

    def test_search_youth_only_shows_admin_validated_profiles(self):
        self.client.force_login(self.company_user)

        response = self.client.get(reverse('companies:search_youth'))

        self.assertEqual(response.status_code, 200)
        results = list(response.context['results'])
        self.assertIn(self.validated_profile, results)
        self.assertNotIn(self.unvalidated_profile, results)
        self.assertContains(response, 'Jovem Validado')
        self.assertNotContains(response, 'Jovem Pendente')

    def test_company_cannot_open_unvalidated_youth_detail(self):
        self.client.force_login(self.company_user)

        response = self.client.get(
            reverse('companies:youth_detail', args=[self.unvalidated_profile.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_company_cannot_create_contact_request_for_unvalidated_profile(self):
        self.client.force_login(self.company_user)

        response = self.client.get(
            reverse('companies:contact_request_create', args=[self.unvalidated_profile.pk])
        )

        self.assertEqual(response.status_code, 404)
