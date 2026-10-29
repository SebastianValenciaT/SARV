"""python manage.py seed_demo — carga datos de ejemplo para desarrollo.

Un "management command" es un script que Django ejecuta con manage.py,
con acceso a los modelos y a settings. Es idempotente: si los reportes demo
ya existen, no los duplica. Con --reset borra los reportes demo y los vuelve
a crear (útil porque las fechas son relativas a "ahora").

La mayoría de los reportes son del usuario demo (para ver la vista del autor);
los últimos son de vecinos, para probar con el usuario demo cómo se reacciona y se
denuncia un reporte ajeno: uno sin reacción suya, uno que ya denunció y uno resuelto.
"""
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image as PilImage
from PIL import ImageDraw

from reportes.models import Denuncia, Imagen, Reaccion, Reporte, TipoIncidente
from usuarios.models import Usuario

# Credenciales SOLO de desarrollo (documentadas en el README). No son secretos.
PASSWORD_DEMO = 'demo12345'
AUTOR = ('demo@sarv.example', 'Usuario Demo')
VECINOS = [
    ('vecino1@sarv.example', 'Vecina Uno'),
    ('vecino2@sarv.example', 'Vecino Dos'),
    ('vecino3@sarv.example', 'Vecina Tres'),
]

# La zona no se escribe: Reporte.save() la calcula con zona_de(lat, lng).
# `autor`: índice en VECINOS (sin la clave, el autor es el usuario demo). Las
# `reacciones` las hacen los vecinos en orden, saltándose al autor del reporte.
# `reaccion_demo` / `denuncia_demo`: lo que ya hizo el usuario demo en ese reporte.
REPORTES = [
    dict(tipo='Inundación', titulo='Inundación en el cruce', direccion='Av. 16 de Septiembre y Juárez',
         latitud='31.739300', longitud='-106.485200', gravedad='grave', hace=timedelta(minutes=40),
         imagenes=2, reacciones=['sin_resolver', 'sin_resolver', 'resuelto'],
         descripcion='El agua cubre ambos carriles después de la lluvia; los autos pasan muy despacio.'),
    dict(tipo='Bache', titulo='Bache profundo en carril derecho',
         direccion='Av. Tecnológico y Plutarco Elías Calles', latitud='31.710500', longitud='-106.424500',
         gravedad='moderado', hace=timedelta(hours=5), imagenes=3, reacciones=['sin_resolver', 'sin_resolver'],
         descripcion='Bache de casi medio metro en el carril derecho, ya dañó llantas de varios autos.'),
    dict(tipo='Choque', titulo='Choque menor sin lesionados', direccion='Periférico Camino Real',
         latitud='31.690000', longitud='-106.500000', gravedad='leve', hace=timedelta(days=1, hours=3),
         imagenes=1, reacciones=['sin_resolver'],
         descripcion='Dos autos chocaron por alcance; ocupan el carril izquierdo mientras llega tránsito.'),
    dict(tipo='Tráfico', titulo='Tráfico sin movimiento', direccion='Av. Insurgentes',
         latitud='31.729000', longitud='-106.452000', gravedad='moderado', hace=timedelta(days=2),
         imagenes=0, reacciones=['sin_resolver', 'resuelto'],
         descripcion='Fila de más de un kilómetro en dirección al centro por obras en la avenida.'),
    dict(tipo='Obstrucción', titulo='Obstrucción por obra', direccion='Parque El Chamizal',
         latitud='31.764000', longitud='-106.479000', gravedad='leve', hace=timedelta(days=3, hours=6),
         imagenes=1, reacciones=[],
         descripcion='Material de construcción sobre el acotamiento, obliga a invadir el otro carril.'),
    dict(tipo='Otro', tipo_otro='Semáforo descompuesto', titulo='Semáforo apagado',
         direccion='Av. Vicente Guerrero', latitud='31.730000', longitud='-106.515000', gravedad='grave',
         hace=timedelta(days=5), imagenes=0, reacciones=['sin_resolver', 'sin_resolver', 'sin_resolver'],
         descripcion='El semáforo del cruce lleva apagado desde la mañana y no hay agente de tránsito.'),
    dict(tipo='Bache', titulo='Bache tapado recientemente', direccion='Calle Rancho Anapra',
         latitud='31.779000', longitud='-106.560000', gravedad='leve', hace=timedelta(days=12),
         imagenes=2, reacciones=['resuelto', 'resuelto'], resuelto=True,
         descripcion='Había un bache grande frente a la escuela; el municipio ya lo reparó.'),
    dict(tipo='Choque', titulo='Choque en Av. de las Torres', direccion='Av. de las Torres',
         latitud='31.650000', longitud='-106.440000', gravedad='moderado', hace=timedelta(days=20),
         imagenes=1, reacciones=['sin_resolver'],
         descripcion='Choque entre una camioneta y un auto compacto en el cruce con la lateral.'),
    # --- reportes de vecinos (el usuario demo puede reaccionar y denunciar) ---
    dict(autor=0, tipo='Bache', titulo='Bache en la lateral del Periférico',
         direccion='Periférico de la Juventud', latitud='31.705000', longitud='-106.395000',
         gravedad='moderado', hace=timedelta(hours=3), imagenes=1, reacciones=['sin_resolver', 'resuelto'],
         descripcion='Bache ancho a la salida de la lateral; de noche casi no se ve.'),
    dict(autor=1, tipo='Obstrucción', titulo='Camión descompuesto en el carril central',
         direccion='Av. Ejército Nacional', latitud='31.718000', longitud='-106.470000',
         gravedad='grave', hace=timedelta(hours=8), imagenes=0, reacciones=['sin_resolver'],
         reaccion_demo='sin_resolver',
         denuncia_demo='Pasé por ahí hace una hora y no había ningún camión en la avenida.',
         descripcion='Un camión de carga quedó detenido en el carril central y no hay señalización.'),
    dict(autor=2, tipo='Inundación', titulo='Encharcamiento frente al mercado',
         direccion='Calle Mariscal', latitud='31.745000', longitud='-106.488000', gravedad='leve',
         hace=timedelta(days=6), imagenes=1, reacciones=['resuelto', 'resuelto'], resuelto=True,
         descripcion='Se juntaba el agua frente al mercado; ya limpiaron la alcantarilla.'),
]

