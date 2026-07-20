from django.db import migrations


def create_jenis_layanan(apps, schema_editor):
    JenisLayanan = apps.get_model('layanan', 'JenisLayanan')
    matches = list(JenisLayanan.objects.filter(url='yanjabatan').order_by('pk'))
    layanan = matches[0] if matches else JenisLayanan(url='yanjabatan')

    duplicate_ids = [item.pk for item in matches[1:]]
    if duplicate_ids:
        for model in apps.get_app_config('layanan').get_models():
            for field in model._meta.fields:
                if (
                    field.is_relation
                    and field.many_to_one
                    and field.related_model == JenisLayanan
                ):
                    model.objects.filter(
                        **{f'{field.attname}__in': duplicate_ids}
                    ).update(**{field.attname: layanan.pk})
        JenisLayanan.objects.filter(pk__in=duplicate_ids).delete()

    layanan.nama = 'Kenaikan Jabatan'
    layanan.status = True
    layanan.icon = 'fa-user-tie'
    layanan.save()


def delete_jenis_layanan(apps, schema_editor):
    JenisLayanan = apps.get_model('layanan', 'JenisLayanan')
    JenisLayanan.objects.filter(url='yanjabatan').update(status=False)


class Migration(migrations.Migration):

    dependencies = [
        ('layanan', '0029_layanannaikjabatan_is_read_and_more'),
    ]

    operations = [
        migrations.RunPython(create_jenis_layanan, delete_jenis_layanan),
    ]
