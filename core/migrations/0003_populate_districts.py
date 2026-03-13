from django.db import migrations


def create_districts(apps, schema_editor):
    District = apps.get_model('core', 'District')

    districts = [
        ('AGU', 'Água Grande'),
        ('CAN', 'Cantagalo'),
        ('CAU', 'Caué'),
        ('LEM', 'Lembá'),
        ('LOB', 'Lobata'),
        ('MEZ', 'Mé-Zóchi'),
        ('PAG', 'Pagué'),
    ]

    for codigo, nome in districts:
        District.objects.get_or_create(codigo=codigo, defaults={'nome': nome})


def reverse_func(apps, schema_editor):
    District = apps.get_model('core', 'District')
    codes = ['AGU', 'CAN', 'CAU', 'LEM', 'LOB', 'MEZ', 'PAG']
    District.objects.filter(codigo__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_populate_skills'),
    ]

    operations = [
        migrations.RunPython(create_districts, reverse_func),
    ]
