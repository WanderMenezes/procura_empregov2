from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from companies.forms import CompanyProfileForm
from companies.models import Company, ContactRequest
from core.models import District
from profiles.models import YouthProfile


User = get_user_model()


def _years_ago(years):
    today = timezone.localdate()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years)


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
            data_nascimento=_years_ago(19),
        )
        self.unvalidated_profile = YouthProfile.objects.create(
            user=self.unvalidated_user,
            visivel=True,
            completo=True,
            validado=False,
            data_nascimento=_years_ago(17),
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
            reverse('companies:youth_detail', args=[self.unvalidated_profile.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse('companies:search_youth'))
        self.assertContains(response, 'dispon')

    def test_company_cannot_create_contact_request_for_unvalidated_profile(self):
        self.client.force_login(self.company_user)

        response = self.client.get(
            reverse('companies:contact_request_create', args=[self.unvalidated_profile.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse('companies:search_youth'))
        self.assertContains(response, 'novos pedidos de contacto')

    def test_company_can_open_disabled_contact_profile_without_seeing_contacts(self):
        contact_request = ContactRequest.objects.create(
            company=self.company,
            youth=self.validated_profile,
            motivo='Queremos falar sobre uma oportunidade.',
            estado='DESATIVADO',
            resposta_admin='Acesso desativado por regra de idade.',
        )
        self.validated_profile.data_nascimento = _years_ago(9)
        self.validated_profile.save()
        self.client.force_login(self.company_user)

        response = self.client.get(reverse('companies:youth_detail', args=[self.validated_profile.pk]))

        self.validated_profile.refresh_from_db()
        self.assertFalse(self.validated_profile.validado)
        self.assertFalse(self.validated_profile.visivel)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Desativado')
        self.assertContains(response, 'deixou de estar dispon')
        self.assertNotContains(response, self.validated_user.telefone)
        contact_request.refresh_from_db()

    def test_contact_request_list_hides_phone_for_stale_underage_approved_request(self):
        ContactRequest.objects.create(
            company=self.company,
            youth=self.validated_profile,
            motivo='Queremos falar sobre uma oportunidade.',
            estado='APROVADO',
        )
        YouthProfile.objects.filter(pk=self.validated_profile.pk).update(
            data_nascimento=_years_ago(9),
            validado=True,
            visivel=True,
        )
        self.client.force_login(self.company_user)

        response = self.client.get(reverse('companies:contact_request_list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.validated_user.telefone)
        self.assertContains(response, 'dados diretos do jovem ja nao estao disponiveis')
