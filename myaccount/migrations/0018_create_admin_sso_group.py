from django.db import migrations


GROUP_NAME = 'Admin SSO'


def create_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name=GROUP_NAME)


def remove_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [('myaccount', '0017_adminscopeassignment_and_more')]
    operations = [migrations.RunPython(create_group, remove_group)]
