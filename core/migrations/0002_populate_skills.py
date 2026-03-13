from django.db import migrations


def create_skills(apps, schema_editor):
    Skill = apps.get_model('core', 'Skill')

    skills = [
        ('Comunicação', 'TRA'),
        ('Trabalho em equipa', 'TRA'),
        ('Liderança', 'TRA'),
        ('Gestão de projetos', 'TRA'),
        ('Atendimento ao cliente', 'TRA'),
        ('Contabilidade', 'TEC'),
        ('Marketing', 'TRA'),
        ('Programação', 'TEC'),
        ('Desenvolvimento web', 'TEC'),
        ('Informática', 'TEC'),
        ('Design Gráfico', 'TEC'),
        ('Carpintaria', 'TEC'),
        ('Eletricidade', 'TEC'),
        ('Canalização', 'TEC'),
        ('Agricultura', 'TEC'),
        ('Turismo', 'TRA'),
        ('Idiomas', 'TRA'),
        ('UX/UI', 'TEC'),
    ]

    for nome, tipo in skills:
        Skill.objects.get_or_create(nome=nome, defaults={'tipo': tipo})


def reverse_func(apps, schema_editor):
    Skill = apps.get_model('core', 'Skill')
    names = [
        'Comunicação', 'Trabalho em equipa', 'Liderança', 'Gestão de projetos',
        'Atendimento ao cliente', 'Contabilidade', 'Marketing', 'Programação',
        'Desenvolvimento web', 'Informática', 'Design Gráfico', 'Carpintaria',
        'Eletricidade', 'Canalização', 'Agricultura', 'Turismo', 'Idiomas', 'UX/UI'
    ]
    Skill.objects.filter(nome__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_skills, reverse_func),
    ]
