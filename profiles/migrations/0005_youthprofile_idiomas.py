from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0004_alter_youthprofile_interesse_setorial'),
    ]

    operations = [
        migrations.AddField(
            model_name='youthprofile',
            name='idiomas',
            field=models.JSONField(blank=True, default=list, verbose_name='idiomas dominados'),
        ),
    ]
