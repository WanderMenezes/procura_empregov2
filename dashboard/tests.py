import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from companies.models import Application, Company, ContactRequest, JobPost
from core.models import AuditLog, District, Notification
from profiles.models import Education, YouthProfile


User = get_user_model()


def _years_ago(years):
    today = timezone.localdate()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years)


def _approval_ready_wizard_data(district_id, birth_date=None):
    birth_date = birth_date or _years_ago(20)
    return {
        '1': {
            'nome': 'Perfil pronto',
            'telefone': '+2399000999',
            'email': 'pronto@example.com',
            'contacto_alternativo': 'Mae',
            'distrito': district_id,
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


class ContactRequestAdminActionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            telefone='+2399000001',
            nome='Admin Teste',
            perfil=User.ProfileType.ADMIN,
        )
        self.company_user = User.objects.create_user(
            telefone='+2399000002',
            nome='Empresa Teste',
            perfil=User.ProfileType.EMPRESA,
        )
        self.youth_user = User.objects.create_user(
            telefone='+2399000003',
            nome='Jovem Teste',
            perfil=User.ProfileType.JOVEM,
            email='jovem@example.com',
        )

        self.company = Company.objects.create(
            user=self.company_user,
            nome='Empresa Teste',
            verificada=True,
        )
        self.youth = YouthProfile.objects.create(
            user=self.youth_user,
            completo=True,
            validado=True,
        )
        self.contact = ContactRequest.objects.create(
            company=self.company,
            youth=self.youth,
            motivo='Queremos falar sobre uma oportunidade.',
            estado='APROVADO',
        )

    def test_admin_can_deactivate_approved_contact_request(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('dashboard:contact_request_action', args=[self.contact.pk, 'desativar'])
        )

        self.assertRedirects(response, reverse('dashboard:manage_contact_requests'))
        self.contact.refresh_from_db()

        self.assertEqual(self.contact.estado, 'DESATIVADO')
        self.assertIsNotNone(self.contact.responded_at)
        self.assertTrue(
            Notification.objects.filter(
                user=self.company_user,
                titulo='Pedido de contacto desativado',
            ).exists()
        )

    def test_deactivated_request_hides_contact_again_for_company(self):
        self.contact.estado = 'DESATIVADO'
        self.contact.save(update_fields=['estado'])
        self.client.force_login(self.company_user)

        response = self.client.get(
            reverse('companies:youth_detail', args=[self.youth.pk])
        )

        self.assertContains(response, 'Desativado')
        self.assertContains(response, 'foi desativado pelo administrador')
        self.assertNotContains(response, self.youth_user.telefone)


class BaseNavbarTests(TestCase):
    def test_help_link_is_no_longer_in_top_nav(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count(reverse('help')), 1)

    def test_footer_image_is_no_longer_rendered(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'footer-brand-mark')

    def test_footer_uses_standard_technical_links(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Técnico PNUD')
        self.assertContains(response, reverse('dashboard:tecnico'))
        self.assertContains(response, reverse('accounts:profile'))


class TechnicalDashboardTests(TestCase):
    def setUp(self):
        self.district, _ = District.objects.get_or_create(
            codigo='AGU',
            defaults={'nome': 'Agua Grande'},
        )
        self.tecnico = User.objects.create_user(
            telefone='+2399000010',
            nome='Tecnico PNUD',
            perfil=User.ProfileType.TECNICO,
        )
        self.company_user = User.objects.create_user(
            telefone='+2399000011',
            nome='Empresa Observatorio',
            perfil=User.ProfileType.EMPRESA,
        )
        self.company = Company.objects.create(
            user=self.company_user,
            nome='Empresa Observatorio',
            ativa=True,
        )
        self.youth_user = User.objects.create_user(
            telefone='+2399000012',
            nome='Jovem Tecnico',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
            email='jovem.tecnico@example.com',
        )
        self.youth = YouthProfile.objects.create(
            user=self.youth_user,
            completo=True,
            validado=True,
        )
        Education.objects.create(
            profile=self.youth,
            nivel='SUP',
            area_formacao='TIC',
            instituicao='Instituto Tecnico',
            ano=2025,
            curso='Programacao',
        )
        self.job = JobPost.objects.create(
            company=self.company,
            titulo='Analista TIC',
            descricao='Acompanhar indicadores e preparar relatorios.',
            requisitos='Conhecimentos de dados e organizacao.',
            tipo='EMP',
            estado='ATIVA',
        )
        Application.objects.create(
            job=self.job,
            youth=self.youth,
            mensagem='Tenho interesse na oportunidade.',
        )

    def test_tecnico_dashboard_shows_monitoring_panels(self):
        self.client.force_login(self.tecnico)

        response = self.client.get(reverse('dashboard:tecnico'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Técnico PNUD')
        self.assertContains(response, 'Jovens por distrito')
        self.assertContains(response, 'Jovem Tecnico')
        self.assertContains(response, 'Empresa Observatorio')
        self.assertContains(response, 'Analista TIC')

    def test_non_tecnico_cannot_open_dashboard(self):
        self.client.force_login(self.company_user)

        response = self.client.get(reverse('dashboard:tecnico'))

        self.assertRedirects(response, reverse('home'))


class ProfileValidationQueueTests(TestCase):
    def setUp(self):
        self.district, _ = District.objects.get_or_create(
            codigo='AGU',
            defaults={'nome': 'Agua Grande'},
        )
        self.admin = User.objects.create_user(
            telefone='+2399000015',
            nome='Admin Validador',
            perfil=User.ProfileType.ADMIN,
            distrito=self.district,
        )
        self.youth_user = User.objects.create_user(
            telefone='+2399000016',
            nome='Jovem Pendente',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
            email='pendente@example.com',
        )
        self.profile = YouthProfile.objects.create(
            user=self.youth_user,
            completo=False,
            validado=False,
            data_nascimento=_years_ago(20),
            situacao_atual='DES',
            disponibilidade='SIM',
            preferencia_oportunidade='EMP',
            wizard_step=3,
            wizard_data=_approval_ready_wizard_data(self.district.id),
        )
        self.incomplete_user = User.objects.create_user(
            telefone='+2399000017',
            nome='Jovem Incompleto',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
            email='incompleto@example.com',
        )
        self.incomplete_profile = YouthProfile.objects.create(
            user=self.incomplete_user,
            completo=False,
            validado=False,
        )
        self.ready_user = User.objects.create_user(
            telefone='+2399000018',
            nome='Jovem Quase Pronto',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
            email='quase.pronto@example.com',
        )
        self.ready_profile = YouthProfile.objects.create(
            user=self.ready_user,
            completo=False,
            validado=False,
            data_nascimento=_years_ago(20),
            situacao_atual='DES',
            disponibilidade='SIM',
            preferencia_oportunidade='EMP',
            wizard_step=3,
            wizard_data=_approval_ready_wizard_data(self.district.id),
        )
        self.company_user = User.objects.create_user(
            telefone='+2399000019',
            nome='Empresa Pendente',
            perfil=User.ProfileType.EMPRESA,
            distrito=self.district,
            email='empresa.pendente@example.com',
        )
        self.company_profile = Company.objects.create(
            user=self.company_user,
            nome='Empresa Pendente',
            nif='123456789',
            setor=['TIC'],
            descricao='Empresa pronta para validacao.',
            telefone='+2399000019',
            email='empresa.pendente@example.com',
            distrito=self.district,
            endereco='Centro de Negocios',
            verificada=False,
        )

    def test_validation_queue_shows_admin_link_to_profile_detail(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:validate_profiles'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ver perfil')
        self.assertContains(
            response,
            reverse('dashboard:user_detail', args=[self.youth_user.pk]),
        )

    def test_admin_cannot_approve_underage_profile(self):
        self.profile.data_nascimento = _years_ago(17)
        self.profile.save(update_fields=['data_nascimento'])
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('dashboard:validate_profile', args=[self.profile.pk, 'aprovar'])
        )

        self.assertRedirects(response, reverse('dashboard:validate_profiles'))
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.validado)
        self.assertTrue(
            Notification.objects.filter(
                user=self.youth_user,
                titulo='Perfil pendente por idade minima',
            ).exists()
        )

    def test_validation_queue_marks_underage_profile_as_blocked(self):
        self.profile.data_nascimento = _years_ago(17)
        self.profile.save(update_fields=['data_nascimento'])
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:validate_profiles'))

        self.assertContains(response, 'Menor de 18 anos')
        self.assertContains(response, 'A idade mínima para aprovação é 18 anos.')

    def test_validation_queue_explains_incomplete_registrations_are_not_ready(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:validate_profiles'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['validation_summary']['incomplete_profiles'], 1)
        self.assertContains(response, 'Registos incompletos')
        self.assertContains(response, 'abaixo de 50%')
        self.assertNotContains(response, 'Jovem Incompleto')

    def test_validation_queue_includes_profiles_that_reach_minimum_progress(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:validate_profiles'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jovem Quase Pronto')
        self.assertContains(response, '66% preenchido')

    def test_validation_queue_includes_unverified_company_with_complete_profile(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:validate_profiles'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Empresa Pendente')
        self.assertContains(response, 'Empresa')
        self.assertContains(response, 'NIF 123456789')

    def test_admin_can_approve_company_profile_from_validation_queue(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('dashboard:validate_profile', args=[self.company_profile.pk, 'aprovar']),
            {'kind': 'company'},
        )

        self.assertRedirects(response, reverse('dashboard:validate_profiles'))
        self.company_profile.refresh_from_db()
        self.assertTrue(self.company_profile.verificada)
        self.assertTrue(
            Notification.objects.filter(
                user=self.company_user,
                titulo='Perfil da empresa validado!',
            ).exists()
        )

    def test_admin_cannot_approve_profile_below_minimum_progress(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('dashboard:validate_profile', args=[self.incomplete_profile.pk, 'aprovar']),
            follow=True,
        )

        self.assertRedirects(response, reverse('dashboard:validate_profiles'))
        self.incomplete_profile.refresh_from_db()
        self.assertFalse(self.incomplete_profile.validado)
        self.assertContains(response, 'atingir pelo menos 50%')

    def test_admin_can_open_incomplete_profiles_page(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:incomplete_profiles'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registos incompletos')
        self.assertContains(response, 'Jovem Incompleto')
        self.assertContains(response, 'A seguir: Dados pessoais')
        self.assertNotContains(response, 'Jovem Pendente')
        self.assertNotContains(response, 'Jovem Quase Pronto')
        self.assertEqual(response.context['incomplete_summary']['filtered_total'], 1)

    def test_non_admin_cannot_open_incomplete_profiles_page(self):
        self.client.force_login(self.youth_user)

        response = self.client.get(reverse('dashboard:incomplete_profiles'))

        self.assertRedirects(response, reverse('home'))

    def test_admin_dashboard_links_to_incomplete_profiles_page(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:admin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('dashboard:incomplete_profiles'))
        self.assertContains(response, 'Registos incompletos')


class ReportsExportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            telefone='+2399000020',
            nome='Admin Relatorios',
            perfil=User.ProfileType.ADMIN,
        )
        self.district, _ = District.objects.get_or_create(
            codigo='AGU',
            defaults={'nome': 'Agua Grande'},
        )
        self.company_user = User.objects.create_user(
            telefone='+2399000021',
            nome='Empresa Relatorios',
            perfil=User.ProfileType.EMPRESA,
        )
        self.company = Company.objects.create(
            user=self.company_user,
            nome='Empresa Relatorios',
            ativa=True,
        )
        self.youth_user = User.objects.create_user(
            telefone='+2399000022',
            nome='Jovem Relatorios',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
            email='jovem.relatorios@example.com',
        )
        self.youth = YouthProfile.objects.create(
            user=self.youth_user,
            completo=True,
            validado=True,
        )
        Education.objects.create(
            profile=self.youth,
            nivel='SUP',
            area_formacao='TIC',
            instituicao='Centro de Formacao',
            ano=2025,
            curso='Analise de Dados',
        )
        self.job = JobPost.objects.create(
            company=self.company,
            titulo='Tecnico de Dados',
            descricao='Preparar indicadores e relatorios.',
            requisitos='Conhecimento de dados.',
            tipo='EMP',
            estado='ATIVA',
        )
        self.application = Application.objects.create(
            job=self.job,
            youth=self.youth,
            estado='ACEITE',
            mensagem='Quero participar.',
        )
        self.contact_request = ContactRequest.objects.create(
            company=self.company,
            youth=self.youth,
            motivo='Queremos falar sobre esta vaga.',
            estado='APROVADO',
            responded_at=timezone.now(),
        )

    def test_reports_page_supports_daily_period(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:reports'), {'periodo': 'diario'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_period_key'], 'diario')
        self.assertEqual(response.context['period_days'], 1)
        self.assertContains(response, 'Gerar relatorio personalizado')

    def test_reports_page_quinzenal_excludes_older_records(self):
        old_dt = timezone.now() - timedelta(days=30)

        old_company_user = User.objects.create_user(
            telefone='+2399000091',
            nome='Empresa Antiga',
            perfil=User.ProfileType.EMPRESA,
        )
        old_company = Company.objects.create(
            user=old_company_user,
            nome='Empresa Antiga',
            ativa=True,
        )
        Company.objects.filter(pk=old_company.pk).update(created_at=old_dt, updated_at=old_dt)

        old_youth_user = User.objects.create_user(
            telefone='+2399000092',
            nome='Jovem Antigo',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
            email='jovem.antigo@example.com',
        )
        old_youth = YouthProfile.objects.create(
            user=old_youth_user,
            completo=True,
            validado=True,
        )
        YouthProfile.objects.filter(pk=old_youth.pk).update(created_at=old_dt, updated_at=old_dt)
        Education.objects.create(
            profile=old_youth,
            nivel='SEC',
            area_formacao='TIC',
            instituicao='Centro Antigo',
            ano=2023,
            curso='Informatica',
        )

        old_job = JobPost.objects.create(
            company=old_company,
            titulo='Tecnico Antigo',
            descricao='Historico antigo.',
            requisitos='Experiencia.',
            tipo='EMP',
            estado='ATIVA',
        )
        JobPost.objects.filter(pk=old_job.pk).update(data_publicacao=old_dt)

        old_application = Application.objects.create(
            job=old_job,
            youth=old_youth,
            estado='ACEITE',
            mensagem='Candidatura antiga.',
        )
        Application.objects.filter(pk=old_application.pk).update(created_at=old_dt, updated_at=old_dt)

        old_contact = ContactRequest.objects.create(
            company=old_company,
            youth=old_youth,
            motivo='Pedido antigo.',
            estado='APROVADO',
            responded_at=old_dt,
        )
        ContactRequest.objects.filter(pk=old_contact.pk).update(created_at=old_dt, responded_at=old_dt)

        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard:reports'), {'periodo': 'quinzenal'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['jovens_novos'], 1)
        self.assertEqual(response.context['empresas_novas'], 1)
        self.assertEqual(response.context['vagas_novas'], 1)
        self.assertEqual(response.context['candidaturas_novas'], 1)
        self.assertEqual(response.context['pedidos_contacto_novos'], 1)

    def test_export_report_csv_supports_annual_period_and_summary_sections(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:export_report_csv'), {'periodo': 'anual'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        body = response.content.decode('utf-8')
        self.assertIn('Resumo executivo', body)
        self.assertIn('Resultados e conversao', body)
        self.assertIn('Destaques do periodo', body)
        self.assertIn('Anual', body)

    def test_export_report_pdf_works_for_selected_date_range(self):
        today = timezone.localdate()
        start_date = today - timedelta(days=30)
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('dashboard:export_report_pdf'),
            {
                'data_inicio': start_date.strftime('%Y-%m-%d'),
                'data_fim': today.strftime('%Y-%m-%d'),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))


class EmploymentPlacementsAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            telefone='+2399000025',
            nome='Admin Colocacoes',
            perfil=User.ProfileType.ADMIN,
        )
        self.district, _ = District.objects.get_or_create(
            codigo='LOB',
            defaults={'nome': 'Lobata'},
        )
        self.company_user = User.objects.create_user(
            telefone='+2399000026',
            nome='Empresa Coloca',
            perfil=User.ProfileType.EMPRESA,
        )
        self.company = Company.objects.create(
            user=self.company_user,
            nome='Empresa Coloca',
            ativa=True,
        )
        self.youth_user = User.objects.create_user(
            telefone='+2399000027',
            nome='Jovem Colocado',
            perfil=User.ProfileType.JOVEM,
            distrito=self.district,
        )
        self.youth = YouthProfile.objects.create(
            user=self.youth_user,
            completo=True,
            validado=True,
        )
        self.job = JobPost.objects.create(
            company=self.company,
            titulo='Assistente Administrativo',
            descricao='Apoio operacional.',
            requisitos='Organizacao e pontualidade.',
            tipo='EMP',
            estado='ATIVA',
            distrito=self.district,
        )
        Application.objects.create(
            job=self.job,
            youth=self.youth,
            estado='ACEITE',
            mensagem='Quero trabalhar nesta vaga.',
        )

        self.stage_job = JobPost.objects.create(
            company=self.company,
            titulo='Estagio TIC',
            descricao='Estagio inicial.',
            requisitos='Bases de informatica.',
            tipo='EST',
            estado='ATIVA',
        )
        Application.objects.create(
            job=self.stage_job,
            youth=self.youth,
            estado='ACEITE',
            mensagem='Aceite mas nao deve contar como emprego.',
        )

    def test_admin_can_view_employment_placements_page(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:employment_placements'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Colocações em emprego')
        self.assertContains(response, 'Jovem Colocado')
        self.assertContains(response, 'Empresa Coloca')
        self.assertContains(response, 'Assistente Administrativo')
        self.assertNotContains(response, 'Estagio TIC')

    def test_admin_dashboard_shows_placements_summary(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:admin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Colocações em emprego')
        self.assertContains(response, 'Jovem Colocado')
        self.assertContains(response, 'Empresa Coloca')

    def test_non_admin_cannot_open_employment_placements_page(self):
        self.client.force_login(self.company_user)

        response = self.client.get(reverse('dashboard:employment_placements'))

        self.assertRedirects(response, reverse('home'))


class OfflineRegistrationFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            telefone='+2399000030',
            nome='Admin Offline',
            perfil=User.ProfileType.ADMIN,
        )
        self.district, _ = District.objects.get_or_create(
            codigo='MES',
            defaults={'nome': 'Me-Zochi'},
        )
        self.company_user = User.objects.create_user(
            telefone='+2399000031',
            nome='Empresa Existente',
            perfil=User.ProfileType.EMPRESA,
            email='empresa.existente@example.com',
        )

    def test_admin_can_open_offline_registrations_page(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:offline_registrations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registos offline')
        self.assertContains(response, 'Gerar formulário offline')
        self.assertContains(response, 'Importar ficheiro offline')

    def test_non_admin_cannot_open_offline_registrations_page(self):
        self.client.force_login(self.company_user)

        response = self.client.get(reverse('dashboard:offline_registrations'))

        self.assertRedirects(response, reverse('home'))

    def test_admin_can_export_fillable_offline_youth_registration_file(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('dashboard:offline_registration_export'),
            {
                'profile_type': 'JO',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
        self.assertIn('registo_offline_jovem.html', response['Content-Disposition'])
        self.assertContains(response, 'Formulario offline de registo - Jovem')
        self.assertContains(response, 'Gerar ficheiro para importação')
        self.assertContains(response, 'bnj_offline_registration')
        self.assertTrue(
            AuditLog.objects.filter(
                user=self.admin,
                acao='Registo offline exportado',
                payload__profile_type='JO',
            ).exists()
        )

    def test_admin_can_import_offline_youth_registration(self):
        self.client.force_login(self.admin)

        payload = {
            'schema': 'bnj_offline_registration',
            'version': 1,
            'profile_type': 'JO',
            'registration_data': {
                'nome': 'Jovem Offline',
                'telefone': '+2399000090',
                'email': 'jovem.offline@example.com',
                'distrito_codigo': self.district.codigo,
                'consentimento_dados': True,
                'consentimento_contacto': True,
                'password': 'offline123',
                'password_confirm': 'offline123',
                'bi_numero': 'BI-900090',
                'data_nascimento': '2002-05-10',
                'sexo': 'F',
                'localidade': 'Trindade',
                'contacto_alternativo': '+2399000099',
                'situacao_atual': 'DES',
                'disponibilidade': 'SIM',
                'preferencia_oportunidade': 'EMP',
                'nivel': 'SEC',
                'area_formacao': 'INF',
                'instituicao': 'Liceu Nacional',
                'ano': '2024',
                'curso': 'Informatica',
                'collected_offline_at': '2026-03-20 10:00',
                'collected_by_name': 'Operador Distrital',
                'collected_by_role': 'Operador',
                'observacoes': 'Registo recolhido em zona sem internet.',
            },
        }
        uploaded = SimpleUploadedFile(
            'registo_jovem_offline.json',
            json.dumps(payload).encode('utf-8'),
            content_type='application/json',
        )

        response = self.client.post(
            reverse('dashboard:offline_registration_import'),
            {'file': uploaded},
        )

        self.assertRedirects(response, reverse('dashboard:offline_registrations'))
        user = User.objects.get(telefone='+2399000090')
        self.assertEqual(user.perfil, User.ProfileType.JOVEM)
        self.assertEqual(user.bi_numero, 'BI-900090')
        self.assertTrue(user.check_password('offline123'))
        self.assertTrue(user.has_youth_profile())
        self.assertTrue(user.youth_profile.completo)
        self.assertFalse(user.youth_profile.validado)
        self.assertTrue(
            Education.objects.filter(
                profile=user.youth_profile,
                nivel='SEC',
                area_formacao='INF',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=user,
                titulo='Registo offline recebido',
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                user=self.admin,
                acao='Registo offline importado',
                payload__file_name='registo_jovem_offline.json',
                payload__profile_type='JO',
                payload__user_name='Jovem Offline',
            ).exists()
        )

    def test_admin_can_import_offline_youth_registration_without_district(self):
        self.client.force_login(self.admin)

        payload = {
            'schema': 'bnj_offline_registration',
            'version': 1,
            'profile_type': 'JO',
            'registration_data': {
                'nome': 'Jovem Exterior Offline',
                'telefone': '+351912300201',
                'email': 'jovem.exterior@example.com',
                'password': 'offline123',
                'password_confirm': 'offline123',
                'bi_numero': 'BI-EXT-201',
                'data_nascimento': '2001-04-18',
                'sexo': 'F',
                'localidade': 'Porto, Portugal',
                'situacao_atual': 'DES',
                'disponibilidade': 'SIM',
                'preferencia_oportunidade': 'EMP',
            },
        }
        uploaded = SimpleUploadedFile(
            'registo_jovem_exterior_offline.json',
            json.dumps(payload).encode('utf-8'),
            content_type='application/json',
        )

        response = self.client.post(
            reverse('dashboard:offline_registration_import'),
            {'file': uploaded},
        )

        self.assertRedirects(response, reverse('dashboard:offline_registrations'))
        user = User.objects.get(telefone='+351912300201')
        self.assertIsNone(user.distrito)
        self.assertEqual(user.youth_profile.localidade, 'Porto, Portugal')

    def test_admin_can_import_offline_company_registration(self):
        self.client.force_login(self.admin)

        payload = {
            'schema': 'bnj_offline_registration',
            'version': 1,
            'profile_type': 'EMP',
            'registration_data': {
                'nome': 'Empresa Offline Nova',
                'telefone': '+2399000091',
                'email': 'empresa.nova@example.com',
                'distrito_codigo': self.district.codigo,
                'consentimento_dados': True,
                'consentimento_contacto': True,
                'password': 'empresa123',
                'password_confirm': 'empresa123',
                'nif': 'NIF-900091',
                'setor_codes': ['TIC', 'SER'],
                'descricao': 'Empresa criada a partir de registo offline.',
                'website': 'https://empresa.example.com',
                'endereco': 'Avenida Central, Sao Tome',
                'collected_by_name': 'Admin Offline',
            },
        }
        uploaded = SimpleUploadedFile(
            'registo_empresa_offline.json',
            json.dumps(payload).encode('utf-8'),
            content_type='application/json',
        )

        response = self.client.post(
            reverse('dashboard:offline_registration_import'),
            {'file': uploaded},
        )

        self.assertRedirects(response, reverse('dashboard:offline_registrations'))
        user = User.objects.get(telefone='+2399000091')
        self.assertEqual(user.perfil, User.ProfileType.EMPRESA)
        self.assertEqual(user.nif, 'NIF-900091')
        self.assertTrue(user.has_company_profile())
        self.assertEqual(user.company_profile.nome, 'Empresa Offline Nova')
        self.assertEqual(user.company_profile.setor, ['TIC', 'SER'])
        self.assertFalse(user.company_profile.verificada)

    def test_import_requires_password_confirmation(self):
        self.client.force_login(self.admin)

        payload = {
            'schema': 'bnj_offline_registration',
            'version': 1,
            'profile_type': 'JO',
            'registration_data': {
                'nome': 'Jovem Sem Confirmacao',
                'telefone': '+2399000092',
                'distrito_codigo': self.district.codigo,
                'password': 'offline123',
                'password_confirm': 'outra123',
                'bi_numero': 'BI-900092',
            },
        }
        uploaded = SimpleUploadedFile(
            'registo_invalido.json',
            json.dumps(payload).encode('utf-8'),
            content_type='application/json',
        )

        response = self.client.post(
            reverse('dashboard:offline_registration_import'),
            {'file': uploaded},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A palavra-passe e a confirmação não coincidem')
        self.assertFalse(User.objects.filter(telefone='+2399000092').exists())


class AdminUserListPaginationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            telefone='+2399000100',
            nome='Admin Utilizadores',
            perfil=User.ProfileType.ADMIN,
        )
        base_time = timezone.now() - timedelta(days=1)
        for index in range(21):
            User.objects.create_user(
                telefone=f'+2399110{index:03d}',
                nome=f'Utilizador paginado {index:02d}',
                perfil=User.ProfileType.JOVEM,
                date_joined=base_time + timedelta(minutes=index),
            )

    def test_admin_user_list_is_paginated_and_keeps_filters(self):
        self.client.force_login(self.admin)

        first_page = self.client.get(reverse('dashboard:user_list'), {'perfil': 'JO'})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context['users_page'].number, 1)
        self.assertEqual(first_page.context['users_page'].paginator.count, 21)
        self.assertEqual(first_page.context['users_page'].paginator.num_pages, 3)
        self.assertEqual(len(first_page.context['users']), 10)
        self.assertContains(first_page, 'perfil=JO')
        self.assertContains(first_page, 'page=2#lista-utilizadores')

        second_page = self.client.get(
            reverse('dashboard:user_list'),
            {'perfil': 'JO', 'page': 2},
        )

        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(second_page.context['users_page'].number, 2)
        self.assertEqual(len(second_page.context['users']), 10)
        self.assertContains(second_page, 'page=3#lista-utilizadores')
        self.assertContains(second_page, 'Utilizador paginado 10')
        self.assertNotContains(second_page, 'Utilizador paginado 20')

        third_page = self.client.get(
            reverse('dashboard:user_list'),
            {'perfil': 'JO', 'page': 3},
        )

        self.assertEqual(third_page.status_code, 200)
        self.assertEqual(third_page.context['users_page'].number, 3)
        self.assertEqual(len(third_page.context['users']), 1)
        self.assertContains(third_page, 'Utilizador paginado 00')
