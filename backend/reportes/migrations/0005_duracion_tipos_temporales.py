from django.db import migrations

# Incidentes pasajeros: se dejan de mostrar 24 h después de publicarse.
# Bache, Obstrucción y Otro quedan sin límite (duracion_horas = NULL).
TIPOS_TEMPORALES = ['Choque', 'Tráfico', 'Inundación']
HORAS = 24


def fijar_duracion(apps, schema_editor):
    # apps.get_model da el modelo "histórico" (como estaba en esta migración),
    # no el de models.py, que podría cambiar en el futuro.
    TipoIncidente = apps.get_model('reportes', 'TipoIncidente')
    TipoIncidente.objects.filter(nombre__in=TIPOS_TEMPORALES).update(duracion_horas=HORAS)


class Migration(migrations.Migration):
    dependencies = [('reportes', '0004_tipoincidente_duracion_horas')]
    # Reversa sin efecto: al revertir la 0004 la columna desaparece de todos modos.
    operations = [migrations.RunPython(fijar_duracion, migrations.RunPython.noop)]
