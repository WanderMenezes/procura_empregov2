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
            completo=True,
            validado=False,
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
        self.assertContains(response, 'Gerar formulario offline')
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
        self.assertContains(response, 'Gerar ficheiro para importacao')
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
        self.assertContains(response, 'A palavra-passe e a confirmacao nao coincidem')
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
