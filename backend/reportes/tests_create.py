"""Pruebas de POST /api/reportes/ (creación con imágenes).

Aún no hay login: force_authenticate simula un usuario con sesión.
Las imágenes se generan en memoria con Pillow.
"""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.urls import reverse
from django.utils import timezone
from PIL import ExifTags, Image
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from usuarios.models import Usuario

from .models import Imagen, Reporte, TipoIncidente
from .zonas import CENTRO_LAT, CENTRO_LNG

URL = reverse('reporte-lista')


def imagen(formato='JPEG', tamano=(800, 600), nombre=None, con_gps=False, modo='RGB'):
    """Archivo de imagen en memoria, listo para subir."""
    img = Image.new(modo, tamano, 'red' if modo == 'RGB' else 1)
    buffer = BytesIO()
    extra = {}
    if con_gps:
        exif = Image.Exif()
        exif[ExifTags.Base.Model] = 'Celular de prueba'
        exif[ExifTags.Base.Orientation] = 6   # "girar 90°": exif_transpose debe aplicarlo
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        gps[ExifTags.GPS.GPSLatitudeRef] = 'N'
        gps[ExifTags.GPS.GPSLatitude] = (31.0, 44.0, 20.0)
        gps[ExifTags.GPS.GPSLongitudeRef] = 'W'
        gps[ExifTags.GPS.GPSLongitude] = (106.0, 29.0, 10.0)
        extra['exif'] = exif
    img.save(buffer, format=formato, **extra)
    extension = {'JPEG': 'jpg', 'PNG': 'png', 'GIF': 'gif', 'WEBP': 'webp'}[formato]
    return SimpleUploadedFile(nombre or f'foto.{extension}', buffer.getvalue(), content_type=f'image/{extension}')


def gps_de(contenido):
    return Image.open(BytesIO(contenido)).getexif().get_ifd(ExifTags.IFD.GPSInfo)


class BaseCreacion(APITestCase):
    def setUp(self):
        cache.clear()   # los contadores del throttle viven en la caché: cada prueba empieza en cero
        self.usuario = Usuario.objects.create_user('ana@correo.mx', 'secreto1', nombre='Ana')
        self.otro = Usuario.objects.create_user('otro@correo.mx', 'secreto2', nombre='Otro')
        self.bache = TipoIncidente.objects.get(nombre='Bache')
        self.tipo_otro = TipoIncidente.objects.get(nombre='Otro')
        self.client.force_authenticate(self.usuario)

    def datos(self, **extra):
        datos = {
            'tipo': self.bache.id,
            'titulo': 'Bache profundo',
            'descripcion': 'Bache profundo en el carril derecho',
            'gravedad': 'moderado',
            'latitud': f'{CENTRO_LAT + 0.05:.6f}',     # zona norte
            'longitud': f'{CENTRO_LNG:.6f}',
            'direccion': 'Av. Tecnológico',
            'fecha_incidente': (timezone.now() - timedelta(hours=1)).isoformat(),
        }
        datos.update(extra)
        return datos

    def post(self, **extra):
        return self.client.post(URL, self.datos(**extra), format='multipart')

    def assertError400(self, response, campo):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(campo, response.data)
        self.assertEqual(Reporte.objects.count(), 0)


