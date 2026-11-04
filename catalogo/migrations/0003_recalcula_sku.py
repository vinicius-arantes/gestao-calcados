from django.db import migrations


def recalcular_skus(apps, schema_editor):
    """Converte os SKUs existentes para o formato referência-id da cor-numeração."""
    Variacao = apps.get_model('catalogo', 'Variacao')
    for variacao in Variacao.objects.select_related('modelo', 'tamanho'):
        variacao.sku = f'{variacao.modelo.referencia}-{variacao.cor_id}-{variacao.tamanho.numero}'
        variacao.save(update_fields=['sku'])


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0002_modelo_ficha_tecnica_variacao'),
    ]

    operations = [
        # O formato antigo continua único, então não há o que desfazer ao reverter
        migrations.RunPython(recalcular_skus, migrations.RunPython.noop),
    ]
