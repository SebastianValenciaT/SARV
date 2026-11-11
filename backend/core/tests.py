"""Pruebas funcionales de SARV, organizadas por módulo.
"""
from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from reportes.models import Denuncia, Imagen, Reaccion, Reporte, TipoIncidente
from reportes.zonas import CENTRO_LAT, CENTRO_LNG
from usuarios.models import Usuario

PASSWORD = 'Calle-Segura-2026'

URL_REGISTRO = reverse('api_registro')
URL_LOGIN = reverse('api_login')
URL_REFRESH = reverse('api_token_refresh')
URL_ME = reverse('api_me')
URL_TIPOS = reverse('tipos')
URL_REPORTES = reverse('reporte-lista')
URL_MAPA = reverse('mapa-reportes')
URL_MIS_REPORTES = reverse('mis-reportes')

# Coordenadas de prueba dentro de Ciudad Juárez (zona calculada por reportes/zonas.py)
COORD_CENTRO = (CENTRO_LAT, CENTRO_LNG)
COORD_NORTE = (CENTRO_LAT + 0.05, CENTRO_LNG)
COORD_SUR = (CENTRO_LAT - 0.05, CENTRO_LNG)
COORD_EL_PASO = (31.90, -106.40)   # fuera de Juárez (EE. UU.)


def url_detalle(pk):
    return reverse('reporte-detalle', args=[pk])


def url_reaccion(pk):
    return reverse('reporte-reaccion', args=[pk])


def url_denuncia(pk):
    return reverse('reporte-denuncias', args=[pk])


def foto(formato='JPEG', nombre=None):
    """Imagen pequeña generada en memoria, como la que sube el formulario."""
    buffer = BytesIO()
    Image.new('RGB', (640, 480), 'red').save(buffer, format=formato)
    extension = {'JPEG': 'jpg', 'PNG': 'png', 'GIF': 'gif'}[formato]
    return SimpleUploadedFile(
        nombre or f'foto.{extension}', buffer.getvalue(), content_type=f'image/{extension}'
    )


