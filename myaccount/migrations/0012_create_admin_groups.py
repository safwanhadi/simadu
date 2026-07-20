from django.db import migrations


ADMIN_GROUPS = (
    "Admin Dashboard",
    "Admin Dokumen SDM",
    "Admin Layanan Cuti",
    "Admin Layanan Berkala",
    "Admin Layanan Diklat",
    "Admin Layanan Inovasi",
    "Admin Layanan SIP",
    "Admin Disiplin SDM",
    "Admin Informasi",
    "Admin Laporan",
    "Admin Akun",
)


def create_admin_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for group_name in ADMIN_GROUPS:
        Group.objects.get_or_create(name=group_name)


class Migration(migrations.Migration):

    dependencies = [
        ('myaccount', '0011_profiladmin_is_pejabat_remove_profiladmin_bidang_and_more'),
    ]

    operations = [
        migrations.RunPython(create_admin_groups, migrations.RunPython.noop),
    ]
