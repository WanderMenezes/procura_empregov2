from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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
