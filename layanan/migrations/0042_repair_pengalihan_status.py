from django.db import migrations, models


TABLE_NAME = "layanan_pengalihanpelimpahantugas"
COLUMN_NAME = "status"


def add_status_if_missing(apps, schema_editor):
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor,
                TABLE_NAME,
            )
        }

    if COLUMN_NAME in columns:
        return

    model = apps.get_model("layanan", "PengalihanPelimpahanTugas")
    field = models.CharField(max_length=15, default="menunggu")
    field.set_attributes_from_name(COLUMN_NAME)
    schema_editor.add_field(model, field)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("layanan", "0041_pengalihanpelimpahantugas"),
    ]

    operations = [
        migrations.RunPython(
            add_status_if_missing,
            migrations.RunPython.noop,
            atomic=False,
        ),
    ]
