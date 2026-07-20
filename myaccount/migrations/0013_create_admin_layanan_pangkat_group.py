from django.db import migrations


GROUP_NAME = 'Admin Layanan Pangkat'


def create_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name=GROUP_NAME)


def delete_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('myaccount', '0012_create_admin_groups'),
    ]

    operations = [
        migrations.RunPython(create_group, delete_group),
    ]
