"""Pruebas de autenticación: registro, login JWT, renovación, /me/ y límites.

A diferencia de las pruebas de reportes (que usan force_authenticate), aquí los
tokens son reales: se obtienen en /api/login/ y viajan en "Authorization: Bearer".
"""
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from reportes.models import Reporte, TipoIncidente
from reportes.zonas import CENTRO_LAT, CENTRO_LNG

from .models import Usuario

URL_REGISTRO = reverse('api_registro')
URL_LOGIN = reverse('api_login')
URL_REFRESH = reverse('api_token_refresh')
URL_ME = reverse('api_me')
PASSWORD = 'Calle-Segura-2026'


class BaseAuth(APITestCase):
    def setUp(self):
        cache.clear()   # contadores del throttle: cada prueba empieza en cero
        self.addCleanup(cache.clear)

    def registrar(self, **extra):
        datos = {
            'email': 'nueva@correo.mx', 'nombre': 'Nueva', 'apellido': 'Vecina',
            'password': PASSWORD, 'aceptaPrivacidad': True,
        }
        datos.update(extra)
        return self.client.post(URL_REGISTRO, datos, format='json')

    def login(self, email='demo@correo.mx', password=PASSWORD):
        return self.client.post(URL_LOGIN, {'email': email, 'password': password}, format='json')

    def con_token(self, access):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')


class RegistroTests(BaseAuth):
    def test_registro_exitoso(self):
        response = self.registrar()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertNotIn('password', response.data)
        usuario = Usuario.objects.get(email='nueva@correo.mx')
        self.assertEqual(usuario.nombre, 'Nueva Vecina')
        self.assertNotEqual(usuario.password, PASSWORD)   # guardada con hash
        self.assertTrue(usuario.check_password(PASSWORD))
        self.assertIsNotNone(usuario.privacidad_aceptada_en)

    def test_correo_se_guarda_en_minusculas(self):
        self.registrar(email='Nueva@Correo.MX')
        self.assertTrue(Usuario.objects.filter(email='nueva@correo.mx').exists())

    def test_correo_duplicado_400(self):
        Usuario.objects.create_user('nueva@correo.mx', PASSWORD, nombre='Ya existe')
        response = self.registrar()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_correo_duplicado_con_mayusculas_400_no_500(self):
        Usuario.objects.create_user('demo@sarv.example', PASSWORD, nombre='Demo')
        response = self.registrar(email='Demo@sarv.example')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertEqual(Usuario.objects.filter(email__iexact='demo@sarv.example').count(), 1)

    def test_contrasena_debil_400(self):
        response = self.registrar(password='12345678')   # común y solo números
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertFalse(Usuario.objects.exists())

    def test_contrasena_corta_400(self):
        response = self.registrar(password='Ab-12')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_sin_aceptar_privacidad_400(self):
        response = self.registrar(aceptaPrivacidad=False)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('aceptaPrivacidad', response.data)
        self.assertFalse(Usuario.objects.exists())


