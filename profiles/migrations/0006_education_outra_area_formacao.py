from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0005_youthprofile_idiomas'),
    ]

    operations = [
        migrations.AddField(
            model_name='education',
            name='outra_area_formacao',
            field=models.CharField(blank=True, max_length=255, verbose_name='outra área de formação'),
        ),
    ]
