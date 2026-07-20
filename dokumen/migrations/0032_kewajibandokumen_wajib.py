from django.db import migrations, models


OPTIONAL_DOCUMENT_URLS = ('hukuman', 'penghargaan')


def mark_optional_documents(apps, schema_editor):
    KewajibanDokumen = apps.get_model('dokumen', 'KewajibanDokumen')
    KewajibanDokumen.objects.filter(
        dokumen__url__in=OPTIONAL_DOCUMENT_URLS,
    ).update(wajib=False)


def mark_documents_required(apps, schema_editor):
    KewajibanDokumen = apps.get_model('dokumen', 'KewajibanDokumen')
    KewajibanDokumen.objects.filter(
        dokumen__url__in=OPTIONAL_DOCUMENT_URLS,
    ).update(wajib=True)


class Migration(migrations.Migration):

    dependencies = [
        ('dokumen', '0031_kewajibandokumen'),
    ]

    operations = [
        migrations.AddField(
            model_name='kewajibandokumen',
            name='wajib',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'Jika tidak wajib, menu tetap terlihat tetapi tidak '
                    'ditandai merah saat kosong.'
                ),
            ),
        ),
        migrations.RunPython(
            mark_optional_documents,
            mark_documents_required,
        ),
    ]
