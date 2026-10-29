"""Pruebas de reacciones (PUT/DELETE reportes/{id}/reaccion/) y denuncias
(POST reportes/{id}/denuncias/).

Aún no hay JWT: force_authenticate simula un usuario con sesión.
"""
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from usuarios.models import Usuario

from .models import Denuncia, Reaccion, Reporte, TipoIncidente
from .serializers import fecha_iso
from .zonas import CENTRO_LAT, CENTRO_LNG

MOTIVO = 'No hay ningún bache en esa calle, la acabo de recorrer.'


class BaseInteraccion(APITestCase):
    def setUp(self):
        cache.clear()   # los contadores del throttle viven en la caché: cada prueba empieza en cero
        self.autor = Usuario.objects.create_user('autor@correo.mx', 'secreto1', nombre='Ana Autora')
        self.vecino = Usuario.objects.create_user('vecino@correo.mx', 'secreto2', nombre='Vecino')
        self.otro = Usuario.objects.create_user('otro@correo.mx', 'secreto3', nombre='Otra Vecina')
        self.reporte = Reporte.objects.create(
            usuario=self.autor, tipo=TipoIncidente.objects.get(nombre='Bache'), titulo='Bache profundo',
            descripcion='Bache profundo en el carril derecho', gravedad='moderado',
            direccion='Av. Tecnológico', latitud=f'{CENTRO_LAT + 0.05:.6f}',
            longitud=f'{CENTRO_LNG:.6f}', fecha_incidente=timezone.now() - timedelta(hours=1),
        )
        self.client.force_authenticate(self.vecino)

    def url_reaccion(self, pk=None):
        return reverse('reporte-reaccion', args=[pk or self.reporte.pk])

    def url_denuncias(self, pk=None):
        return reverse('reporte-denuncias', args=[pk or self.reporte.pk])

    def reaccionar(self, tipo, pk=None):
        return self.client.put(self.url_reaccion(pk), {'tipo': tipo}, format='json')

    def quitar(self, pk=None):
        return self.client.delete(self.url_reaccion(pk))

    def denunciar(self, motivo=MOTIVO, pk=None):
        return self.client.post(self.url_denuncias(pk), {'motivo': motivo}, format='json')

    def como(self, usuario):
        self.client.force_authenticate(usuario)

    def resolver(self):
        self.reporte.resolver()
        self.reporte.refresh_from_db()

    def fase(self, response, nombre):
        return next(f for f in response.data['seguimiento'] if f['fase'] == nombre)


class ReaccionTests(BaseInteraccion):
    def test_crea_reaccion_y_responde_el_detalle(self):
        response = self.reaccionar('sin_resolver')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['id'], self.reporte.pk)
        self.assertEqual(response.data['mi_reaccion'], 'sin_resolver')
        self.assertEqual(response.data['reacciones'], {'sin_resolver': 1, 'resuelto': 0})
        self.assertEqual(response.data['confirmaciones'], 1)
        self.assertEqual(Reaccion.objects.get().usuario, self.vecino)

    def test_cambiar_de_tipo_no_duplica_la_fila(self):
        self.reaccionar('sin_resolver')
        response = self.reaccionar('resuelto')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mi_reaccion'], 'resuelto')
        self.assertEqual(response.data['reacciones'], {'sin_resolver': 0, 'resuelto': 1})
        self.assertEqual(Reaccion.objects.count(), 1)

    def test_repetir_el_mismo_tipo_no_duplica(self):
        self.reaccionar('sin_resolver')
        self.reaccionar('sin_resolver')
        self.assertEqual(Reaccion.objects.count(), 1)

    def test_reaccion_ajena_no_cambia_el_estado(self):
        self.reaccionar('resuelto')
        self.reporte.refresh_from_db()
        self.assertEqual(self.reporte.estado, Reporte.Estado.SIN_RESOLVER)
        self.assertIsNone(self.reporte.resuelto_en)

    def test_tipo_invalido_400(self):
        response = self.reaccionar('ya_no_existe')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tipo', response.data)
        self.assertEqual(Reaccion.objects.count(), 0)

    def test_sin_tipo_400(self):
        response = self.client.put(self.url_reaccion(), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tipo', response.data)

    def test_quitar_reaccion(self):
        self.reaccionar('sin_resolver')
        response = self.quitar()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['mi_reaccion'])
        self.assertEqual(response.data['confirmaciones'], 0)
        self.assertEqual(Reaccion.objects.count(), 0)

    def test_quitar_solo_borra_la_mia(self):
        Reaccion.objects.create(reporte=self.reporte, usuario=self.otro, tipo='sin_resolver')
        self.reaccionar('sin_resolver')
        response = self.quitar()
        self.assertEqual(response.data['reacciones'], {'sin_resolver': 1, 'resuelto': 0})
        self.assertTrue(Reaccion.objects.filter(usuario=self.otro).exists())

    def test_quitar_sin_tener_reaccion_es_idempotente(self):
        response = self.quitar()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['mi_reaccion'])

    def test_anonimo_rechazado(self):
        self.client.force_authenticate(None)
        # Hoy 403 (autenticación por sesión de DRF); con JWT será 401.
        self.assertIn(self.reaccionar('sin_resolver').status_code, (401, 403))
        self.assertIn(self.quitar().status_code, (401, 403))
        self.assertEqual(Reaccion.objects.count(), 0)

    def test_reporte_inexistente_404(self):
        self.assertEqual(self.reaccionar('sin_resolver', pk=99999).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.quitar(pk=99999).status_code, status.HTTP_404_NOT_FOUND)

    def test_reporte_resuelto_rechaza_reaccionar(self):
        self.resolver()
        response = self.reaccionar('sin_resolver')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['codigo'], 'reporte_resuelto')
        self.assertEqual(Reaccion.objects.count(), 0)

    def test_reporte_resuelto_rechaza_quitar(self):
        Reaccion.objects.create(reporte=self.reporte, usuario=self.vecino, tipo='resuelto')
        self.resolver()
        self.assertEqual(self.quitar().status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Reaccion.objects.count(), 1)


