import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from companies.models import Application, Company, ContactRequest, JobPost
from core.models import AuditLog, District, Notification
from profiles.forms import YouthProfileStep1Form, YouthProfileStep2Form, YouthProfileStep3Form
from profiles.models import Education, YouthProfile


User = get_user_model()


def _years_ago(years):
    today = timezone.localdate()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years)


class AssistedRegisterTests(TestCase):
    def setUp(self):
        self.district, _ = District.objects.get_or_create(codigo='AGU', defaults={'nome': 'Agua Grande'})
        self.operator = User.objects.create_user(
            telefone='+2399000100',
            nome='Operador Teste',
            perfil=User.ProfileType.OPERADOR,
            distrito=self.district,
            associacao_parceira='Associacao Jovem',
        )

    def test_operator_can_open_assisted_registration_page(self):
        self.client.force_login(self.operator)

        response = self.client.get(reverse('profiles:assisted_register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registo assistido de jovem')
        self.assertContains(response, 'Notas internas do atendimento')

    def test_operator_can_create_assisted_registration_and_log_notes(self):
        self.client.force_login(self.operator)

        response = self.client.post(reverse('profiles:assisted_register'), {
            'nome': 'Maria Silva',
            'telefone': '+2399000200',
            'email': 'maria@example.com',
            'data_nascimento': '2004-05-02',
            'sexo': 'F',
            'distrito': self.district.id,
            'localidade': 'Riboque',
            'nivel': 'SEC',
            'area_formacao': 'TIC',
            'situacao_atual': 'DES',
            'disponibilidade': 'SIM',
            'preferencia_oportunidade': 'EMP',
            'idioma_1_nome': 'Ingles',
            'idioma_1_dominio': 'AMBOS',
            'observacoes': 'Atendimento presencial com apoio documental.',
        })

        self.assertRedirects(response, reverse('profiles:assisted_register'))

        created_user = User.objects.get(telefone='+2399000200')
        created_profile = YouthProfile.objects.get(user=created_user)
        created_education = Education.objects.get(profile=created_profile)
        created_log = AuditLog.objects.get(acao='registo_assistido_criado')

        self.assertEqual(created_user.perfil, User.ProfileType.JOVEM)
        self.assertTrue(created_profile.completo)
        self.assertFalse(created_profile.validado)
        self.assertEqual(created_profile.idiomas, [{'idioma': 'Ingles', 'dominio': 'AMBOS'}])
        self.assertEqual(created_education.area_formacao, 'TIC')
        self.assertEqual(created_log.user, self.operator)
        self.assertEqual(
            created_log.payload['observacoes'],
            'Atendimento presencial com apoio documental.',
        )

    def test_operator_can_create_assisted_registration_without_district(self):
        self.client.force_login(self.operator)

        response = self.client.post(reverse('profiles:assisted_register'), {
            'nome': 'Candidato Exterior',
            'telefone': '+351912300200',
            'email': 'exterior@example.com',
            'data_nascimento': '2003-08-12',
            'sexo': 'M',
            'distrito': '',
            'localidade': 'Lisboa, Portugal',
            'situacao_atual': 'DES',
            'disponibilidade': 'SIM',
            'preferencia_oportunidade': 'EMP',
            'observacoes': 'Registo de candidato fora de Sao Tome e Principe.',
        })

        self.assertRedirects(response, reverse('profiles:assisted_register'))

        created_user = User.objects.get(telefone='+351912300200')
        created_profile = YouthProfile.objects.get(user=created_user)

        self.assertIsNone(created_user.distrito)
        self.assertEqual(created_profile.localidade, 'Lisboa, Portugal')
        self.assertTrue(created_profile.completo)

    def test_non_operator_cannot_access_assisted_registration(self):
        young_user = User.objects.create_user(
            telefone='+2399000300',
            nome='Jovem Teste',
            perfil=User.ProfileType.JOVEM,
        )
        self.client.force_login(young_user)

        response = self.client.get(reverse('profiles:assisted_register'))

        self.assertRedirects(response, reverse('home'))


class YouthProfileInterestSectorTests(TestCase):
    def test_step1_form_accepts_empty_district(self):
        form = YouthProfileStep1Form(data={
            'nome': 'Jovem Exterior',
            'telefone': '+351912345678',
            'email': '',
            'contacto_alternativo': '',
            'distrito': '',
            'data_nascimento': '2000-05-02',
            'sexo': 'F',
            'localidade': 'Lisboa, Portugal',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['distrito'])

    def test_step2_form_accepts_languages_with_domain_type(self):
        form = YouthProfileStep2Form(data={
            'nivel': 'SEC',
            'area_formacao': 'TIC',
            'instituicao': 'Escola Tecnica',
            'ano': '2024',
            'curso': 'Informatica',
            'idioma_1_nome': 'Portugues',
            'idioma_1_dominio': 'AMBOS',
            'idioma_2_nome': 'Ingles',
            'idioma_2_dominio': 'ORAL',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            json.loads(form.cleaned_data['idiomas_data']),
            [
                {'idioma': 'Portugues', 'dominio': 'AMBOS'},
                {'idioma': 'Ingles', 'dominio': 'ORAL'},
            ],
        )

    def test_step2_form_requires_language_domain_when_language_is_filled(self):
        form = YouthProfileStep2Form(data={
            'idioma_1_nome': 'Frances',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('idioma_1_dominio', form.errors)

    def test_step3_form_accepts_custom_interest_sector(self):
        form = YouthProfileStep3Form(data={
            'situacao_atual': 'DES',
            'disponibilidade': 'SIM',
            'interesse_setorial': ['AGR', 'OUT'],
            'outros_setores_interesse': 'Turismo, Robotica',
            'preferencia_oportunidade': 'EMP',
            'sobre': 'Quero trabalhar em areas tecnicas.',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['interesse_setorial'], ['AGR', 'TUR', 'Robotica'])

    def test_step3_form_prefills_custom_interest_sector(self):
        form = YouthProfileStep3Form(initial={
            'interesse_setorial': ['AGR', 'Robotica'],
        })

        self.assertEqual(form.initial['interesse_setorial'], ['AGR'])
        self.assertEqual(form.initial['outros_setores_interesse'], 'Robotica')

    def test_profile_display_keeps_custom_interest_sector(self):
        user = User.objects.create_user(
            telefone='+2399000400',
            nome='Jovem Setor',
            perfil=User.ProfileType.JOVEM,
            password='SenhaSegura123',
        )
        profile = YouthProfile.objects.create(
            user=user,
            interesse_setorial=['AGR', 'Robotica'],
        )

        self.assertEqual(profile.interesses_setoriais_labels, ['Agricultura', 'Robotica'])
        self.assertEqual(profile.interesses_setoriais_display, 'Agricultura, Robotica')


class YouthJobApplicationPermissionsTests(TestCase):
    def setUp(self):
        self.district, _ = District.objects.get_or_create(
            codigo='AGU',
            defaults={'nome': 'Agua Grande'},
        )
        self.company_user = User.objects.create_user(
            telefone='+2399220001',
            nome='Empresa Oportunidades',
            perfil=User.ProfileType.EMPRESA,
            distrito=self.district,
        )
        self.company = Company.objects.create(
            user=self.company_user,
            nome='Empresa Oportunidades',
            ativa=True,
            distrito=self.district,
        )
        self.job = JobPost.objects.create(
            company=self.company,
            titulo='Assistente TIC',
            descricao='Apoio operacional e digital.',
            requisitos='Boa comunicacao e vontade de aprender.',
            tipo='EMP',
            distrito=self.district,
            estado='ATIVA',
        )
        self.unvalidated_user = User.objects.create_user(
            telefone='+2399220002',
            nome='Jovem Pendente',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
        )
        self.unvalidated_profile = YouthProfile.objects.create(
            user=self.unvalidated_user,
            visivel=True,
            completo=True,
            validado=False,
        )
        self.validated_user = User.objects.create_user(
            telefone='+2399220003',
            nome='Jovem Validado',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
        )
        self.validated_profile = YouthProfile.objects.create(
            user=self.validated_user,
            visivel=True,
            completo=True,
            validado=True,
        )
        self.external_user = User.objects.create_user(
            telefone='+351912300003',
            nome='Jovem Exterior',
            perfil=User.ProfileType.JOVEM,
        )
        self.external_profile = YouthProfile.objects.create(
            user=self.external_user,
            visivel=True,
            completo=True,
            validado=True,
            localidade='Lisboa, Portugal',
        )

    def test_unvalidated_youth_can_view_jobs_but_sees_waiting_state(self):
        self.client.force_login(self.unvalidated_user)

        response = self.client.get(reverse('profiles:available_jobs'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Assistente TIC')
        self.assertContains(response, 'Aguardar validacao')
        self.assertNotContains(response, 'data-form-id="apply-form-{}"'.format(self.job.id))

    def test_unvalidated_youth_cannot_apply_to_job(self):
        self.client.force_login(self.unvalidated_user)

        response = self.client.post(reverse('companies:job_apply', args=[self.job.pk]))

        self.assertRedirects(response, reverse('profiles:available_jobs'))
        self.assertFalse(
            Application.objects.filter(job=self.job, youth=self.unvalidated_profile).exists()
        )

    def test_validated_youth_can_apply_to_job(self):
        self.client.force_login(self.validated_user)

        response = self.client.post(reverse('companies:job_apply', args=[self.job.pk]))

        self.assertRedirects(response, reverse('profiles:detail'))
        self.assertTrue(
            Application.objects.filter(job=self.job, youth=self.validated_profile).exists()
        )

    def test_validated_youth_without_district_can_apply_to_job(self):
        self.client.force_login(self.external_user)

        response = self.client.post(reverse('companies:job_apply', args=[self.job.pk]))

        self.assertRedirects(response, reverse('profiles:detail'))
        self.assertTrue(
            Application.objects.filter(job=self.job, youth=self.external_profile).exists()
        )


class YouthProfileAgeWarningTests(TestCase):
    def test_underage_candidate_sees_age_validation_warning(self):
        district, _ = District.objects.get_or_create(
            codigo='AGU',
            defaults={'nome': 'Agua Grande'},
        )
        youth_user = User.objects.create_user(
            telefone='+2399220099',
            nome='Jovem Menor',
            perfil=User.ProfileType.JOVEM,
            distrito=district,
        )
        profile = YouthProfile.objects.create(
            user=youth_user,
            completo=True,
            validado=False,
            data_nascimento=_years_ago(17),
        )

        self.client.force_login(youth_user)
        response = self.client.get(reverse('profiles:detail'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Atencao:')
        self.assertContains(response, profile.validation_age_message)

    def test_validated_candidate_loses_validation_when_birth_date_changes_to_underage(self):
        district, _ = District.objects.get_or_create(
            codigo='AGU',
            defaults={'nome': 'Agua Grande'},
        )
        company_user = User.objects.create_user(
            telefone='+2399220101',
            nome='Empresa Contacto',
            perfil=User.ProfileType.EMPRESA,
            distrito=district,
        )
        company = Company.objects.create(
            user=company_user,
            nome='Empresa Contacto',
            ativa=True,
            distrito=district,
        )
        youth_user = User.objects.create_user(
            telefone='+2399220100',
            nome='Jovem Aprovado',
            perfil=User.ProfileType.JOVEM,
            distrito=district,
        )
        profile = YouthProfile.objects.create(
            user=youth_user,
            completo=True,
            validado=True,
            visivel=True,
            data_nascimento=_years_ago(19),
            situacao_atual='DES',
            disponibilidade='SIM',
            preferencia_oportunidade='EMP',
        )
        contact_request = ContactRequest.objects.create(
            company=company,
            youth=profile,
            motivo='Gostariamos de entrar em contacto.',
            estado='APROVADO',
        )

        self.client.force_login(youth_user)
        session = self.client.session
        session['wizard_data'] = {
            '1': {
                'nome': youth_user.nome,
                'telefone': youth_user.telefone,
                'email': youth_user.email or '',
                'distrito': district.id,
                'data_nascimento': _years_ago(17).isoformat(),
                'sexo': '',
                'localidade': '',
                'contacto_alternativo': '',
            },
            '2': {
                'nivel': '',
                'area_formacao': '',
                'instituicao': '',
                'ano': '',
                'curso': '',
                'skills': [],
                'idiomas_data': '[]',
            },
            '3': {
                'situacao_atual': 'DES',
                'disponibilidade': 'SIM',
                'interesse_setorial': [],
                'preferencia_oportunidade': 'EMP',
                'sobre': '',
            },
        }
        session.save()

        response = self.client.post(
            reverse('profiles:wizard_step', args=[4]),
            {
                'visivel': 'on',
                'submit': '1',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        contact_request.refresh_from_db()
        self.assertFalse(profile.validado)
        self.assertEqual(contact_request.estado, 'DESATIVADO')
        self.assertIsNotNone(contact_request.responded_at)
        self.assertIn('idade minima', contact_request.resposta_admin)
        self.assertContains(response, 'a validacao anterior foi removida automaticamente')
        self.assertContains(response, 'A idade minima para aprovacao e 18 anos.')
        self.assertContains(response, 'Tambem desativamos 1 acesso de empresa ao teu contacto.')
        self.assertTrue(
            Notification.objects.filter(
                user=youth_user,
                titulo='Validacao removida por idade',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=company_user,
                titulo='Pedido de contacto desativado',
            ).exists()
        )
