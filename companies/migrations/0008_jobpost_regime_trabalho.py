from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0007_alter_contactrequest_estado'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobpost',
            name='regime_trabalho',
            field=models.CharField(
                choices=[
                    ('PRE', 'Trabalho presencial'),
                    ('REM', 'Trabalho remoto (home office)'),
                    ('HIB', 'Trabalho hibrido'),
                    ('INT', 'Tempo integral (full-time)'),
                    ('PAR', 'Tempo parcial (part-time)'),
                    ('TEM', 'Trabalho temporario'),
                    ('INF', 'Trabalho informal'),
                ],
                default='PRE',
                max_length=3,
                verbose_name='regime de trabalho',
            ),
        ),
    ]