class ReaccionAutorTests(BaseInteraccion):
    def setUp(self):
        super().setUp()
        self.como(self.autor)

    def test_resuelto_resuelve_el_reporte_sin_crear_fila(self):
        response = self.reaccionar('resuelto')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], 'resuelto')
        self.assertTrue(self.fase(response, 'resuelto')['completada'])
        self.assertIsNotNone(self.fase(response, 'resuelto')['fecha'])
        self.reporte.refresh_from_db()
        self.assertEqual(self.reporte.estado, Reporte.Estado.RESUELTO)
        self.assertIsNotNone(self.reporte.resuelto_en)
        self.assertEqual(Reaccion.objects.count(), 0)

    def test_resolver_no_cuenta_como_confirmacion(self):
        response = self.reaccionar('resuelto')
        self.assertEqual(response.data['confirmaciones'], 0)
        self.assertEqual(response.data['reacciones'], {'sin_resolver': 0, 'resuelto': 0})
        self.assertIsNone(response.data['mi_reaccion'])
        # Sin reacciones ajenas, la fase 2 sigue "Pendiente" (fecha null).
        confirmado = self.fase(response, 'confirmado')
        self.assertFalse(confirmado['completada'])
        self.assertIsNone(confirmado['fecha'])

    def test_sin_resolver_se_ignora(self):
        response = self.reaccionar('sin_resolver')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], 'sin_resolver')
        self.assertIsNone(response.data['mi_reaccion'])
        self.assertEqual(Reaccion.objects.count(), 0)

    def test_resolver_un_reporte_ya_resuelto_409(self):
        self.resolver()
        self.assertEqual(self.reaccionar('resuelto').status_code, status.HTTP_409_CONFLICT)


class EfectoEnDetalleTests(BaseInteraccion):
    def test_conteos_de_varios_usuarios(self):
        self.reaccionar('sin_resolver')
        self.como(self.otro)
        response = self.reaccionar('resuelto')
        self.assertEqual(response.data['reacciones'], {'sin_resolver': 1, 'resuelto': 1})
        self.assertEqual(response.data['confirmaciones'], 2)
        self.assertEqual(response.data['mi_reaccion'], 'resuelto')
        self.assertEqual(self.fase(response, 'confirmado')['confirmaciones'], 2)

    def test_el_get_del_detalle_ve_lo_mismo(self):
        self.reaccionar('sin_resolver')
        response = self.client.get(reverse('reporte-detalle', args=[self.reporte.pk]))
        self.assertEqual(response.data['mi_reaccion'], 'sin_resolver')
        self.assertEqual(response.data['confirmaciones'], 1)

    def test_confirmado_usa_la_primera_reaccion_ajena(self):
        # Una reacción vieja del autor (datos previos) no debe contar como confirmación.
        ahora = timezone.now()
        del_autor = Reaccion.objects.create(reporte=self.reporte, usuario=self.autor, tipo='sin_resolver')
        Reaccion.objects.filter(pk=del_autor.pk).update(creada_en=ahora - timedelta(hours=3))
        self.reaccionar('sin_resolver')
        primera = Reaccion.objects.get(usuario=self.vecino)
        Reaccion.objects.filter(pk=primera.pk).update(creada_en=ahora - timedelta(hours=2))
        self.como(self.otro)
        response = self.reaccionar('resuelto')

        confirmado = self.fase(response, 'confirmado')
        self.assertTrue(confirmado['completada'])
        primera.refresh_from_db()
        self.assertEqual(confirmado['fecha'], fecha_iso(primera.creada_en))

    def test_quitar_la_unica_reaccion_regresa_confirmado_a_pendiente(self):
        self.reaccionar('sin_resolver')
        response = self.quitar()
        self.assertFalse(self.fase(response, 'confirmado')['completada'])


