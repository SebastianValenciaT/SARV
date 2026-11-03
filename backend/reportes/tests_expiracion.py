"""Pruebas de la expiración de reportes por tipo (se calcula, no se guarda).

El tiempo se congela con mock.patch('django.utils.timezone.now'): todo el código
usa timezone.now(), así que "ahora" es el mismo en el modelo, los filtros y las vistas.
"""
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import Usuario

from .models import Denuncia, Reaccion, Reporte, TipoIncidente
from .serializers import fecha_iso
from .zonas import CENTRO_LAT, CENTRO_LNG

AHORA = datetime(2026, 10, 28, 18, 0, tzinfo=dt_timezone.utc)
MOTIVO = 'Ese choque ya no está, pasé hace un momento por ahí.'


class BaseExpiracion(APITestCase):
    def setUp(self):
        cache.clear()   # throttles
        reloj = mock.patch('django.utils.timezone.now', return_value=AHORA)
        reloj.start()
        self.addCleanup(reloj.stop)   # se restaura aunque la prueba falle

        self.autor = Usuario.objects.create_user('autor@correo.mx', 'secreto1', nombre='Ana Autora')
        self.vecino = Usuario.objects.create_user('vecino@correo.mx', 'secreto2', nombre='Vecino')
        self.choque = TipoIncidente.objects.get(nombre='Choque')
        self.bache = TipoIncidente.objects.get(nombre='Bache')

    def crear(self, hace, tipo=None, titulo='Reporte', resuelto=False):
        """Reporte publicado hace `hace` (creado_en se fija con update(), como en seed_demo)."""
        reporte = Reporte.objects.create(
            usuario=self.autor, tipo=tipo or self.choque, titulo=titulo,
            descripcion='Descripción suficientemente larga', gravedad='leve',
            direccion='Av. Tecnológico', latitud=f'{CENTRO_LAT + 0.05:.6f}',
            longitud=f'{CENTRO_LNG:.6f}', fecha_incidente=AHORA - hace,
        )
        Reporte.objects.filter(pk=reporte.pk).update(creado_en=AHORA - hace)
        if resuelto:
            reporte.resolver()
        reporte.refresh_from_db()
        return reporte

    def ids(self, url, **params):
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        datos = response.data['results'] if isinstance(response.data, dict) else response.data
        return {r['id'] for r in datos}

    def lista(self, **params):
        return self.ids(reverse('reporte-lista'), **params)

    def mapa(self, **params):
        return self.ids(reverse('mapa-reportes'), **params)


class ReglaTests(BaseExpiracion):
    def test_tipos_temporales_y_sin_limite(self):
        duraciones = dict(TipoIncidente.objects.values_list('nombre', 'duracion_horas'))
        self.assertEqual(duraciones['Choque'], 24)
        self.assertEqual(duraciones['Tráfico'], 24)
        self.assertEqual(duraciones['Inundación'], 24)
        self.assertIsNone(duraciones['Bache'])
        self.assertIsNone(duraciones['Obstrucción'])
        self.assertIsNone(duraciones['Otro'])

    def test_tipo_sin_duracion_nunca_expira(self):
        viejo = self.crear(timedelta(days=365), tipo=self.bache)
        self.assertIsNone(viejo.expira_en)
        self.assertFalse(viejo.esta_expirado)
        self.assertEqual(viejo.estado_efectivo, 'sin_resolver')
        self.assertTrue(viejo.es_editable)

    def test_choque_a_23_59_vigente(self):
        reporte = self.crear(timedelta(hours=23, minutes=59))
        self.assertFalse(reporte.esta_expirado)
        self.assertTrue(reporte.es_editable)

    def test_choque_a_24_horas_exactas_expirado(self):
        reporte = self.crear(timedelta(hours=24))
        self.assertEqual(reporte.expira_en, AHORA)
        self.assertTrue(reporte.esta_expirado)
        self.assertEqual(reporte.estado_efectivo, 'expirado')
        self.assertFalse(reporte.es_editable)        # RN-14: solo lectura
        self.assertEqual(reporte.estado, 'sin_resolver')   # lo guardado no cambia

    def test_gana_resuelto(self):
        reporte = self.crear(timedelta(days=2), resuelto=True)
        self.assertFalse(reporte.esta_expirado)
        self.assertEqual(reporte.estado_efectivo, 'resuelto')

    def test_base_de_datos_y_python_coinciden_en_el_limite(self):
        casos = [
            self.crear(timedelta(hours=24) - timedelta(microseconds=1), titulo='justo antes'),
            self.crear(timedelta(hours=24), titulo='justo en el límite'),
            self.crear(timedelta(hours=24, microseconds=1), titulo='justo después'),
            self.crear(timedelta(days=30), tipo=self.bache, titulo='sin límite'),
            self.crear(timedelta(days=2), titulo='resuelto vencido', resuelto=True),
        ]
        expirados_bd = set(Reporte.objects.expirados().values_list('id', flat=True))
        no_expirados_bd = set(Reporte.objects.no_expirados().values_list('id', flat=True))
        for reporte in casos:
            with self.subTest(reporte.titulo):
                self.assertEqual(reporte.id in expirados_bd, reporte.esta_expirado)
                # complemento exacto: cada reporte está en uno y solo uno de los dos
                self.assertNotEqual(reporte.id in expirados_bd, reporte.id in no_expirados_bd)
        self.assertEqual(
            {r.titulo for r in casos if r.esta_expirado}, {'justo en el límite', 'justo después'}
        )

    def test_anotacion_igual_a_la_propiedad(self):
        reporte = self.crear(timedelta(hours=3))
        anotado = Reporte.objects.con_expiracion().get(pk=reporte.pk)
        self.assertEqual(anotado.expira_en_bd, reporte.expira_en)
        bache = self.crear(timedelta(hours=3), tipo=self.bache)
        self.assertIsNone(Reporte.objects.con_expiracion().get(pk=bache.pk).expira_en_bd)


