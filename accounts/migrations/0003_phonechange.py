from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PhoneChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('new_phone', models.CharField(max_length=20, verbose_name='novo telemóvel')),
                ('code', models.CharField(max_length=6, verbose_name='código')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('used', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, to='accounts.user')),
            ],
            options={
                'verbose_name': 'alteração de telemóvel',
                'verbose_name_plural': 'alterações de telemóvel',
            },
        ),
    ]
