from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0008_jobpost_regime_trabalho'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobpost',
            name='regime_trabalho',
            field=models.CharField(
                choices=[
                    ('PRE', 'Presencial'),
                    ('REM', 'Remoto (home office)'),
                    ('HIB', 'Hibrido'),
                    ('INT', 'Tempo integral (full-time)'),
                    ('PAR', 'Tempo parcial (part-time)'),
                    ('TEM', 'Temporario'),
                    ('INF', 'Informal'),
                ],
                default='PRE',
                max_length=3,
                verbose_name='regime da oportunidade',
            ),
        ),
    ]
