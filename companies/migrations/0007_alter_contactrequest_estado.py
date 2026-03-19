from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0006_company_setor_multiple'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactrequest',
            name='estado',
            field=models.CharField(
                choices=[
                    ('PENDENTE', 'Pendente'),
                    ('APROVADO', 'Aprovado'),
                    ('DESATIVADO', 'Desativado'),
                    ('REJEITADO', 'Rejeitado'),
                ],
                default='PENDENTE',
                max_length=10,
                verbose_name='estado',
            ),
        ),
    ]
