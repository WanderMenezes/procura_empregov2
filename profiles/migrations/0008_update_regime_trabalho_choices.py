from django.db import migrations, models


def migrate_legacy_regime_trabalho(apps, schema_editor):
    YouthProfile = apps.get_model('profiles', 'YouthProfile')
    YouthProfile.objects.filter(regime_trabalho='IND').update(regime_trabalho='PRE')


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0007_youthprofile_regime_trabalho'),
    ]

    operations = [
        migrations.RunPython(
            migrate_legacy_regime_trabalho,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='youthprofile',
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
