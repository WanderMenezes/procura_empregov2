from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from companies.models import Application, Company, ContactRequest, JobPost
from core.models import District, Notification
from profiles.models import Education, YouthProfile


User = get_user_model()


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
        self.assertContains(response, 'Tecnico PNUD')
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
        self.assertContains(response, 'Dashboard Tecnico PNUD')
        self.assertContains(response, 'Jovens por distrito')
        self.assertContains(response, 'Jovem Tecnico')
        self.assertContains(response, 'Empresa Observatorio')
        self.assertContains(response, 'Analista TIC')

    def test_non_tecnico_cannot_open_dashboard(self):
        self.client.force_login(self.company_user)

        response = self.client.get(reverse('dashboard:tecnico'))

        self.assertRedirects(response, reverse('home'))


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
        Application.objects.create(
            job=self.job,
            youth=self.youth,
            mensagem='Quero participar.',
        )

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
