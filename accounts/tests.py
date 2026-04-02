import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import PasswordResetCode
from accounts.sms import send_whatsapp
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
        self.assertContains(response, 'Entrar com seguranca')
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

    def test_request_page_offers_email_and_whatsapp_channels(self):
        response = self.client.get(reverse('accounts:password_reset_request'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WhatsApp')
        self.assertContains(response, 'name="channel"', html=False)
        self.assertContains(response, 'id="id_telefone"', html=False)

    @patch('accounts.views.send_mail', return_value=1)
    def test_password_reset_request_can_send_code_by_email(self, mocked_send_mail):
        response = self.client.post(
            reverse('accounts:password_reset_request'),
            {
                'channel': 'email',
                'email': self.user.email,
                'telefone': '',
            },
        )

        self.assertRedirects(response, reverse('accounts:password_reset_confirm'), fetch_redirect_response=False)
        reset_code = PasswordResetCode.objects.get(user=self.user, used=False)
        self.assertEqual(self.client.session['reset_user_id'], self.user.id)
        self.assertEqual(self.client.session['reset_channel'], 'email')
        mocked_send_mail.assert_called_once()
        self.assertIn(reset_code.code, mocked_send_mail.call_args.args[1])

    @override_settings(
        WHATSAPP_BACKEND='twilio',
        TWILIO_ACCOUNT_SID='AC_TEST',
        TWILIO_AUTH_TOKEN='token-test',
        TWILIO_WHATSAPP_FROM_NUMBER='whatsapp:+14155238886',
    )
    @patch('accounts.views.send_whatsapp', return_value=True)
    def test_password_reset_request_can_send_code_by_whatsapp(self, mocked_send_whatsapp):
        response = self.client.post(
            reverse('accounts:password_reset_request'),
            {
                'channel': 'whatsapp',
                'email': '',
                'telefone': self.user.telefone,
            },
        )

        self.assertRedirects(response, reverse('accounts:password_reset_confirm'), fetch_redirect_response=False)
        reset_code = PasswordResetCode.objects.get(user=self.user, used=False)
        self.assertEqual(self.client.session['reset_user_id'], self.user.id)
        self.assertEqual(self.client.session['reset_channel'], 'whatsapp')
        mocked_send_whatsapp.assert_called_once()
        self.assertEqual(mocked_send_whatsapp.call_args.args[0], self.user.telefone)
        self.assertIn(reset_code.code, mocked_send_whatsapp.call_args.args[1])

    @override_settings(
        WHATSAPP_BACKEND='twilio',
        TWILIO_ACCOUNT_SID='AC_TEST',
        TWILIO_AUTH_TOKEN='token-test',
        TWILIO_WHATSAPP_FROM_NUMBER='whatsapp:+14155238886',
    )
    @patch('accounts.views.send_whatsapp', return_value=False)
    def test_password_reset_request_shows_error_when_whatsapp_delivery_fails(self, mocked_send_whatsapp):
        response = self.client.post(
            reverse('accounts:password_reset_request'),
            {
                'channel': 'whatsapp',
                'email': '',
                'telefone': self.user.telefone,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WhatsApp')
        self.assertFalse(PasswordResetCode.objects.filter(user=self.user).exists())
        mocked_send_whatsapp.assert_called_once()

    def test_password_reset_request_requires_registered_phone_for_whatsapp(self):
        response = self.client.post(
            reverse('accounts:password_reset_request'),
            {
                'channel': 'whatsapp',
                'email': '',
                'telefone': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'telem')
        self.assertFalse(PasswordResetCode.objects.exists())


class WhatsAppDeliveryTests(TestCase):
    @override_settings(
        WHATSAPP_BACKEND='twilio',
        TWILIO_ACCOUNT_SID='AC_TEST',
        TWILIO_AUTH_TOKEN='token-test',
        TWILIO_WHATSAPP_FROM_NUMBER='whatsapp:+14155238886',
        TWILIO_WHATSAPP_CONTENT_SID='HX229f5a04fd0510ce1b071852155d3e75',
    )
    @patch('twilio.rest.Client')
    def test_send_whatsapp_uses_content_template_when_configured(self, mocked_client):
        sent = send_whatsapp(
            '+2399940219',
            'O teu cÃ³digo de recuperaÃ§Ã£o Ã©: 409173',
            content_variables={'1': '409173'},
        )

        self.assertTrue(sent)
        mocked_client.assert_called_once_with('AC_TEST', 'token-test')
        kwargs = mocked_client.return_value.messages.create.call_args.kwargs
        self.assertEqual(kwargs['from_'], 'whatsapp:+14155238886')
        self.assertEqual(kwargs['to'], 'whatsapp:+2399940219')
        self.assertEqual(kwargs['content_sid'], 'HX229f5a04fd0510ce1b071852155d3e75')
        self.assertEqual(json.loads(kwargs['content_variables']), {'1': '409173'})
        self.assertNotIn('body', kwargs)


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
