import json

from django.db import migrations, models


def wrap_company_setor(apps, schema_editor):
    Company = apps.get_model('companies', 'Company')

    for company in Company.objects.all():
        value = company.setor
        if value in (None, ''):
            company.setor = '[]'
        else:
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    company.setor = json.dumps(parsed)
                elif isinstance(parsed, str):
                    company.setor = json.dumps([parsed])
                else:
                    company.setor = json.dumps([str(parsed)])
            except Exception:
                if isinstance(value, (list, tuple, set)):
                    company.setor = json.dumps([str(item) for item in value if item])
                else:
                    company.setor = json.dumps([value])
        company.save(update_fields=['setor'])


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0005_jobpost_numero_vagas'),
    ]

    operations = [
        migrations.RunPython(wrap_company_setor, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='company',
            name='setor',
            field=models.JSONField(blank=True, default=list, verbose_name='setores de atividade'),
        ),
    ]
