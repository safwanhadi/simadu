from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('strukturorg', '0003_pejabatstruktur'),
    ]

    operations = [
        migrations.AddField(
            model_name='pejabatstruktur',
            name='jenis_penugasan',
            field=models.CharField(
                choices=[
                    ('definitif', 'Definitif'),
                    ('plt', 'Pelaksana Tugas (Plt.)'),
                    ('plh', 'Pelaksana Harian (Plh.)'),
                ],
                default='definitif',
                max_length=12,
            ),
        ),
    ]