class LecturaTests(BaseExpiracion):
    def setUp(self):
        super().setUp()
        self.vigente = self.crear(timedelta(hours=2), titulo='Choque vigente')
        self.expirado = self.crear(timedelta(hours=30), titulo='Choque expirado')
        self.bache_viejo = self.crear(timedelta(days=60), tipo=self.bache, titulo='Bache viejo')

    def test_mapa_excluye_expirados(self):
        self.assertEqual(self.mapa(), {self.vigente.id, self.bache_viejo.id})

    def test_mapa_nunca_muestra_expirados_aunque_se_pidan(self):
        self.assertEqual(self.mapa(estado='expirado'), set())

    def test_lista_por_defecto_excluye_expirados(self):
        self.assertEqual(self.lista(), {self.vigente.id, self.bache_viejo.id})

    def test_lista_estado_expirado(self):
        self.assertEqual(self.lista(estado='expirado'), {self.expirado.id})

    def test_lista_estado_sin_resolver_solo_vigentes(self):
        self.assertEqual(self.lista(estado='sin_resolver'), {self.vigente.id, self.bache_viejo.id})

    def test_estado_invalido_400(self):
        response = self.client.get(reverse('reporte-lista'), {'estado': 'caducado'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)

    def test_resuelto_vencido_sigue_en_la_lista(self):
        resuelto = self.crear(timedelta(days=2), titulo='Choque resuelto', resuelto=True)
        self.assertIn(resuelto.id, self.lista())
        self.assertIn(resuelto.id, self.lista(estado='resuelto'))
        self.assertNotIn(resuelto.id, self.lista(estado='expirado'))
        self.assertNotIn(resuelto.id, self.lista(estado='sin_resolver'))
        datos = self.client.get(reverse('reporte-lista')).data['results']
        self.assertEqual(next(r for r in datos if r['id'] == resuelto.id)['estado'], 'resuelto')

    def test_lista_expone_estado_efectivo_y_expira_en(self):
        datos = self.client.get(reverse('reporte-lista'), {'estado': 'expirado'}).data['results']
        self.assertEqual(datos[0]['estado'], 'expirado')
        self.assertEqual(datos[0]['expira_en'], fecha_iso(self.expirado.expira_en))
        datos = self.client.get(reverse('reporte-lista')).data['results']
        bache = next(r for r in datos if r['id'] == self.bache_viejo.id)
        self.assertIsNone(bache['expira_en'])

    def test_detalle_de_expirado_responde_200(self):
        response = self.client.get(reverse('reporte-detalle', args=[self.expirado.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], 'expirado')
        self.assertEqual(response.data['expira_en'], fecha_iso(AHORA - timedelta(hours=6)))

    def test_mapa_no_expone_expira_en(self):
        response = self.client.get(reverse('mapa-reportes'))
        self.assertNotIn('expira_en', response.data[0])

    def test_lista_sin_consultas_extra(self):
        # 1) count de la paginación, 2) reportes + tipo (JOIN), 3) prefetch de imágenes.
        # El estado efectivo usa el tipo ya cargado: no agrega una consulta por reporte.
        for i in range(5):
            self.crear(timedelta(hours=i), titulo=f'Extra {i}')
        with self.assertNumQueries(3):
            response = self.client.get(reverse('reporte-lista'))
        self.assertEqual(response.data['count'], 7)

    def test_mapa_una_sola_consulta(self):
        with self.assertNumQueries(1):
            self.client.get(reverse('mapa-reportes'))


class AccionesTests(BaseExpiracion):
    def setUp(self):
        super().setUp()
        self.expirado = self.crear(timedelta(hours=25))
        self.client.force_authenticate(self.vecino)

    def assertExpirado(self, response):
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['codigo'], 'reporte_expirado')
        self.assertEqual(response.data['detail'], 'Este reporte expiró y ya no admite cambios.')

    def test_reaccionar_409(self):
        url = reverse('reporte-reaccion', args=[self.expirado.pk])
        self.assertExpirado(self.client.put(url, {'tipo': 'sin_resolver'}, format='json'))
        self.assertExpirado(self.client.delete(url))
        self.assertEqual(Reaccion.objects.count(), 0)

    def test_denunciar_409(self):
        url = reverse('reporte-denuncias', args=[self.expirado.pk])
        self.assertExpirado(self.client.post(url, {'motivo': MOTIVO}, format='json'))
        self.assertEqual(Denuncia.objects.count(), 0)

    def test_el_autor_no_puede_resolverlo(self):
        self.client.force_authenticate(self.autor)
        url = reverse('reporte-reaccion', args=[self.expirado.pk])
        self.assertExpirado(self.client.put(url, {'tipo': 'resuelto'}, format='json'))
        self.expirado.refresh_from_db()
        self.assertEqual(self.expirado.estado, 'sin_resolver')
        self.assertIsNone(self.expirado.resuelto_en)

    def test_resuelto_vencido_sigue_respondiendo_reporte_resuelto(self):
        resuelto = self.crear(timedelta(days=2), resuelto=True)
        url = reverse('reporte-reaccion', args=[resuelto.pk])
        response = self.client.put(url, {'tipo': 'sin_resolver'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['codigo'], 'reporte_resuelto')

    def test_vigente_si_acepta_reacciones(self):
        vigente = self.crear(timedelta(hours=23))
        url = reverse('reporte-reaccion', args=[vigente.pk])
        self.assertEqual(self.client.put(url, {'tipo': 'sin_resolver'}, format='json').status_code, 200)