COLORES = ['#3B82F6', '#F59E0B', '#10B981']


def imagen_png(texto, color):
    """Genera en memoria un PNG pequeño de un color con un texto."""
    img = PilImage.new('RGB', (480, 320), color)
    ImageDraw.Draw(img).text((20, 20), texto, fill='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def obtener_usuario(email, nombre):
    usuario = Usuario.objects.filter(email=email).first()
    if usuario is None:
        # create_user guarda la contraseña con hash.
        usuario = Usuario.objects.create_user(
            email, PASSWORD_DEMO, nombre=nombre, privacidad_aceptada_en=timezone.now()
        )
    return usuario


class Command(BaseCommand):
    help = 'Carga usuarios y reportes de ejemplo (solo con DEBUG=True).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Borra los reportes demo y los vuelve a crear.')

    @transaction.atomic  # si algo falla, no queda nada a medias
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_demo solo puede ejecutarse con DEBUG=True.')

        autor = obtener_usuario(*AUTOR)
        vecinos = [obtener_usuario(*datos) for datos in VECINOS]

        if options['reset']:
            # Solo reportes demo: el título debe estar en la lista Y el autor ser un
            # usuario sembrado. Nunca se borra por título solo (un usuario real
            # podría haber escrito "Semáforo apagado").
            demo = Reporte.objects.filter(
                usuario__in=[autor, *vecinos], titulo__in=[datos['titulo'] for datos in REPORTES]
            )
            borrados, _ = demo.delete()
            self.stdout.write(f'Se borraron {borrados} registros demo.')

        creados = 0
        for datos in REPORTES:
            duenio = vecinos[datos['autor']] if 'autor' in datos else autor
            if Reporte.objects.filter(usuario=duenio, titulo=datos['titulo']).exists():
                continue
            self.crear_reporte(duenio, autor, vecinos, datos)
            creados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {creados} reportes nuevos ({len(REPORTES) - creados} ya existían). '
            f'Usuario demo: {AUTOR[0]} / {PASSWORD_DEMO}'
        ))

    def crear_reporte(self, duenio, demo, vecinos, datos):
        ahora = timezone.now()
        momento = ahora - datos['hace']
        reporte = Reporte.objects.create(
            usuario=duenio,
            tipo=TipoIncidente.objects.get(nombre=datos['tipo']),
            tipo_otro=datos.get('tipo_otro', ''),
            titulo=datos['titulo'],
            descripcion=datos['descripcion'],
            gravedad=datos['gravedad'],
            direccion=datos['direccion'],
            latitud=datos['latitud'],
            longitud=datos['longitud'],
            fecha_incidente=momento,
        )
        # creado_en es auto_now_add (siempre "ahora"); lo ajustamos con update() para fechas variadas.
        creado_en = min(momento + timedelta(minutes=5), ahora)
        Reporte.objects.filter(pk=reporte.pk).update(creado_en=creado_en, actualizado_en=creado_en)

        total = datos['imagenes']
        for i in range(total):
            Imagen.objects.create(
                reporte=reporte,
                contenido=imagen_png(f'SARV demo - {datos["tipo"]} {i + 1}/{total}', COLORES[i]),
                tipo_mime=Imagen.Mime.PNG,
            )

        # El autor no reacciona a su propio reporte (su "Resuelto" lo resuelve).
        otros = [vecino for vecino in vecinos if vecino != duenio]
        reacciones = list(zip(otros, datos['reacciones']))
        if 'reaccion_demo' in datos:
            reacciones.append((demo, datos['reaccion_demo']))
        for i, (usuario, tipo) in enumerate(reacciones):
            reaccion = Reaccion.objects.create(reporte=reporte, usuario=usuario, tipo=tipo)
            creada_en = min(creado_en + timedelta(minutes=20 * (i + 1)), ahora)
            Reaccion.objects.filter(pk=reaccion.pk).update(creada_en=creada_en)

        if 'denuncia_demo' in datos:
            Denuncia.objects.create(reporte=reporte, usuario=demo, motivo=datos['denuncia_demo'])

        if datos.get('resuelto'):
            reporte.resolver()
            resuelto_en = min(creado_en + timedelta(days=2), ahora)
            Reporte.objects.filter(pk=reporte.pk).update(resuelto_en=resuelto_en, actualizado_en=resuelto_en)
