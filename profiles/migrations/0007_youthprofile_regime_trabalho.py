from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0006_education_outra_area_formacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='youthprofile',
            name='regime_trabalho',
            field=models.CharField(
                choices=[
                    ('IND', 'Indiferente'),
                    ('PRE', 'Presencial'),
                    ('HIB', 'Hibrido'),
                    ('REM', 'Remoto'),
                ],
                default='IND',
                max_length=3,
                verbose_name='regime de trabalho',
            ),
        ),
    ]