class LoginTests(BaseAuth):
    def setUp(self):
        super().setUp()
        self.usuario = Usuario.objects.create_user('demo@correo.mx', PASSWORD, nombre='Demo')

    def test_login_correcto_devuelve_access_y_refresh(self):
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_con_mayusculas_en_el_correo(self):
        self.assertEqual(self.login(email='  Demo@Correo.MX ').status_code, status.HTTP_200_OK)

    def test_login_incorrecto_401(self):
        response = self.login(password='otra-cosa-123')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)

    def test_refresh_valido_devuelve_nuevo_access(self):
        refresh = self.login().data['refresh']
        response = self.client.post(URL_REFRESH, {'refresh': refresh}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_invalido_401(self):
        response = self.client.post(URL_REFRESH, {'refresh': 'no-es-un-token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_con_token(self):
        self.con_token(self.login().data['access'])
        response = self.client.get(URL_ME)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'id': self.usuario.id, 'email': 'demo@correo.mx', 'nombre': 'Demo'})

    def test_me_sin_token_401(self):
        self.assertEqual(self.client.get(URL_ME).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_invalido_en_endpoint_publico_401(self):
        # JWTAuthentication rechaza el encabezado antes de mirar el permiso (AllowAny).
        # Por eso el frontend no manda tokens vencidos y reintenta los GET sin token.
        lista = reverse('reporte-lista')
        self.con_token('token-vencido-o-alterado')
        self.assertEqual(self.client.get(lista).status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.credentials()   # sin encabezado
        self.assertEqual(self.client.get(lista).status_code, status.HTTP_200_OK)


class LimitesTests(BaseAuth):
    def test_limite_de_login(self):
        Usuario.objects.create_user('demo@correo.mx', PASSWORD, nombre='Demo')
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'auth_login': '2/min'}):
            self.assertEqual(self.login().status_code, status.HTTP_200_OK)
            self.assertEqual(self.login(password='mala-123456').status_code, status.HTTP_401_UNAUTHORIZED)
            response = self.login()
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Demasiados intentos', str(response.data['detail']))

    def test_limite_de_registro(self):
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'auth_registro': '2/hour'}):
            self.assertEqual(self.registrar(email='a@correo.mx').status_code, status.HTTP_201_CREATED)
            self.assertEqual(self.registrar(email='b@correo.mx').status_code, status.HTTP_201_CREATED)
            response = self.registrar(email='c@correo.mx')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('demasiados registros', str(response.data['detail']))
        self.assertFalse(Usuario.objects.filter(email='c@correo.mx').exists())


class IntegracionJWTTests(BaseAuth):
    """Flujo completo con un token real: demuestra que JWTAuthentication está conectada."""

    def setUp(self):
        super().setUp()
        vecina = Usuario.objects.create_user('vecina@correo.mx', 'secreto1', nombre='Vecina')
        self.bache = TipoIncidente.objects.get(nombre='Bache')
        self.ajeno = Reporte.objects.create(
            usuario=vecina, tipo=self.bache, titulo='Bache ajeno',
            descripcion='Bache profundo en el carril derecho', gravedad='moderado',
            latitud=f'{CENTRO_LAT + 0.05:.6f}', longitud=f'{CENTRO_LNG:.6f}',
            fecha_incidente=timezone.now() - timedelta(hours=1),
        )

    def datos_reporte(self):
        return {
            'tipo': self.bache.id, 'titulo': 'Bache nuevo', 'gravedad': 'leve',
            'descripcion': 'Bache recién abierto frente a la escuela',
            'latitud': f'{CENTRO_LAT:.6f}', 'longitud': f'{CENTRO_LNG:.6f}',
            'fecha_incidente': (timezone.now() - timedelta(minutes=30)).isoformat(),
        }

    def test_crear_reporte_sin_token_401(self):
        response = self.client.post(reverse('reporte-lista'), self.datos_reporte(), format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_registro_login_y_acciones_con_bearer(self):
        self.assertEqual(self.registrar().status_code, status.HTTP_201_CREATED)
        tokens = self.login(email='nueva@correo.mx').data
        self.con_token(tokens['access'])

        creado = self.client.post(reverse('reporte-lista'), self.datos_reporte(), format='multipart')
        self.assertEqual(creado.status_code, status.HTTP_201_CREATED, creado.data)
        self.assertTrue(creado.data['es_autor'])
        self.assertEqual(Reporte.objects.get(pk=creado.data['id']).usuario.email, 'nueva@correo.mx')

        url = reverse('reporte-reaccion', args=[self.ajeno.pk])
        reaccion = self.client.put(url, {'tipo': 'sin_resolver'}, format='json')
        self.assertEqual(reaccion.status_code, status.HTTP_200_OK)
        self.assertEqual(reaccion.data['mi_reaccion'], 'sin_resolver')