# MD5 solo acelera las pruebas (el hash real es lento a propósito); no cambia el comportamiento.
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class BaseFuncional(APITestCase):
    """Datos y acciones comunes: usuarios, tipos, reportes y sesión con JWT."""

    def setUp(self):
        cache.clear()   # los límites de peticiones (throttle) viven en la caché
        self.addCleanup(cache.clear)
        self.ana = Usuario.objects.create_user('ana@correo.mx', PASSWORD, nombre='Ana López')
        self.luis = Usuario.objects.create_user('luis@correo.mx', PASSWORD, nombre='Luis Pérez')
        self.bache = TipoIncidente.objects.get(nombre='Bache')
        self.choque = TipoIncidente.objects.get(nombre='Choque')
        self.trafico = TipoIncidente.objects.get(nombre='Tráfico')
        self.tipo_otro = TipoIncidente.objects.get(nombre='Otro')

    # ---------- sesión ----------

    def iniciar_sesion(self, usuario):
        """Login real en /api/login/ y token en el encabezado, como hace el frontend."""
        response = self.client.post(
            URL_LOGIN, {'email': usuario.email, 'password': PASSWORD}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data

    def cerrar_sesion(self):
        self.client.credentials()

    # ---------- datos ----------

    def crear_reporte(self, usuario=None, tipo=None, hace=timedelta(hours=1), coord=COORD_NORTE,
                      titulo='Bache profundo', direccion='Av. Tecnológico', resuelto=False):
        """Reporte guardado directo en la base. `hace` fija fecha_incidente y creado_en."""
        ahora = timezone.now()
        reporte = Reporte.objects.create(
            usuario=usuario or self.ana, tipo=tipo or self.bache, titulo=titulo,
            descripcion='Bache profundo en el carril derecho', gravedad='moderado',
            direccion=direccion, latitud=f'{coord[0]:.6f}', longitud=f'{coord[1]:.6f}',
            fecha_incidente=ahora - hace,
        )
        # creado_en es auto_now_add: se ajusta con update() para simular reportes viejos
        Reporte.objects.filter(pk=reporte.pk).update(creado_en=ahora - hace)
        if resuelto:
            reporte.resolver()
        reporte.refresh_from_db()
        return reporte

    def datos_formulario(self, **cambios):
        """Lo que manda el formulario de Crear reporte (multipart)."""
        datos = {
            'tipo': self.bache.id,
            'titulo': 'Bache frente a la escuela',
            'descripcion': 'Bache de medio metro en el carril derecho, frente a la escuela.',
            'gravedad': 'moderado',
            'latitud': f'{COORD_NORTE[0]:.6f}',
            'longitud': f'{COORD_NORTE[1]:.6f}',
            'direccion': 'Av. Tecnológico 1340',
            'fecha_incidente': (timezone.now() - timedelta(minutes=30)).isoformat(),
        }
        datos.update(cambios)
        return datos

    def publicar(self, **cambios):
        return self.client.post(URL_REPORTES, self.datos_formulario(**cambios), format='multipart')

    def ids(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        datos = response.data['results'] if isinstance(response.data, dict) else response.data
        return [r['id'] for r in datos]


# =====================================================================
# Módulo General (todas las vistas)
# =====================================================================

class GeneralTests(BaseFuncional):
    def test_CP_GEN_01_acciones_protegidas_sin_sesion_responden_401(self):
        reporte = self.crear_reporte()
        peticiones = [
            ('post', URL_REPORTES, self.datos_formulario()),
            ('get', URL_MIS_REPORTES, None),
            ('get', URL_ME, None),
            ('patch', url_detalle(reporte.pk), {'titulo': 'Otro'}),
            ('delete', url_detalle(reporte.pk), None),
            ('put', url_reaccion(reporte.pk), {'tipo': 'resuelto'}),
            ('post', url_denuncia(reporte.pk), {'motivo': 'Parece un reporte falso.'}),
        ]
        for metodo, url, datos in peticiones:
            with self.subTest(metodo=metodo, url=url):
                response = getattr(self.client, metodo)(url, datos, format='json')
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Reporte.objects.filter(pk=reporte.pk).exists())   # nada cambió

    def test_CP_GEN_02_consultas_publicas_sin_sesion(self):
        reporte = self.crear_reporte()
        for url in (URL_TIPOS, URL_REPORTES, URL_MAPA, url_detalle(reporte.pk)):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

    def test_CP_GEN_03_token_alterado_o_vencido_se_rechaza(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer token-alterado')
        self.assertEqual(self.client.get(URL_ME).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_CP_GEN_04_sesion_activa_identifica_al_usuario(self):
        self.iniciar_sesion(self.ana)
        response = self.client.get(URL_ME)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'ana@correo.mx')
        self.assertEqual(response.data['nombre'], 'Ana López')


# =====================================================================
# Módulo Inicio
# =====================================================================

class InicioTests(BaseFuncional):
    def test_CP_INI_01_reportes_recientes_ultimos_7_dias_del_mas_nuevo(self):
        viejo = self.crear_reporte(hace=timedelta(days=10), titulo='Viejo')
        anterior = self.crear_reporte(hace=timedelta(days=2), titulo='Anterior')
        nuevo = self.crear_reporte(hace=timedelta(hours=1), titulo='Nuevo')
        ids = self.ids(self.client.get(URL_REPORTES, {'fecha': '7d'}))   # misma consulta que el carrusel
        self.assertEqual(ids, [nuevo.id, anterior.id])
        self.assertNotIn(viejo.id, ids)

    def test_CP_INI_02_mapa_de_inicio_muestra_solo_activos(self):
        activo = self.crear_reporte(titulo='Activo')
        resuelto = self.crear_reporte(titulo='Resuelto', resuelto=True)
        expirado = self.crear_reporte(tipo=self.choque, hace=timedelta(hours=25), titulo='Expirado')
        ids = self.ids(self.client.get(URL_MAPA))
        self.assertIn(activo.id, ids)
        self.assertNotIn(resuelto.id, ids)
        self.assertNotIn(expirado.id, ids)

    def test_CP_INI_03_sin_reportes_recientes(self):
        response = self.client.get(URL_REPORTES, {'fecha': '7d'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)   # el carrusel muestra «Aún no hay reportes recientes.»

    def test_CP_INI_04_catalogo_de_tipos_de_incidente(self):
        response = self.client.get(URL_TIPOS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [t['nombre'] for t in response.data],
            ['Bache', 'Choque', 'Inundación', 'Tráfico', 'Obstrucción', 'Otro'],
        )


# =====================================================================
# Módulo Registrarse
# =====================================================================

class RegistroTests(BaseFuncional):
    def registrar(self, **cambios):
        datos = {
            'nombre': 'María', 'apellido': 'García', 'email': 'maria@correo.mx',
            'password': PASSWORD, 'aceptaPrivacidad': True,
        }
        datos.update(cambios)
        return self.client.post(URL_REGISTRO, datos, format='json')

    def test_CP_REG_01_registro_exitoso_y_puede_iniciar_sesion(self):
        response = self.registrar()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertNotIn('password', response.data)
        usuario = Usuario.objects.get(email='maria@correo.mx')
        self.assertEqual(usuario.nombre, 'María García')            # nombre + apellido
        self.assertNotEqual(usuario.password, PASSWORD)              # guardada con hash
        self.assertIsNotNone(usuario.privacidad_aceptada_en)         # constancia del aviso
        login = self.client.post(URL_LOGIN, {'email': 'maria@correo.mx', 'password': PASSWORD}, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_CP_REG_02_correo_ya_registrado(self):
        response = self.registrar(email='ANA@correo.mx')   # ana ya existe; no distingue mayúsculas
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['email'], ['Ya existe una cuenta con este correo electrónico.'])
        self.assertEqual(Usuario.objects.filter(email__iexact='ana@correo.mx').count(), 1)

    def test_CP_REG_03_contrasena_menor_a_8_caracteres(self):
        response = self.registrar(password='Ab-12')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertFalse(Usuario.objects.filter(email='maria@correo.mx').exists())

    def test_CP_REG_04_contrasena_comun_o_solo_numeros(self):
        for password in ('12345678', 'password'):
            with self.subTest(password=password):
                response = self.registrar(password=password)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('password', response.data)

    def test_CP_REG_05_sin_aceptar_aviso_de_privacidad(self):
        response = self.registrar(aceptaPrivacidad=False)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['aceptaPrivacidad'], ['Debes aceptar el aviso de privacidad.'])
        self.assertFalse(Usuario.objects.filter(email='maria@correo.mx').exists())

    def test_CP_REG_06_campos_obligatorios_vacios(self):
        response = self.client.post(URL_REGISTRO, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for campo in ('nombre', 'apellido', 'email', 'password', 'aceptaPrivacidad'):
            self.assertIn(campo, response.data)

    def test_CP_REG_07_correo_con_formato_invalido(self):
        response = self.registrar(email='maria-correo.mx')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_CP_REG_08_correo_se_guarda_en_minusculas(self):
        self.assertEqual(self.registrar(email='Maria@Correo.MX').status_code, status.HTTP_201_CREATED)
        self.assertTrue(Usuario.objects.filter(email='maria@correo.mx').exists())


# =====================================================================
# Módulo Iniciar sesión
# =====================================================================

class LoginTests(BaseFuncional):
    def login(self, email='ana@correo.mx', password=PASSWORD):
        return self.client.post(URL_LOGIN, {'email': email, 'password': password}, format='json')

    def test_CP_LOG_01_credenciales_correctas(self):
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_CP_LOG_02_contrasena_incorrecta(self):
        response = self.login(password='otra-cosa-123')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)

    def test_CP_LOG_03_correo_no_registrado(self):
        response = self.login(email='nadie@correo.mx')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_CP_LOG_04_correo_con_mayusculas_y_espacios(self):
        self.assertEqual(self.login(email='  Ana@Correo.MX ').status_code, status.HTTP_200_OK)

    def test_CP_LOG_05_campos_vacios(self):
        response = self.login(email='', password='')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_CP_LOG_06_la_sesion_se_renueva_con_el_refresh(self):
        refresh = self.login().data['refresh']
        response = self.client.post(URL_REFRESH, {'refresh': refresh}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(self.client.get(URL_ME).status_code, status.HTTP_200_OK)

    def test_CP_LOG_07_limite_de_intentos(self):
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'auth_login': '3/min'}):
            for _ in range(3):
                self.login(password='mala-123456')
            response = self.login()   # aunque ahora sea correcta
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Demasiados intentos de inicio de sesión', str(response.data['detail']))


# =====================================================================
# Módulo Crear reporte
# =====================================================================

class CrearReporteTests(BaseFuncional):
    def setUp(self):
        super().setUp()
        self.iniciar_sesion(self.ana)

    def assertErrorEn(self, response, campo, texto=None):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(campo, response.data)
        if texto:
            self.assertIn(texto, str(response.data[campo]))
        self.assertFalse(Reporte.objects.exists())   # no se guarda nada

    def test_CP_CRE_01_publicar_reporte_completo_sin_fotos(self):
        response = self.publicar()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['estado'], 'sin_resolver')
        self.assertEqual(response.data['zona'], 'norte')
        self.assertTrue(response.data['es_autor'])
        reporte = Reporte.objects.get(pk=response.data['id'])
        self.assertEqual(reporte.usuario, self.ana)
        # Queda visible en Mis reportes, en la lista y en el mapa
        self.assertIn(reporte.id, self.ids(self.client.get(URL_MIS_REPORTES)))
        self.assertIn(reporte.id, self.ids(self.client.get(URL_REPORTES)))
        self.assertIn(reporte.id, self.ids(self.client.get(URL_MAPA)))

    def test_CP_CRE_02_publicar_con_tres_fotos_jpg_y_png(self):
        response = self.publicar(imagenes=[foto('JPEG'), foto('PNG'), foto('JPEG')])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['total_imagenes'], 3)
        imagen = self.client.get(response.data['imagenes'][0]['url'])
        self.assertEqual(imagen.status_code, status.HTTP_200_OK)
        self.assertEqual(imagen['Content-Type'], 'image/jpeg')

    def test_CP_CRE_03_mas_de_tres_fotos(self):
        response = self.publicar(imagenes=[foto() for _ in range(4)])
        self.assertErrorEn(response, 'imagenes')

    def test_CP_CRE_04_foto_que_no_es_jpg_ni_png(self):
        response = self.publicar(imagenes=[foto('GIF')])
        self.assertErrorEn(response, 'imagenes', 'debe ser JPG o PNG')

    def test_CP_CRE_05_foto_de_mas_de_5_mb(self):
        pesada = SimpleUploadedFile('grande.jpg', b'0' * (5 * 1024 * 1024 + 1), content_type='image/jpeg')
        response = self.publicar(imagenes=[pesada])
        self.assertErrorEn(response, 'imagenes', 'pesa más de 5 MB')

    def test_CP_CRE_06_descripcion_fuera_de_10_a_500_caracteres(self):
        for descripcion in ('Corta', 'x' * 501):
            with self.subTest(largo=len(descripcion)):
                self.assertErrorEn(self.publicar(descripcion=descripcion), 'descripcion')

    def test_CP_CRE_07_campos_obligatorios_vacios(self):
        response = self.client.post(URL_REPORTES, {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for campo in ('tipo', 'titulo', 'descripcion', 'gravedad', 'latitud', 'longitud', 'fecha_incidente'):
            self.assertIn(campo, response.data)

    def test_CP_CRE_08_tipo_otro_requiere_describir_el_incidente(self):
        self.assertErrorEn(self.publicar(tipo=self.tipo_otro.id), 'tipo_otro', 'Describe el tipo de incidente.')
        response = self.publicar(tipo=self.tipo_otro.id, tipo_otro='Semáforo descompuesto')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['tipo_etiqueta'], 'Semáforo descompuesto')

    def test_CP_CRE_09_ubicacion_fuera_de_ciudad_juarez(self):
        response = self.publicar(latitud=f'{COORD_EL_PASO[0]:.6f}', longitud=f'{COORD_EL_PASO[1]:.6f}')
        self.assertErrorEn(response, 'latitud', 'dentro de Ciudad Juárez')

    def test_CP_CRE_10_fecha_del_incidente_en_el_futuro(self):
        futura = (timezone.now() + timedelta(hours=2)).isoformat()
        self.assertErrorEn(self.publicar(fecha_incidente=futura), 'fecha_incidente', 'no puede estar en el futuro')

    def test_CP_CRE_11_gravedad_invalida(self):
        self.assertErrorEn(self.publicar(gravedad='urgente'), 'gravedad')

    def test_CP_CRE_12_el_servidor_asigna_autor_y_estado(self):
        response = self.publicar(usuario=self.luis.id, estado='resuelto')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        reporte = Reporte.objects.get(pk=response.data['id'])
        self.assertEqual(reporte.usuario, self.ana)
        self.assertEqual(reporte.estado, 'sin_resolver')

    def test_CP_CRE_13_coordenadas_del_gps_con_muchos_decimales(self):
        response = self.publicar(latitud='31.78850123456789', longitud='-106.48700987654321')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertAlmostEqual(response.data['latitud'], 31.788501, places=6)

    def test_CP_CRE_14_duracion_por_tipo_de_incidente(self):
        duracion = {t['nombre']: t['duracion_horas'] for t in self.client.get(URL_TIPOS).data}
        for nombre in ('Choque', 'Tráfico', 'Inundación'):
            self.assertEqual(duracion[nombre], 24)      # «se mostrará durante 24 horas»
        for nombre in ('Bache', 'Obstrucción', 'Otro'):
            self.assertIsNone(duracion[nombre])         # sin límite

    def test_CP_CRE_15_sin_sesion_no_se_puede_publicar(self):
        self.cerrar_sesion()
        self.assertEqual(self.publicar().status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Reporte.objects.exists())


# =====================================================================
# Módulo Mapa / Reportes (vista de mapa y vista de lista)
# =====================================================================

class MapaYListaTests(BaseFuncional):
    def test_CP_MAP_01_lista_publica_paginada_del_mas_reciente(self):
        for i in range(22):
            self.crear_reporte(hace=timedelta(hours=i + 1), titulo=f'Reporte {i}')
        response = self.client.get(URL_REPORTES)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 22)
        self.assertEqual(len(response.data['results']), 20)          # 20 por página
        self.assertEqual(response.data['results'][0]['titulo'], 'Reporte 0')
        self.assertIsNotNone(response.data['next'])
        segunda = self.client.get(response.data['next'])
        self.assertEqual(len(segunda.data['results']), 2)

    def test_CP_MAP_02_filtro_por_tipo_uno_o_varios(self):
        bache = self.crear_reporte(tipo=self.bache)
        choque = self.crear_reporte(tipo=self.choque)
        trafico = self.crear_reporte(tipo=self.trafico)
        self.assertEqual(self.ids(self.client.get(URL_REPORTES, {'tipo': self.bache.id})), [bache.id])
        varios = self.ids(self.client.get(URL_REPORTES, {'tipo': [self.bache.id, self.choque.id]}))
        self.assertCountEqual(varios, [bache.id, choque.id])
        self.assertNotIn(trafico.id, varios)

    def test_CP_MAP_03_filtro_por_zona(self):
        norte = self.crear_reporte(coord=COORD_NORTE)
        sur = self.crear_reporte(coord=COORD_SUR)
        centro = self.crear_reporte(coord=COORD_CENTRO)
        self.assertEqual(self.ids(self.client.get(URL_REPORTES, {'zona': 'sur'})), [sur.id])
        self.assertEqual(self.ids(self.client.get(URL_REPORTES, {'zona': 'centro'})), [centro.id])
        self.assertNotIn(norte.id, self.ids(self.client.get(URL_REPORTES, {'zona': 'sur'})))

    def test_CP_MAP_04_filtro_por_fecha(self):
        ayer = self.crear_reporte(hace=timedelta(days=1, hours=1))
        hace_15 = self.crear_reporte(hace=timedelta(days=15))
        hace_40 = self.crear_reporte(hace=timedelta(days=40))
        self.assertEqual(self.ids(self.client.get(URL_REPORTES, {'fecha': '7d'})), [ayer.id])
        self.assertEqual(self.ids(self.client.get(URL_REPORTES, {'fecha': '30d'})), [ayer.id, hace_15.id])
        self.assertIn(hace_40.id, self.ids(self.client.get(URL_REPORTES)))   # sin filtro salen todos

    def test_CP_MAP_05_busqueda_por_calle_o_titulo(self):
        por_titulo = self.crear_reporte(titulo='Semáforo apagado', direccion='Av. Juárez')
        por_calle = self.crear_reporte(titulo='Bache', direccion='Calle Semáforos 10')
        otro = self.crear_reporte(titulo='Choque', direccion='Av. de las Torres')
        ids = self.ids(self.client.get(URL_REPORTES, {'q': 'semáforo'}))
        self.assertCountEqual(ids, [por_titulo.id, por_calle.id])
        self.assertNotIn(otro.id, ids)

    def test_CP_MAP_06_filtro_con_valor_invalido(self):
        for params in ({'zona': 'marte'}, {'fecha': 'ayer'}, {'tipo': 'bache'}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(URL_REPORTES, params).status_code, status.HTTP_400_BAD_REQUEST)

    def test_CP_MAP_07_mapa_con_un_pin_por_reporte_activo(self):
        activo = self.crear_reporte()
        resuelto = self.crear_reporte(resuelto=True)
        response = self.client.get(URL_MAPA)
        self.assertEqual(self.ids(response), [activo.id])
        self.assertNotIn(resuelto.id, self.ids(response))
        pin = response.data[0]
        self.assertIsInstance(pin['latitud'], float)    # Leaflet necesita números
        for campo in ('id', 'latitud', 'longitud', 'tipo', 'tipo_etiqueta', 'titulo', 'direccion', 'zona'):
            self.assertIn(campo, pin)

    def test_CP_MAP_08_filtro_por_tipo_y_busqueda_en_el_mapa(self):
        bache = self.crear_reporte(tipo=self.bache, titulo='Bache en Tecnológico')
        choque = self.crear_reporte(tipo=self.choque, titulo='Choque en Tecnológico')
        self.assertEqual(self.ids(self.client.get(URL_MAPA, {'tipo': self.choque.id})), [choque.id])
        self.assertEqual(self.ids(self.client.get(URL_MAPA, {'q': 'bache'})), [bache.id])

    def test_CP_MAP_09_reportes_expirados_no_se_muestran(self):
        vigente = self.crear_reporte(tipo=self.choque, hace=timedelta(hours=23))
        expirado = self.crear_reporte(tipo=self.choque, hace=timedelta(hours=25))
        bache_viejo = self.crear_reporte(tipo=self.bache, hace=timedelta(days=20))   # sin límite
        for url in (URL_REPORTES, URL_MAPA):
            with self.subTest(url=url):
                ids = self.ids(self.client.get(url))
                self.assertIn(vigente.id, ids)
                self.assertIn(bache_viejo.id, ids)
                self.assertNotIn(expirado.id, ids)

    def test_CP_MAP_10_reporte_resuelto_sigue_en_la_lista(self):
        resuelto = self.crear_reporte(resuelto=True)
        response = self.client.get(URL_REPORTES)
        self.assertIn(resuelto.id, self.ids(response))
        self.assertEqual(response.data['results'][0]['estado'], 'resuelto')


