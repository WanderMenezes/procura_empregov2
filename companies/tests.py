from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from companies.forms import CompanyProfileForm
from companies.models import Application, Company, ContactRequest, JobPost
from core.models import District, Notification
from profiles.models import Education, YouthProfile


User = get_user_model()


def _years_ago(years):
    today = timezone.localdate()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years)


def _create_company_visible_profile(user, **overrides):
    profile_defaults = {
        'visivel': True,
        'completo': True,
        'validado': True,
        'data_nascimento': _years_ago(20),
        'sexo': 'M',
        'localidade': 'Riboque',
        'contacto_alternativo': 'Mae',
        'situacao_atual': 'DES',
        'disponibilidade': 'SIM',
        'interesse_setorial': ['TIC'],
        'preferencia_oportunidade': 'EMP',
        'sobre': 'Quero uma oportunidade.',
        'consentimento_sms': True,
        'consentimento_whatsapp': True,
        'consentimento_email': True,
        'idiomas': [{'idioma': 'Ingles', 'dominio': 'AMBOS'}],
    }
    profile_defaults.update(overrides)
    profile = YouthProfile.objects.create(user=user, **profile_defaults)
    Education.objects.create(
        profile=profile,
        nivel='SEC',
        area_formacao='TIC',
        instituicao='Liceu Nacional',
        ano=2024,
        curso='Informatica',
    )
    return profile


