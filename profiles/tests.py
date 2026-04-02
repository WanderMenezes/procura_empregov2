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


def _approval_ready_wizard_data(district_id=None, birth_date=None):
    birth_date = birth_date or _years_ago(20)
    return {
        '1': {
            'nome': 'Perfil pronto',
            'telefone': '+2399000999',
            'email': 'pronto@example.com',
            'contacto_alternativo': 'Mae',
            'distrito': district_id or '',
            'data_nascimento': birth_date.isoformat(),
            'sexo': 'M',
            'localidade': 'Riboque',
        },
        '2': {
            'nivel': 'SEC',
            'area_formacao': 'TIC',
            'instituicao': 'Liceu Nacional',
            'ano': '2024',
            'curso': 'Informatica',
            'skills': [],
            'idiomas_data': '[]',
        },
        '3': {
            'situacao_atual': 'DES',
            'disponibilidade': 'SIM',
            'interesse_setorial': ['TIC'],
            'preferencia_oportunidade': 'EMP',
            'sobre': 'Quero uma oportunidade.',
        },
        '4': {},
    }


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


class AssistedRegisterTests(TestCase):
    def setUp(self):
        self.district, _ = District.objects.get_or_create(codigo='AGU', defaults={'nome': 'Agua Grande'})
        self.admin = User.objects.create_user(
            telefone='+2399000099',
            nome='Admin Perfis',
            perfil=User.ProfileType.ADMIN,
        )
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
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin,
                titulo='Novo utilizador registado',
                mensagem__icontains='Maria Silva',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin,
                titulo='Perfil pronto para validacao',
                mensagem__icontains='Maria Silva',
            ).exists()
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

    def test_operator_can_create_assisted_registration_with_custom_training_area(self):
        self.client.force_login(self.operator)

        response = self.client.post(reverse('profiles:assisted_register'), {
            'nome': 'Jovem Robotica',
            'telefone': '+2399000210',
            'email': 'robotica@example.com',
            'data_nascimento': '2002-03-12',
            'sexo': 'M',
            'distrito': self.district.id,
            'localidade': 'Riboque',
            'nivel': 'TEC',
            'area_formacao': 'OUT',
            'outra_area_formacao': 'Robotica Industrial',
            'situacao_atual': 'DES',
            'disponibilidade': 'SIM',
            'preferencia_oportunidade': 'EMP',
            'observacoes': 'Area personalizada.',
        })

        self.assertRedirects(response, reverse('profiles:assisted_register'))

        created_user = User.objects.get(telefone='+2399000210')
        created_education = Education.objects.get(profile=created_user.youth_profile)
        self.assertEqual(created_education.area_formacao, 'OUT')
        self.assertEqual(created_education.outra_area_formacao, 'Robotica Industrial')
        self.assertEqual(created_education.area_formacao_display, 'Robotica Industrial')

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

    def test_step1_form_requires_localidade_when_outside_country_is_checked(self):
        form = YouthProfileStep1Form(data={
            'nome': 'Jovem Exterior',
            'telefone': '+351912345678',
            'email': '',
            'contacto_alternativo': '',
            'distrito': '',
            'fora_do_pais': 'on',
            'data_nascimento': '2000-05-02',
            'sexo': 'F',
            'localidade': '',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('localidade', form.errors)

    def test_step1_form_clears_district_when_outside_country_is_checked(self):
        district = District.objects.create(codigo='LOB', nome='Lobata')
        form = YouthProfileStep1Form(data={
            'nome': 'Jovem Exterior',
            'telefone': '+351912345678',
            'email': '',
            'contacto_alternativo': '',
            'distrito': district.id,
            'fora_do_pais': 'on',
            'data_nascimento': '2000-05-02',
            'sexo': 'F',
            'localidade': 'Lisboa, Portugal',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data['fora_do_pais'])
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

    def test_step2_form_requires_custom_training_area_when_other_is_selected(self):
        form = YouthProfileStep2Form(data={
            'nivel': 'SEC',
            'area_formacao': 'OUT',
            'instituicao': 'Escola Tecnica',
            'curso': 'Curso Livre',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('outra_area_formacao', form.errors)

    def test_step2_form_accepts_custom_training_area_when_other_is_selected(self):
        form = YouthProfileStep2Form(data={
            'nivel': 'SEC',
            'area_formacao': 'OUT',
            'outra_area_formacao': 'Robotica Industrial',
            'instituicao': 'Escola Tecnica',
            'curso': 'Curso Livre',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['outra_area_formacao'], 'Robotica Industrial')

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
        self.unvalidated_profile = _create_company_visible_profile(
            self.unvalidated_user,
            validado=False,
        )
        self.validated_user = User.objects.create_user(
            telefone='+2399220003',
            nome='Jovem Validado',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
        )
        self.validated_profile = _create_company_visible_profile(self.validated_user)
        self.external_user = User.objects.create_user(
            telefone='+351912300003',
            nome='Jovem Exterior',
            perfil=User.ProfileType.JOVEM,
            email='exterior@example.com',
        )
        self.external_profile = _create_company_visible_profile(
            self.external_user,
            localidade='Lisboa, Portugal',
        )
        self.auto_unlock_user = User.objects.create_user(
            telefone='+2399220006',
            nome='Jovem Auto Visivel',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
        )
        self.auto_unlock_profile = _create_company_visible_profile(
            self.auto_unlock_user,
            visivel=False,
        )
        self.low_progress_user = User.objects.create_user(
            telefone='+2399220005',
            nome='Jovem Parcial',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
            email='parcial@example.com',
        )
        self.low_progress_profile = _create_admin_approved_but_hidden_profile(
            self.low_progress_user,
        )
        self.preapproved_user = User.objects.create_user(
            telefone='+2399220004',
            nome='Jovem Preaprovado',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
        )
        self.preapproved_profile = YouthProfile.objects.create(
            user=self.preapproved_user,
            visivel=True,
            completo=False,
            validado=True,
            data_nascimento=_years_ago(20),
            situacao_atual='DES',
            disponibilidade='SIM',
            preferencia_oportunidade='EMP',
            wizard_step=3,
            wizard_data=_approval_ready_wizard_data(self.district.id),
        )

    def test_unvalidated_youth_can_view_jobs_but_sees_waiting_state(self):
        self.client.force_login(self.unvalidated_user)

        response = self.client.get(reverse('profiles:available_jobs'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Assistente TIC')
        self.assertContains(response, 'Aguardar validacao')
        self.assertNotContains(response, 'data-form-id="apply-form-{}"'.format(self.job.id))

    def test_available_jobs_page_shows_details_modal_and_apply_button(self):
        self.client.force_login(self.validated_user)

        response = self.client.get(reverse('profiles:available_jobs'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ver detalhes')
        self.assertContains(response, 'id="jobDetailsModal"', html=False)
        self.assertContains(response, 'id="jobDetailsApplyBtn"', html=False)

    def test_available_jobs_direct_link_opens_the_page_where_the_target_job_is_listed(self):
        for index in range(10):
            JobPost.objects.create(
                company=self.company,
                titulo='Oportunidade Extra {}'.format(index),
                descricao='Descricao {}'.format(index),
                requisitos='Requisitos {}'.format(index),
                tipo='EMP',
                distrito=self.district,
                estado='ATIVA',
            )

        self.client.force_login(self.validated_user)

        response = self.client.get(
            reverse('profiles:available_jobs'),
            {'vaga': self.job.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['vagas_page'].number, 2)
        self.assertContains(response, 'id="job-card-{}"'.format(self.job.id), html=False)
        self.assertContains(response, 'data-job-id="{}"'.format(self.job.id), html=False)

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

    def test_validated_youth_reaches_80_percent_and_can_apply_even_if_visibility_was_off(self):
        self.client.force_login(self.auto_unlock_user)

        response = self.client.post(reverse('companies:job_apply', args=[self.job.pk]))

        self.assertRedirects(response, reverse('profiles:detail'))
        self.assertTrue(
            Application.objects.filter(job=self.job, youth=self.auto_unlock_profile).exists()
        )

    def test_admin_approved_youth_below_80_percent_cannot_apply_to_job(self):
        self.client.force_login(self.low_progress_user)

        response = self.client.post(reverse('companies:job_apply', args=[self.job.pk]), follow=True)

        self.assertRedirects(response, reverse('profiles:available_jobs'))
        self.assertFalse(
            Application.objects.filter(job=self.job, youth=self.low_progress_profile).exists()
        )
        self.assertContains(response, '80%')

    def test_preapproved_incomplete_youth_cannot_apply_until_profile_is_complete(self):
        self.client.force_login(self.preapproved_user)

        response = self.client.post(reverse('companies:job_apply', args=[self.job.pk]))

        self.assertRedirects(response, reverse('profiles:available_jobs'))
        self.assertFalse(
            Application.objects.filter(job=self.job, youth=self.preapproved_profile).exists()
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
        self.assertContains(response, 'O teu perfil foi atualizado.')
        self.assertContains(response, 'A idade minima para aprovacao e 18 anos.')
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


class ProfileWizardEditingTests(TestCase):
    def test_editing_step1_can_be_saved_without_finishing_all_steps(self):
        district, _ = District.objects.get_or_create(
            codigo='AGU',
            defaults={'nome': 'Agua Grande'},
        )
        youth_user = User.objects.create_user(
            telefone='+2399220200',
            nome='Perfil Original',
            perfil=User.ProfileType.JOVEM,
            distrito=district,
        )
        profile = YouthProfile.objects.create(
            user=youth_user,
            completo=True,
            validado=False,
            data_nascimento=_years_ago(20),
            sexo='M',
            localidade='Riboque',
            contacto_alternativo='Vizinho',
            situacao_atual='DES',
            disponibilidade='SIM',
            preferencia_oportunidade='EMP',
            sobre='Texto inicial',
            idiomas=[{'idioma': 'Ingles', 'dominio': 'AMBOS'}],
            visivel=True,
            consentimento_whatsapp=True,
        )
        Education.objects.create(
            profile=profile,
            nivel='SEC',
            area_formacao='TIC',
            instituicao='Liceu Nacional',
            ano=2024,
            curso='Informatica',
        )

        self.client.force_login(youth_user)
        self.client.get(reverse('profiles:wizard_step', args=[1]) + '?reset=1')

        response = self.client.post(
            reverse('profiles:wizard_step', args=[1]),
            {
                'nome': 'Perfil Atualizado',
                'telefone': youth_user.telefone,
                'email': 'novoemail@example.com',
                'contacto_alternativo': 'Irma',
                'distrito': district.id,
                'data_nascimento': _years_ago(20).isoformat(),
                'sexo': 'F',
                'localidade': 'Neves',
                'save': '1',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('profiles:detail'))
        youth_user.refresh_from_db()
        profile.refresh_from_db()
        education = Education.objects.get(profile=profile)

        self.assertEqual(youth_user.nome, 'Perfil Atualizado')
        self.assertEqual(youth_user.email, 'novoemail@example.com')
        self.assertEqual(profile.contacto_alternativo, 'Irma')
        self.assertEqual(profile.localidade, 'Neves')
        self.assertEqual(profile.sexo, 'F')
        self.assertEqual(profile.situacao_atual, 'DES')
        self.assertEqual(profile.preferencia_oportunidade, 'EMP')
        self.assertEqual(education.area_formacao, 'TIC')
        self.assertContains(response, 'ja entrou na fila de validacao do administrador')

    def test_editing_step1_can_clear_district_when_outside_country_is_checked(self):
        district, _ = District.objects.get_or_create(
            codigo='AGU',
            defaults={'nome': 'Agua Grande'},
        )
        youth_user = User.objects.create_user(
            telefone='+2399220201',
            nome='Perfil Exterior',
            perfil=User.ProfileType.JOVEM,
            distrito=district,
        )
        profile = YouthProfile.objects.create(
            user=youth_user,
            completo=True,
            validado=False,
            data_nascimento=_years_ago(20),
            sexo='M',
            localidade='Riboque',
            situacao_atual='DES',
            disponibilidade='SIM',
            preferencia_oportunidade='EMP',
            visivel=True,
        )

        self.client.force_login(youth_user)
        self.client.get(reverse('profiles:wizard_step', args=[1]) + '?reset=1')

        response = self.client.post(
            reverse('profiles:wizard_step', args=[1]),
            {
                'nome': 'Perfil Exterior',
                'telefone': youth_user.telefone,
                'email': 'exterior.atualizado@example.com',
                'contacto_alternativo': '',
                'distrito': '',
                'fora_do_pais': 'on',
                'data_nascimento': _years_ago(20).isoformat(),
                'sexo': 'F',
                'localidade': 'Lisboa, Portugal',
                'save': '1',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('profiles:detail'))
        youth_user.refresh_from_db()
        profile.refresh_from_db()

        self.assertIsNone(youth_user.distrito)
        self.assertEqual(youth_user.email, 'exterior.atualizado@example.com')
        self.assertEqual(profile.localidade, 'Lisboa, Portugal')
        self.assertEqual(profile.sexo, 'F')
