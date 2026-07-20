from django.db import migrations


GROUP_NAME = 'Admin Layanan Jabatan'


def create_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name=GROUP_NAME)


def delete_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('myaccount', '0013_create_admin_layanan_pangkat_group'),
    ]

    operations = [
        migrations.RunPython(create_group, delete_group),
    ]