def _create_admin_approved_but_hidden_profile(user, **overrides):
    profile_defaults = {
        'visivel': True,
        'completo': True,
        'validado': True,
        'data_nascimento': _years_ago(20),
        'sexo': 'M',
        'localidade': 'Riboque',
        'contacto_alternativo': 'Mae',
        'situacao_atual': 'DES',
        'disponibilidade': 'SIM',
        'interesse_setorial': ['TIC'],
        'preferencia_oportunidade': 'EMP',
        'sobre': 'Quero uma oportunidade.',
        'consentimento_sms': True,
        'consentimento_whatsapp': True,
        'consentimento_email': True,
    }
    profile_defaults.update(overrides)
    return YouthProfile.objects.create(user=user, **profile_defaults)


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
            verificada=True,
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
        self.low_progress_user = User.objects.create_user(
            telefone='+2399110004',
            nome='Jovem Aprovado Parcial',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
            email='parcial@example.com',
        )
        self.auto_unlock_user = User.objects.create_user(
            telefone='+2399110005',
            nome='Jovem Auto Visivel',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
        )
        self.manually_hidden_user = User.objects.create_user(
            telefone='+2399110006',
            nome='Jovem Oculto Manualmente',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
            consentimento_dados=True,
        )
        self.validated_profile = _create_company_visible_profile(
            self.validated_user,
        )
        self.unvalidated_profile = _create_company_visible_profile(
            self.unvalidated_user,
            validado=False,
        )
        self.low_progress_profile = _create_admin_approved_but_hidden_profile(
            self.low_progress_user,
        )
        self.auto_unlock_profile = _create_company_visible_profile(
            self.auto_unlock_user,
            visivel=False,
        )
        self.manually_hidden_profile = _create_company_visible_profile(
            self.manually_hidden_user,
            visivel=False,
        )

    def test_search_youth_only_shows_admin_validated_profiles(self):
        self.client.force_login(self.company_user)

        response = self.client.get(reverse('companies:search_youth'))

        self.assertEqual(response.status_code, 200)
        results = list(response.context['results'])
        self.assertIn(self.validated_profile, results)
        self.assertIn(self.auto_unlock_profile, results)
        self.assertNotIn(self.unvalidated_profile, results)
        self.assertNotIn(self.low_progress_profile, results)
        self.assertNotIn(self.manually_hidden_profile, results)
        self.assertContains(response, 'Jovem Validado')
        self.assertContains(response, 'Jovem Auto Visivel')
        self.assertNotContains(response, 'Jovem Pendente')
        self.assertNotContains(response, 'Jovem Aprovado Parcial')
        self.assertNotContains(response, 'Jovem Oculto Manualmente')

    def test_search_youth_hides_admin_approved_profiles_below_80_percent(self):
        self.client.force_login(self.company_user)

        response = self.client.get(reverse('companies:search_youth'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Jovem Aprovado Parcial')

    def test_unverified_company_cannot_search_youth(self):
        self.company.verificada = False
        self.company.save(update_fields=['verificada'])
        self.client.force_login(self.company_user)

        response = self.client.get(reverse('companies:search_youth'), follow=True)

        self.assertRedirects(response, reverse('companies:dashboard'))
        self.assertContains(response, 'aprov')

    def test_unverified_company_cannot_open_valid_youth_detail(self):
        self.company.verificada = False
        self.company.save(update_fields=['verificada'])
        self.client.force_login(self.company_user)

        response = self.client.get(
            reverse('companies:youth_detail', args=[self.validated_profile.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse('companies:dashboard'))
        self.assertContains(response, 'aprov')

    def test_unverified_company_cannot_create_contact_request_even_for_valid_profile(self):
        self.company.verificada = False
        self.company.save(update_fields=['verificada'])
        self.client.force_login(self.company_user)

        response = self.client.post(
            reverse('companies:contact_request_create', args=[self.validated_profile.pk]),
            {'motivo': 'Queremos falar sobre uma oportunidade.'},
            follow=True,
        )

        self.assertRedirects(response, reverse('companies:dashboard'))
        self.assertContains(response, 'aprov')
        self.assertFalse(
            ContactRequest.objects.filter(company=self.company, youth=self.validated_profile).exists()
        )

    def test_auto_unlocked_profile_is_visible_to_companies_after_reaching_80_percent(self):
        self.assertTrue(self.auto_unlock_profile.is_visible_to_companies)

    def test_profile_hidden_manually_stays_out_of_company_search(self):
        self.assertFalse(self.manually_hidden_profile.is_visible_to_companies)

    def test_company_cannot_open_unvalidated_youth_detail(self):
        self.client.force_login(self.company_user)

        response = self.client.get(
            reverse('companies:youth_detail', args=[self.unvalidated_profile.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse('companies:search_youth'))
        self.assertContains(response, '80%')

    def test_company_cannot_create_contact_request_for_unvalidated_profile(self):
        self.client.force_login(self.company_user)

        response = self.client.get(
            reverse('companies:contact_request_create', args=[self.unvalidated_profile.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse('companies:search_youth'))
        self.assertContains(response, '80%')

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


class AdminWorkflowNotificationTests(TestCase):
    def setUp(self):
        self.district, _ = District.objects.get_or_create(
            codigo='AGU',
            defaults={'nome': 'Agua Grande'},
        )
        self.admin = User.objects.create_user(
            telefone='+2399110100',
            nome='Admin Fluxos',
            perfil=User.ProfileType.ADMIN,
        )
        self.company_user = User.objects.create_user(
            telefone='+2399110101',
            nome='Empresa Fluxos',
            perfil=User.ProfileType.EMPRESA,
            distrito=self.district,
        )
        self.company = Company.objects.create(
            user=self.company_user,
            nome='Empresa Fluxos',
            ativa=True,
            verificada=True,
        )
        self.youth_user = User.objects.create_user(
            telefone='+2399110102',
            nome='Jovem Fluxos',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
        )
        self.profile = _create_company_visible_profile(self.youth_user)
        self.job = JobPost.objects.create(
            company=self.company,
            titulo='Assistente de Projeto',
            descricao='Apoio operacional.',
            requisitos='Organizacao.',
            tipo='EMP',
            estado='ATIVA',
        )

    def test_contact_request_create_notifies_admin(self):
        self.client.force_login(self.company_user)

        response = self.client.post(
            reverse('companies:contact_request_create', args=[self.profile.pk]),
            {'motivo': 'Queremos falar sobre uma oportunidade.'},
        )

        self.assertRedirects(response, reverse('companies:youth_detail', args=[self.profile.pk]))
        self.assertTrue(
            ContactRequest.objects.filter(
                company=self.company,
                youth=self.profile,
                estado='PENDENTE',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin,
                titulo='Novo pedido de contacto',
                mensagem__icontains='Empresa Fluxos',
            ).exists()
        )

    def test_accepting_employment_application_notifies_admin_about_placement(self):
        application = Application.objects.create(
            job=self.job,
            youth=self.profile,
            estado='PENDENTE',
            mensagem='Quero trabalhar nesta vaga.',
        )
        self.client.force_login(self.company_user)

        response = self.client.get(
            reverse('companies:application_update', args=[application.pk, 'ACEITE'])
        )

        self.assertRedirects(response, reverse('companies:job_applications', args=[self.job.pk]))
        application.refresh_from_db()
        self.assertEqual(application.estado, 'ACEITE')
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin,
                titulo='Nova colocacao em emprego',
                mensagem__icontains='Jovem Fluxos',
            ).exists()
        )