class CreacionExitosaTests(BaseCreacion):
    def test_crea_con_usuario_zona_e_imagenes(self):
        response = self.post(imagenes=[imagen(), imagen('PNG')])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        reporte = Reporte.objects.get()
        self.assertEqual(reporte.usuario, self.usuario)
        self.assertEqual(reporte.zona, 'norte')
        self.assertEqual(reporte.estado, 'sin_resolver')
        self.assertEqual(list(reporte.imagenes.values_list('tipo_mime', flat=True)), ['image/jpeg', 'image/png'])
        # Responde como el detalle
        self.assertEqual(response.data['id'], reporte.id)
        self.assertTrue(response.data['es_autor'])
        self.assertEqual(len(response.data['imagenes']), 2)
        self.assertEqual(response.data['seguimiento'][0]['autor'], 'Ana')
        self.assertNotIn('contenido', str(response.data))

    def test_sin_imagenes_tambien_funciona(self):
        self.assertEqual(self.post().status_code, status.HTTP_201_CREATED)

    def test_quita_exif_y_gps_y_conserva_la_orientacion(self):
        original = imagen(con_gps=True, tamano=(800, 600))
        self.assertTrue(gps_de(original.read()))   # la foto original SÍ trae GPS
        original.seek(0)
        self.assertEqual(self.post(imagenes=[original]).status_code, status.HTTP_201_CREATED)

        guardada = bytes(Imagen.objects.get().contenido)
        self.assertNotIn(b'Exif', guardada)
        self.assertEqual(len(Image.open(BytesIO(guardada)).getexif()), 0)
        self.assertFalse(gps_de(guardada))
        # Orientation=6 giraba la foto: 800x600 queda vertical (600x800)
        self.assertEqual(Image.open(BytesIO(guardada)).size, (600, 800))

    def test_reduce_el_lado_mayor_a_1600(self):
        self.post(imagenes=[imagen(tamano=(2400, 1200))])
        guardada = Image.open(BytesIO(bytes(Imagen.objects.get().contenido)))
        self.assertEqual(guardada.size, (1600, 800))

    def test_formato_real_y_no_la_extension(self):
        # Un PNG real con nombre .jpg se guarda como PNG
        self.post(imagenes=[imagen('PNG', nombre='engano.jpg')])
        self.assertEqual(Imagen.objects.get().tipo_mime, 'image/png')

    def test_redondea_coordenadas_a_6_decimales(self):
        response = self.post(latitud='31.73932847261', longitud='-106.48701234567')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        reporte = Reporte.objects.get()
        self.assertEqual(reporte.latitud, Decimal('31.739328'))
        self.assertEqual(reporte.longitud, Decimal('-106.487012'))

    def test_ignora_usuario_y_estado_enviados(self):
        self.post(usuario=self.otro.id, estado='resuelto', zona='sur')
        reporte = Reporte.objects.get()
        self.assertEqual(reporte.usuario, self.usuario)
        self.assertEqual(reporte.estado, 'sin_resolver')
        self.assertEqual(reporte.zona, 'norte')

    def test_tipo_otro_con_descripcion(self):
        response = self.post(tipo=self.tipo_otro.id, tipo_otro='  Semáforo descompuesto  ')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['tipo_etiqueta'], 'Semáforo descompuesto')

    def test_fecha_con_minutos_de_adelanto_se_acepta(self):
        fecha = (timezone.now() + timedelta(minutes=2)).isoformat()
        self.assertEqual(self.post(fecha_incidente=fecha).status_code, status.HTTP_201_CREATED)


class PermisosTests(BaseCreacion):
    def test_anonimo_es_rechazado(self):
        self.client.force_authenticate(None)
        response = self.post()
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertEqual(Reporte.objects.count(), 0)

    def test_el_listado_sigue_siendo_publico(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_200_OK)


