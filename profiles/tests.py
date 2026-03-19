from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import AuditLog, District
from profiles.models import Education, YouthProfile


User = get_user_model()


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
        self.assertEqual(created_education.area_formacao, 'TIC')
        self.assertEqual(created_log.user, self.operator)
        self.assertEqual(
            created_log.payload['observacoes'],
            'Atendimento presencial com apoio documental.',
        )

    def test_non_operator_cannot_access_assisted_registration(self):
        young_user = User.objects.create_user(
            telefone='+2399000300',
            nome='Jovem Teste',
            perfil=User.ProfileType.JOVEM,
        )
        self.client.force_login(young_user)

        response = self.client.get(reverse('profiles:assisted_register'))

        self.assertRedirects(response, reverse('home'))