# =====================================================================
# Detalle de reporte (reacciones y denuncias)
# =====================================================================

class DetalleReporteTests(BaseFuncional):
    def setUp(self):
        super().setUp()
        self.reporte = self.crear_reporte(usuario=self.ana)   # ana es la autora

    def test_CP_DET_01_detalle_publico_completo(self):
        Imagen.objects.create(reporte=self.reporte, contenido=b'x', tipo_mime='image/jpeg')
        response = self.client.get(url_detalle(self.reporte.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for campo in ('titulo', 'descripcion', 'tipo_etiqueta', 'gravedad', 'direccion', 'zona',
                      'estado', 'fecha_incidente', 'creado_en', 'imagenes', 'reacciones', 'seguimiento'):
            self.assertIn(campo, response.data)
        self.assertEqual(len(response.data['imagenes']), 1)
        self.assertFalse(response.data['es_autor'])          # visitante
        self.assertEqual(response.data['seguimiento'][0]['autor'], 'Ana López')

    def test_CP_DET_02_reporte_inexistente(self):
        self.assertEqual(self.client.get(url_detalle(99999)).status_code, status.HTTP_404_NOT_FOUND)

    def test_CP_DET_03_el_autor_ve_que_es_suyo(self):
        self.iniciar_sesion(self.ana)
        self.assertTrue(self.client.get(url_detalle(self.reporte.pk)).data['es_autor'])

    def test_CP_DET_04_confirmar_que_sigue_sin_resolver(self):
        self.iniciar_sesion(self.luis)
        response = self.client.put(url_reaccion(self.reporte.pk), {'tipo': 'sin_resolver'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mi_reaccion'], 'sin_resolver')
        self.assertEqual(response.data['reacciones']['sin_resolver'], 1)
        self.assertEqual(response.data['confirmaciones'], 1)
        self.assertTrue(response.data['seguimiento'][1]['completada'])   # «Confirmado por la comunidad»

    def test_CP_DET_05_cambiar_de_reaccion_no_la_duplica(self):
        self.iniciar_sesion(self.luis)
        self.client.put(url_reaccion(self.reporte.pk), {'tipo': 'sin_resolver'}, format='json')
        response = self.client.put(url_reaccion(self.reporte.pk), {'tipo': 'resuelto'}, format='json')
        self.assertEqual(response.data['reacciones'], {'sin_resolver': 0, 'resuelto': 1})
        self.assertEqual(Reaccion.objects.filter(reporte=self.reporte).count(), 1)
        self.assertEqual(response.data['estado'], 'sin_resolver')   # la reacción de otro no lo resuelve

    def test_CP_DET_06_quitar_mi_reaccion(self):
        self.iniciar_sesion(self.luis)
        self.client.put(url_reaccion(self.reporte.pk), {'tipo': 'sin_resolver'}, format='json')
        response = self.client.delete(url_reaccion(self.reporte.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['mi_reaccion'])
        self.assertEqual(response.data['confirmaciones'], 0)
        self.assertFalse(response.data['seguimiento'][1]['completada'])

    def test_CP_DET_07_el_autor_marca_su_reporte_como_resuelto(self):
        self.iniciar_sesion(self.ana)
        response = self.client.put(url_reaccion(self.reporte.pk), {'tipo': 'resuelto'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], 'resuelto')
        self.assertTrue(response.data['seguimiento'][2]['completada'])
        self.assertEqual(response.data['confirmaciones'], 0)    # no cuenta como confirmación
        self.assertNotIn(self.reporte.id, self.ids(self.client.get(URL_MAPA)))   # sale del mapa

    def test_CP_DET_08_el_autor_no_reacciona_sin_resolver_a_su_reporte(self):
        self.iniciar_sesion(self.ana)
        response = self.client.put(url_reaccion(self.reporte.pk), {'tipo': 'sin_resolver'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Reaccion.objects.exists())
        self.assertEqual(response.data['estado'], 'sin_resolver')

    def test_CP_DET_09_reporte_resuelto_no_admite_reacciones_ni_denuncias(self):
        self.reporte.resolver()
        self.iniciar_sesion(self.luis)
        reaccion = self.client.put(url_reaccion(self.reporte.pk), {'tipo': 'sin_resolver'}, format='json')
        denuncia = self.client.post(url_denuncia(self.reporte.pk), {'motivo': 'Este reporte es falso.'}, format='json')
        for response in (reaccion, denuncia):
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
            self.assertEqual(response.data['detail'], 'Este reporte ya está resuelto y no admite cambios.')

    def test_CP_DET_10_reaccion_con_tipo_invalido(self):
        self.iniciar_sesion(self.luis)
        response = self.client.put(url_reaccion(self.reporte.pk), {'tipo': 'me_gusta'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_CP_DET_11_denunciar_reporte_falso(self):
        self.iniciar_sesion(self.luis)
        response = self.client.post(
            url_denuncia(self.reporte.pk), {'motivo': 'Pasé por ahí y no hay ningún bache.'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['ya_denuncie'])     # el botón cambia a «Denuncia registrada»
        self.assertEqual(Denuncia.objects.count(), 1)
        self.assertIn(self.reporte.id, self.ids(self.client.get(URL_MAPA)))   # solo se registra

    def test_CP_DET_12_motivo_de_denuncia_muy_corto(self):
        self.iniciar_sesion(self.luis)
        response = self.client.post(url_denuncia(self.reporte.pk), {'motivo': '   falso   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motivo', response.data)
        self.assertFalse(Denuncia.objects.exists())

    def test_CP_DET_13_denunciar_dos_veces_el_mismo_reporte(self):
        self.iniciar_sesion(self.luis)
        datos = {'motivo': 'Pasé por ahí y no hay ningún bache.'}
        self.client.post(url_denuncia(self.reporte.pk), datos, format='json')
        response = self.client.post(url_denuncia(self.reporte.pk), datos, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Ya denunciaste este reporte.')
        self.assertEqual(Denuncia.objects.count(), 1)

    def test_CP_DET_14_no_se_puede_denunciar_el_propio_reporte(self):
        self.iniciar_sesion(self.ana)
        response = self.client.post(
            url_denuncia(self.reporte.pk), {'motivo': 'Quiero denunciar mi reporte.'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'No puedes denunciar tu propio reporte.')

    def test_CP_DET_15_reporte_expirado_se_consulta_pero_no_admite_acciones(self):
        expirado = self.crear_reporte(tipo=self.choque, hace=timedelta(hours=25))
        detalle = self.client.get(url_detalle(expirado.pk))
        self.assertEqual(detalle.status_code, status.HTTP_200_OK)
        self.assertEqual(detalle.data['estado'], 'expirado')
        self.iniciar_sesion(self.luis)
        response = self.client.put(url_reaccion(expirado.pk), {'tipo': 'resuelto'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['detail'], 'Este reporte expiró y ya no admite cambios.')


# =====================================================================
# Módulo Mis reportes
# =====================================================================

class MisReportesTests(BaseFuncional):
    def setUp(self):
        super().setUp()
        self.iniciar_sesion(self.ana)

    def editar(self, reporte, datos):
        return self.client.patch(url_detalle(reporte.pk), datos, format='multipart')

    def test_CP_MIS_01_lista_solo_mis_reportes_del_mas_reciente(self):
        viejo = self.crear_reporte(hace=timedelta(days=3), titulo='Viejo')
        nuevo = self.crear_reporte(hace=timedelta(hours=1), titulo='Nuevo')
        ajeno = self.crear_reporte(usuario=self.luis, titulo='De Luis')
        response = self.client.get(URL_MIS_REPORTES)
        self.assertEqual(self.ids(response), [nuevo.id, viejo.id])
        self.assertNotIn(ajeno.id, self.ids(response))
        self.assertTrue(response.data['results'][0]['es_editable'])   # muestra Editar y Eliminar

    def test_CP_MIS_02_resumen_de_mis_reportes(self):
        self.crear_reporte()
        self.crear_reporte()
        self.crear_reporte(resuelto=True)
        self.crear_reporte(tipo=self.choque, hace=timedelta(hours=25))   # expirado
        resumen = self.client.get(URL_MIS_REPORTES).data['resumen']
        self.assertEqual(resumen, {'total': 4, 'activos': 2, 'resueltos': 1, 'expirados': 1})

    def test_CP_MIS_03_usuario_sin_reportes(self):
        self.crear_reporte(usuario=self.luis)
        response = self.client.get(URL_MIS_REPORTES)
        self.assertEqual(response.data['results'], [])
        self.assertEqual(response.data['resumen']['total'], 0)   # la vista muestra «Sin reportes»

    def test_CP_MIS_04_filtrar_por_estado(self):
        activo = self.crear_reporte()
        resuelto = self.crear_reporte(resuelto=True)
        expirado = self.crear_reporte(tipo=self.choque, hace=timedelta(hours=25))
        casos = {'sin_resolver': [activo.id], 'resuelto': [resuelto.id], 'expirado': [expirado.id]}
        for estado, esperado in casos.items():
            with self.subTest(estado=estado):
                response = self.client.get(URL_MIS_REPORTES, {'estado': estado})
                self.assertEqual(self.ids(response), esperado)
                self.assertEqual(response.data['resumen']['total'], 3)   # el resumen no cambia
        self.assertEqual(
            self.client.get(URL_MIS_REPORTES, {'estado': 'pendiente'}).status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_CP_MIS_05_resueltos_y_expirados_son_de_solo_lectura(self):
        self.crear_reporte(resuelto=True)
        self.crear_reporte(tipo=self.choque, hace=timedelta(hours=25))
        for reporte in self.client.get(URL_MIS_REPORTES).data['results']:
            self.assertFalse(reporte['es_editable'])   # solo «Ver detalle →»

    def test_CP_MIS_06_editar_mi_reporte(self):
        reporte = self.crear_reporte()
        fecha_original = reporte.fecha_incidente
        response = self.editar(reporte, {
            'titulo': 'Bache ya muy grande', 'gravedad': 'grave',
            'descripcion': 'El bache creció y ya ocupa todo el carril.',
            'fecha_incidente': (timezone.now() - timedelta(days=5)).isoformat(),   # no se edita
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        reporte.refresh_from_db()
        self.assertEqual(reporte.titulo, 'Bache ya muy grande')
        self.assertEqual(reporte.gravedad, 'grave')
        self.assertEqual(reporte.fecha_incidente, fecha_original)

    def test_CP_MIS_07_editar_ubicacion_recalcula_la_zona(self):
        reporte = self.crear_reporte(coord=COORD_NORTE)
        response = self.editar(reporte, {'latitud': f'{COORD_SUR[0]:.6f}', 'longitud': f'{COORD_SUR[1]:.6f}'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['zona'], 'sur')

    def test_CP_MIS_08_agregar_y_quitar_fotos_al_editar(self):
        reporte = self.crear_reporte()
        guardada = Imagen.objects.create(reporte=reporte, contenido=b'x', tipo_mime='image/jpeg')
        response = self.editar(reporte, {'imagenes': [foto(), foto('PNG')], 'imagenes_eliminar': [guardada.id]})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['total_imagenes'], 2)
        self.assertFalse(Imagen.objects.filter(pk=guardada.pk).exists())

    def test_CP_MIS_09_no_puede_quedar_con_mas_de_tres_fotos(self):
        reporte = self.crear_reporte()
        for _ in range(2):
            Imagen.objects.create(reporte=reporte, contenido=b'x', tipo_mime='image/jpeg')
        response = self.editar(reporte, {'imagenes': [foto(), foto()]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['imagenes'], ['Un reporte puede tener máximo 3 fotos.'])
        self.assertEqual(reporte.imagenes.count(), 2)

    def test_CP_MIS_10_editar_con_datos_invalidos_no_guarda_cambios(self):
        reporte = self.crear_reporte(titulo='Original')
        response = self.editar(reporte, {'titulo': 'Cambio', 'descripcion': 'Corta'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('descripcion', response.data)
        reporte.refresh_from_db()
        self.assertEqual(reporte.titulo, 'Original')

    def test_CP_MIS_11_no_puede_editar_ni_eliminar_reportes_ajenos(self):
        ajeno = self.crear_reporte(usuario=self.luis)
        for response in (self.editar(ajeno, {'titulo': 'Hackeado'}), self.client.delete(url_detalle(ajeno.pk))):
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(response.data['detail'], 'Solo el autor puede modificar este reporte.')
        self.assertTrue(Reporte.objects.filter(pk=ajeno.pk, titulo='Bache profundo').exists())

    def test_CP_MIS_12_reporte_resuelto_no_se_edita_ni_elimina(self):
        resuelto = self.crear_reporte(resuelto=True)
        for response in (self.editar(resuelto, {'titulo': 'Cambio'}), self.client.delete(url_detalle(resuelto.pk))):
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
            self.assertEqual(response.data['detail'], 'Este reporte ya está resuelto y no admite cambios.')
        self.assertTrue(Reporte.objects.filter(pk=resuelto.pk).exists())

    def test_CP_MIS_13_reporte_expirado_no_se_edita(self):
        expirado = self.crear_reporte(tipo=self.choque, hace=timedelta(hours=25))
        response = self.editar(expirado, {'titulo': 'Cambio'})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['detail'], 'Este reporte expiró y ya no admite cambios.')

    def test_CP_MIS_14_eliminar_mi_reporte_con_sus_fotos_y_reacciones(self):
        reporte = self.crear_reporte()
        Imagen.objects.create(reporte=reporte, contenido=b'x', tipo_mime='image/jpeg')
        Reaccion.objects.create(reporte=reporte, usuario=self.luis, tipo='sin_resolver')
        Denuncia.objects.create(reporte=reporte, usuario=self.luis, motivo='Parece un reporte falso.')
        response = self.client.delete(url_detalle(reporte.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Reporte.objects.filter(pk=reporte.pk).exists())
        self.assertEqual((Imagen.objects.count(), Reaccion.objects.count(), Denuncia.objects.count()), (0, 0, 0))
        # Al recargar la lista ya no aparece y el resumen se actualiza
        lista = self.client.get(URL_MIS_REPORTES)
        self.assertNotIn(reporte.id, self.ids(lista))
        self.assertEqual(lista.data['resumen']['total'], 0)

    def test_CP_MIS_15_eliminar_un_reporte_que_ya_no_existe(self):
        self.assertEqual(self.client.delete(url_detalle(99999)).status_code, status.HTTP_404_NOT_FOUND)

    def test_CP_MIS_16_quitar_foto_que_no_es_del_reporte(self):
        mio = self.crear_reporte()
        ajeno = self.crear_reporte(usuario=self.luis)
        foto_ajena = Imagen.objects.create(reporte=ajeno, contenido=b'x', tipo_mime='image/jpeg')
        response = self.editar(mio, {'imagenes_eliminar': [foto_ajena.id]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('imagenes_eliminar', response.data)
        self.assertTrue(Imagen.objects.filter(pk=foto_ajena.pk).exists())
