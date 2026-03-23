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