class ValidacionTests(BaseCreacion):
    def test_tipo_otro_sin_descripcion(self):
        self.assertError400(self.post(tipo=self.tipo_otro.id, tipo_otro='   '), 'tipo_otro')

    def test_coordenadas_fuera_de_juarez(self):
        self.assertError400(self.post(latitud='31.900000'), 'latitud')
        self.assertError400(self.post(longitud='-106.07123456789'), 'longitud')

    def test_descripcion_corta_o_larga(self):
        self.assertError400(self.post(descripcion='corta'), 'descripcion')
        self.assertError400(self.post(descripcion='x' * 501), 'descripcion')

    def test_fecha_futura(self):
        fecha = (timezone.now() + timedelta(hours=1)).isoformat()
        self.assertError400(self.post(fecha_incidente=fecha), 'fecha_incidente')

    def test_mas_de_3_imagenes(self):
        self.assertError400(self.post(imagenes=[imagen() for _ in range(4)]), 'imagenes')

    def test_imagen_de_mas_de_5_mb(self):
        # Ni siquiera es una imagen válida: prueba que el tamaño se revisa antes de abrirla.
        grande = SimpleUploadedFile('grande.jpg', b'0' * (5 * 1024 * 1024 + 1), content_type='image/jpeg')
        response = self.post(imagenes=[grande])
        self.assertError400(response, 'imagenes')
        self.assertIn('5 MB', str(response.data['imagenes']))

    def test_gif_y_webp_se_rechazan(self):
        self.assertError400(self.post(imagenes=[imagen('GIF')]), 'imagenes')
        self.assertError400(self.post(imagenes=[imagen('WEBP')]), 'imagenes')

    def test_texto_renombrado_como_png(self):
        falso = SimpleUploadedFile('foto.png', b'esto es texto, no una imagen', content_type='image/png')
        self.assertError400(self.post(imagenes=[falso]), 'imagenes')

    def test_archivo_corrupto(self):
        png = imagen('PNG').read()
        truncado = SimpleUploadedFile('rota.png', png[: len(png) // 2], content_type='image/png')
        self.assertError400(self.post(imagenes=[truncado]), 'imagenes')

    def test_demasiados_pixeles(self):
        # 7000x6000 = 42 MP en blanco y negro: el archivo pesa poco, pero se rechaza antes de decodificar
        enorme = imagen('PNG', tamano=(7000, 6000), modo='1')
        self.assertError400(self.post(imagenes=[enorme]), 'imagenes')

    def test_segunda_imagen_invalida_no_crea_nada(self):
        falso = SimpleUploadedFile('2.png', b'no soy imagen', content_type='image/png')
        response = self.post(imagenes=[imagen(), falso])
        self.assertError400(response, 'imagenes')
        self.assertIn('imagen 2', str(response.data['imagenes']))
        self.assertEqual(Imagen.objects.count(), 0)


class TransaccionTests(BaseCreacion):
    def test_fallo_al_guardar_la_segunda_imagen_no_deja_reporte(self):
        """Simula que la base de datos falla al guardar la 2.ª imagen: transaction.atomic deshace todo."""
        guardar_real = Imagen.objects.create
        llamadas = []

        def falla_en_la_segunda(**kwargs):
            llamadas.append(kwargs)
            if len(llamadas) == 2:
                raise DatabaseError('falla simulada')
            return guardar_real(**kwargs)

        self.client.raise_request_exception = False   # recibir el 500 en vez de la excepción
        with mock.patch('reportes.serializers.Imagen.objects.create', side_effect=falla_en_la_segunda):
            response = self.post(imagenes=[imagen(), imagen()])
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(len(llamadas), 2)
        self.assertEqual(Reporte.objects.count(), 0)
        self.assertEqual(Imagen.objects.count(), 0)


class LimiteDeReportesTests(BaseCreacion):
    """Throttle del POST. Se baja la tasa a 2/hora para no crear 20 reportes;
    como la ventana es de una hora, la prueba no depende del reloj real."""

    def test_post_limitado_por_usuario(self):
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'reportes_crear': '2/hour'}):
            self.assertEqual(self.post().status_code, status.HTTP_201_CREATED)
            self.assertEqual(self.post().status_code, status.HTTP_201_CREATED)
            response = self.post()
            self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            self.assertIn('demasiados reportes', response.data['detail'])
            self.assertEqual(Reporte.objects.count(), 2)

            # Otro usuario tiene su propio contador
            self.client.force_authenticate(self.otro)
            self.assertEqual(self.post().status_code, status.HTTP_201_CREATED)

    def test_intentos_invalidos_tambien_cuentan(self):
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'reportes_crear': '2/hour'}):
            self.post(descripcion='corta')
            self.post(descripcion='corta')
            self.assertEqual(self.post().status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_el_get_no_tiene_limite(self):
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'reportes_crear': '2/hour'}):
            for _ in range(5):
                self.assertEqual(self.client.get(URL).status_code, status.HTTP_200_OK)
