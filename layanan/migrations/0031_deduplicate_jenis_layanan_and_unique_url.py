from django.db import migrations, models


def deduplicate_services(apps, schema_editor):
    JenisLayanan = apps.get_model('layanan', 'JenisLayanan')

    urls = (
        JenisLayanan.objects.exclude(url__isnull=True)
        .exclude(url='')
        .values_list('url', flat=True)
        .distinct()
    )
    for url in urls:
        matches = list(JenisLayanan.objects.filter(url=url).order_by('pk'))
        if len(matches) < 2:
            continue

        canonical = matches[0]
        duplicate_ids = [item.pk for item in matches[1:]]
        for model in apps.get_app_config('layanan').get_models():
            for field in model._meta.fields:
                if (
                    field.is_relation
                    and field.many_to_one
                    and field.related_model == JenisLayanan
                ):
                    model.objects.filter(
                        **{f'{field.attname}__in': duplicate_ids}
                    ).update(**{field.attname: canonical.pk})

        JenisLayanan.objects.filter(pk__in=duplicate_ids).delete()

    JenisLayanan.objects.filter(url='').update(url=None)


class Migration(migrations.Migration):

    dependencies = [
        ('layanan', '0030_create_jenis_layanan_jabatan'),
    ]

    operations = [
        migrations.RunPython(deduplicate_services, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='jenislayanan',
            name='url',
            field=models.CharField(
                blank=True,
                max_length=50,
                null=True,
                unique=True,
            ),
        ),
    ]
