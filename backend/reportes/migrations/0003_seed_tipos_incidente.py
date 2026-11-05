from django.db import migrations

TIPOS = [
    ('Bache', 'Baches y daños en el pavimento'),
    ('Choque', 'Choques y accidentes viales'),
    ('Inundación', 'Encharcamientos e inundaciones en la vía'),
    ('Tráfico', 'Tráfico intenso o sin movimiento'),
    ('Obstrucción', 'Obstrucción vial'),
    # El usuario describe el incidente: semáforos que no funcionan, retenes, etc.
    ('Otro', 'Incidentes menos frecuentes; el usuario los describe'),
]


def cargar(apps, schema_editor):
    TipoIncidente = apps.get_model('reportes', 'TipoIncidente')
    for nombre, descripcion in TIPOS:
        TipoIncidente.objects.get_or_create(nombre=nombre, defaults={'descripcion': descripcion})


class Migration(migrations.Migration):
    dependencies = [('reportes', '0002_initial')]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