class DenunciaTests(BaseInteraccion):
    def test_denuncia_exitosa(self):
        response = self.denunciar()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data['ya_denuncie'])
        denuncia = Denuncia.objects.get()
        self.assertEqual((denuncia.usuario, denuncia.reporte), (self.vecino, self.reporte))

    def test_motivo_se_guarda_recortado(self):
        self.denunciar(f'   {MOTIVO}   ')
        self.assertEqual(Denuncia.objects.get().motivo, MOTIVO)

    def test_la_denuncia_no_cambia_el_reporte(self):
        self.denunciar()
        self.reporte.refresh_from_db()
        self.assertEqual(self.reporte.estado, Reporte.Estado.SIN_RESOLVER)
        self.assertEqual(self.client.get(reverse('reporte-lista')).data['count'], 1)

    def test_ya_denuncie_en_el_detalle(self):
        url = reverse('reporte-detalle', args=[self.reporte.pk])
        self.assertFalse(self.client.get(url).data['ya_denuncie'])
        self.denunciar()
        self.assertTrue(self.client.get(url).data['ya_denuncie'])

    def assertMotivoInvalido(self, motivo):
        response = self.denunciar(motivo)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motivo', response.data)
        self.assertEqual(Denuncia.objects.count(), 0)

    def test_motivo_corto(self):
        self.assertMotivoInvalido('Es falso')            # 8 caracteres

    def test_motivo_corto_contando_ya_recortado(self):
        self.assertMotivoInvalido('     falso!     ')    # 6 sin los espacios

    def test_motivo_largo(self):
        self.assertMotivoInvalido('a' * 301)

    def test_motivo_limites_exactos(self):
        self.assertEqual(self.denunciar('a' * 10).status_code, status.HTTP_201_CREATED)
        self.como(self.otro)
        self.assertEqual(self.denunciar('a' * 300).status_code, status.HTTP_201_CREATED)

    def test_motivo_solo_espacios(self):
        self.assertMotivoInvalido('             ')

    def test_sin_motivo(self):
        response = self.client.post(self.url_denuncias(), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motivo', response.data)

    def test_propio_reporte_403(self):
        self.como(self.autor)
        response = self.denunciar()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['codigo'], 'reporte_propio')
        self.assertEqual(Denuncia.objects.count(), 0)

    def test_duplicada_400(self):
        self.denunciar()
        response = self.denunciar()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['codigo'], 'denuncia_duplicada')
        self.assertIn('detail', response.data)
        self.assertEqual(Denuncia.objects.count(), 1)

    def test_duplicada_por_carrera_400(self):
        # Simula dos peticiones simultáneas: la validación previa no ve la otra
        # denuncia y el UniqueConstraint de la base de datos la detiene.
        Denuncia.objects.create(reporte=self.reporte, usuario=self.vecino, motivo=MOTIVO)
        with mock.patch('reportes.views.Denuncia.objects.filter') as filtro:
            filtro.return_value.exists.return_value = False
            response = self.denunciar()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['codigo'], 'denuncia_duplicada')
        self.assertEqual(Denuncia.objects.count(), 1)

    def test_reporte_resuelto_409(self):
        self.resolver()
        response = self.denunciar()
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Denuncia.objects.count(), 0)

    def test_anonimo_rechazado(self):
        self.client.force_authenticate(None)
        self.assertIn(self.denunciar().status_code, (401, 403))
        self.assertEqual(Denuncia.objects.count(), 0)

    def test_reporte_inexistente_404(self):
        self.assertEqual(self.denunciar(pk=99999).status_code, status.HTTP_404_NOT_FOUND)


class ThrottleTests(BaseInteraccion):
    """La tasa real (60/min, 10/hour) se reemplaza por '2/hour' para no depender del reloj.

    override_settings no sirve aquí: DRF copia DEFAULT_THROTTLE_RATES en
    ScopedRateThrottle.THROTTLE_RATES al importarse. patch.object lo cambia solo
    dentro del `with` y lo restaura al salir (aunque la prueba falle).
    """

    def test_reacciones_limitadas(self):
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'reacciones': '2/hour'}):
            self.reaccionar('sin_resolver')
            self.quitar()   # PUT y DELETE comparten el mismo contador
            response = self.reaccionar('resuelto')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Reaccionaste demasiadas veces', str(response.data['detail']))

    def test_denuncias_limitadas(self):
        otros = [
            Reporte.objects.create(
                usuario=self.autor, tipo=self.reporte.tipo, titulo=f'Reporte {i}',
                descripcion='Bache profundo en el carril derecho', gravedad='leve',
                latitud=self.reporte.latitud, longitud=self.reporte.longitud,
                fecha_incidente=self.reporte.fecha_incidente,
            )
            for i in range(2)
        ]
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'denuncias': '2/hour'}):
            self.denunciar(pk=otros[0].pk)
            self.denunciar(pk=otros[1].pk)
            response = self.denunciar()
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('demasiadas denuncias', str(response.data['detail']))
        self.assertEqual(Denuncia.objects.count(), 2)

    def test_cada_usuario_tiene_su_contador(self):
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'reacciones': '2/hour'}):
            self.reaccionar('sin_resolver')
            self.reaccionar('resuelto')
            self.como(self.otro)
            response = self.reaccionar('sin_resolver')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
