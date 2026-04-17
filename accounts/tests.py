import json

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import PasswordResetCode, SecurityQuestion
from core.models import Notification


User = get_user_model()


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            telefone='+2399000100',
            nome='Jovem Login',
            perfil=User.ProfileType.JOVEM,
            password='SenhaSegura123',
            email='jovem.login@example.com',
        )

    def test_login_page_renders_new_layout(self):
        response = self.client.get(reverse('accounts:login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Entrar na plataforma sem perder o fio ao trabalho.')
        self.assertContains(response, 'Entrar com segurança')
        self.assertContains(response, reverse('accounts:password_reset_request'))

    def test_login_respects_safe_next_url(self):
        response = self.client.post(
            f"{reverse('accounts:login')}?next={reverse('about')}",
            {
                'username': self.user.telefone,
                'password': 'SenhaSegura123',
                'remember_me': 'on',
            },
        )

        self.assertRedirects(response, reverse('about'), fetch_redirect_response=False)

    def test_login_accepts_email(self):
        response = self.client.post(
            reverse('accounts:login'),
            {
                'username': self.user.email,
                'password': 'SenhaSegura123',
            },
        )

        self.assertRedirects(response, reverse('profiles:wizard'), fetch_redirect_response=False)

    def test_login_accepts_email_case_insensitively(self):
        response = self.client.post(
            reverse('accounts:login'),
            {
                'username': 'JOVEM.LOGIN@EXAMPLE.COM',
                'password': 'SenhaSegura123',
            },
        )

        self.assertRedirects(response, reverse('profiles:wizard'), fetch_redirect_response=False)

    def test_login_ignores_external_next_url(self):
        response = self.client.post(
            f"{reverse('accounts:login')}?next=https://example.com/fora",
            {
                'username': self.user.telefone,
                'password': 'SenhaSegura123',
            },
        )

        self.assertRedirects(response, reverse('profiles:wizard'), fetch_redirect_response=False)

    def test_protected_account_page_redirects_to_localized_login_url(self):
        response = self.client.get(reverse('accounts:profile'))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:profile')}",
            fetch_redirect_response=False,
        )

    def test_legacy_login_url_redirects_to_current_login_page(self):
        response = self.client.get('/accounts/login/')

        self.assertRedirects(response, reverse('accounts:login'), fetch_redirect_response=False)


class RegisterViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            telefone='+2399000199',
            nome='Admin Notificacoes',
            perfil=User.ProfileType.ADMIN,
        )

    def _company_payload(self, **overrides):
        payload = {
            'perfil': User.ProfileType.EMPRESA,
            'nome': 'Empresa Horizonte',
            'telefone': '+2399000111',
            'email': 'empresa.horizonte@example.com',
            'nif': '123456789',
            'password1': 'SenhaSegura123',
            'password2': 'SenhaSegura123',
            'consentimento_dados': 'on',
            'consentimento_contacto': 'on',
            'confirmacao_empresa': 'on',
            'question_1': 'mother_second_name',
            'answer_1': 'Maria',
            'question_2': 'father_second_name',
            'answer_2': 'João',
            'question_3': 'favorite_pet_name',
            'answer_3': 'Rex',
        }
        payload.update(overrides)
        return payload

    def _youth_payload(self, **overrides):
        payload = {
            'perfil': User.ProfileType.JOVEM,
            'nome': 'Ana Candidata',
            'telefone': '+2399000112',
            'email': 'ana.candidata@example.com',
            'bi_numero': 'BI-ANA-112',
            'password1': 'SenhaSegura123',
            'password2': 'SenhaSegura123',
            'consentimento_dados': 'on',
            'consentimento_contacto': 'on',
            'question_1': 'mother_second_name',
            'answer_1': 'Maria',
            'question_2': 'father_second_name',
            'answer_2': 'João',
            'question_3': 'favorite_pet_name',
            'answer_3': 'Rex',
        }
        payload.update(overrides)
        return payload

    def test_register_page_includes_company_confirmation_prompt(self):
        response = self.client.get(reverse('accounts:register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Esta conta é mesmo para uma empresa?')
        self.assertContains(response, 'confirmacao_empresa')

    def test_company_registration_requires_company_confirmation(self):
        response = self.client.post(
            reverse('accounts:register'),
            self._company_payload(confirmacao_empresa=''),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirma que este registo é para uma empresa antes de continuar.')
        self.assertFalse(User.objects.filter(telefone='+2399000111').exists())

    def test_company_registration_succeeds_with_company_confirmation(self):
        response = self.client.post(
            reverse('accounts:register'),
            self._company_payload(),
        )

        self.assertRedirects(response, reverse('accounts:login'), fetch_redirect_response=False)
        user = User.objects.get(telefone='+2399000111')
        self.assertEqual(user.perfil, User.ProfileType.EMPRESA)
        self.assertEqual(user.nome_empresa, 'Empresa Horizonte')
        self.assertEqual(user.nif, '123456789')
        self.assertEqual(user.security_questions.count(), 3)
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin,
                titulo='Novo utilizador registado',
                mensagem__icontains='Empresa Horizonte',
            ).exists()
        )

    def test_youth_registration_notifies_admin_that_validation_waits_for_minimum_progress(self):
        response = self.client.post(
            reverse('accounts:register'),
            self._youth_payload(),
        )

        self.assertRedirects(response, reverse('accounts:login'), fetch_redirect_response=False)
        notification = Notification.objects.filter(
            user=self.admin,
            titulo='Novo utilizador registado',
            mensagem__icontains='ainda nao entra na fila de validacao',
        ).first()
        self.assertIsNotNone(notification)
        self.assertIn('Ana Candidata', notification.mensagem)
        self.assertIn('50%', notification.mensagem)


class PasswordResetRequestTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            telefone='+2399000201',
            nome='Conta Recuperacao',
            perfil=User.ProfileType.JOVEM,
            password='SenhaSegura123',
            email='recuperacao@example.com',
        )

    def test_request_page_shows_security_question_recovery_prompt(self):
        response = self.client.get(reverse('accounts:password_reset_request'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Responde às tuas perguntas de segurança')
        self.assertContains(response, 'id="id_telefone"', html=False)
        self.assertContains(response, 'id="id_email"', html=False)

    def test_password_reset_request_requires_email_or_phone(self):
        response = self.client.post(
            reverse('accounts:password_reset_request'),
            {
                'email': '',
                'telefone': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Indica o teu email ou telemóvel registado.')
        self.assertFalse(PasswordResetCode.objects.exists())

    def test_password_reset_request_can_start_security_questions_flow(self):
        question = SecurityQuestion(
            user=self.user,
            question_key='mother_second_name',
            order=1,
        )
        question.set_answer('Maria')
        question.save()
        question = SecurityQuestion(
            user=self.user,
            question_key='father_second_name',
            order=2,
        )
        question.set_answer('João')
        question.save()
        question = SecurityQuestion(
            user=self.user,
            question_key='favorite_pet_name',
            order=3,
        )
        question.set_answer('Rex')
        question.save()

        response = self.client.post(
            reverse('accounts:password_reset_request'),
            {
                'email': self.user.email,
                'telefone': '',
            },
        )

        self.assertRedirects(response, reverse('accounts:password_reset_confirm'), fetch_redirect_response=False)
        self.assertEqual(self.client.session['reset_channel'], 'security_questions')
        self.assertEqual(self.client.session['reset_user_id'], self.user.id)

    def test_password_reset_confirm_with_security_questions_changes_password(self):
        question = SecurityQuestion(
            user=self.user,
            question_key='mother_second_name',
            order=1,
        )
        question.set_answer('Maria')
        question.save()
        question = SecurityQuestion(
            user=self.user,
            question_key='father_second_name',
            order=2,
        )
        question.set_answer('João')
        question.save()
        question = SecurityQuestion(
            user=self.user,
            question_key='favorite_pet_name',
            order=3,
        )
        question.set_answer('Rex')
        question.save()

        self.client.post(
            reverse('accounts:password_reset_request'),
            {
                'email': self.user.email,
                'telefone': '',
            },
        )

        response = self.client.post(
            reverse('accounts:password_reset_confirm'),
            {
                'answer_1': 'Maria',
                'answer_2': 'João',
                'answer_3': 'Rex',
                'new_password': 'NovaSenha123',
                'confirm_password': 'NovaSenha123',
            },
        )

        self.assertRedirects(response, reverse('accounts:login'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NovaSenha123'))




class NotificationViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            telefone='+2399000301',
            nome='Admin Centro',
            perfil=User.ProfileType.ADMIN,
        )

    def test_admin_notifications_are_grouped_by_operational_topic(self):
        Notification.objects.create(
            user=self.admin,
            titulo='Novo utilizador registado',
            mensagem='Novo utilizador registado na plataforma: Ana (Jovem).',
            tipo='INFO',
        )
        Notification.objects.create(
            user=self.admin,
            titulo='Perfil pronto para validacao',
            mensagem='O perfil de Ana atingiu 66% e aguarda validacao administrativa.',
            tipo='INFO',
        )
        Notification.objects.create(
            user=self.admin,
            titulo='Novo pedido de contacto',
            mensagem='A empresa "Empresa Centro" solicitou contacto com Ana.',
            tipo='INFO',
        )
        Notification.objects.create(
            user=self.admin,
            titulo='Nova colocacao em emprego',
            mensagem='A candidatura de Ana foi aceite e conta como colocacao.',
            tipo='SUCESSO',
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:notifications'))

        self.assertEqual(response.status_code, 200)
        groups = response.context['notification_groups']
        self.assertEqual(
            [group['key'] for group in groups],
            ['colocacoes', 'contactos', 'validacao', 'utilizadores'],
        )
        self.assertEqual(
            [notification.titulo for notification in response.context['notifications'][:2]],
            ['Nova colocacao em emprego', 'Novo pedido de contacto'],
        )
        self.assertContains(response, 'Utilizadores')
        self.assertContains(response, 'Validacao')
        self.assertContains(response, 'Contactos')
        self.assertContains(response, 'Colocacoes')

    def test_job_publication_notification_renders_clickable_link(self):
        Notification.objects.create(
            user=self.admin,
            titulo='Nova vaga publicada',
            mensagem='Veja os detalhes e candidata-te clicando <a href="/profiles/vagas-disponiveis/?vaga=12">aqui</a>.',
            tipo='INFO',
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:notifications'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<a href="/profiles/vagas-disponiveis/?vaga=12">aqui</a>',
            html=False,
        )
