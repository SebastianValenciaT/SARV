"""Pruebas de los endpoints públicos de lectura (tipos, reportes, mapa, imágenes)."""
from datetime import datetime, timedelta
from io import StringIO
from unittest import mock
from zoneinfo import ZoneInfo

from django.core.management import CommandError, call_command
from django.db.models import F
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import Usuario

from .models import Denuncia, Imagen, Reaccion, Reporte, TipoIncidente
from .zonas import CENTRO_LAT, CENTRO_LNG

JUAREZ = ZoneInfo('America/Ciudad_Juarez')
PNG_FALSO = b'\x89PNG\r\n\x1a\n' + b'0' * 20   # basta con unos bytes para probar el endpoint


class BaseApi(APITestCase):
    def setUp(self):
        self.autor = Usuario.objects.create_user('autor@correo.mx', 'secreto1', nombre='Ana Autora')
        self.vecino = Usuario.objects.create_user('vecino@correo.mx', 'secreto2', nombre='Vecino')
        self.bache = TipoIncidente.objects.get(nombre='Bache')
        self.choque = TipoIncidente.objects.get(nombre='Choque')
        self.inundacion = TipoIncidente.objects.get(nombre='Inundación')

    def crear_reporte(self, hace=timedelta(hours=1), dlat=0.05, dlng=0.0, **extra):
        """Crea un reporte; `hace` define fecha_incidente y creado_en (para controlar el orden)."""
        momento = timezone.now() - hace
        datos = dict(
            usuario=self.autor, tipo=self.bache, titulo='Bache profundo',
            descripcion='Bache profundo en el carril derecho', gravedad='moderado',
            direccion='Av. Tecnológico', latitud=f'{CENTRO_LAT + dlat:.6f}',
            longitud=f'{CENTRO_LNG + dlng:.6f}', fecha_incidente=momento,
        )
        datos.update(extra)
        reporte = Reporte.objects.create(**datos)
        Reporte.objects.filter(pk=reporte.pk).update(creado_en=momento)
        return reporte

    def ids(self, response):
        """Ids de un listado paginado o sin paginar."""
        datos = response.data['results'] if isinstance(response.data, dict) else response.data
        return [r['id'] for r in datos]


class TiposApiTests(BaseApi):
    def test_lista_los_seis_tipos(self):
        response = self.client.get(reverse('tipos'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)
        self.assertEqual(set(response.data[0].keys()), {'id', 'nombre'})


class ListadoApiTests(BaseApi):
    def test_paginado_y_ordenado_del_mas_reciente(self):
        viejo = self.crear_reporte(hace=timedelta(days=2))
        nuevo = self.crear_reporte(hace=timedelta(minutes=5))
        medio = self.crear_reporte(hace=timedelta(hours=5))
        response = self.client.get(reverse('reporte-lista'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data.keys()), {'count', 'next', 'previous', 'results'})
        self.assertEqual(self.ids(response), [nuevo.id, medio.id, viejo.id])

    def test_campos_conteos_e_imagen_principal(self):
        r = self.crear_reporte()
        img = Imagen.objects.create(reporte=r, contenido=PNG_FALSO, tipo_mime='image/png')
        Imagen.objects.create(reporte=r, contenido=PNG_FALSO, tipo_mime='image/png')
        Reaccion.objects.create(reporte=r, usuario=self.vecino, tipo='sin_resolver')
        item = self.client.get(reverse('reporte-lista')).data['results'][0]
        self.assertEqual(item['confirmaciones'], 1)
        self.assertEqual(item['total_imagenes'], 2)
        self.assertEqual(item['tipo'], self.bache.id)
        self.assertEqual(item['tipo_etiqueta'], 'Bache')
        self.assertEqual(item['zona'], 'norte')
        self.assertTrue(item['imagen_principal'].endswith(f'/api/imagenes/{img.id}/'))
        self.assertTrue(item['imagen_principal'].startswith('http'))
        self.assertNotIn('contenido', item)

    def test_coordenadas_numericas_y_mismo_formato_en_los_tres_serializers(self):
        """Leaflet necesita números: lista, detalle y mapa mandan floats idénticos."""
        r = self.crear_reporte(dlat=0.012345, dlng=-0.054321)
        de_lista = self.client.get(reverse('reporte-lista')).data['results'][0]
        de_detalle = self.client.get(reverse('reporte-detalle', args=[r.id])).data
        de_mapa = self.client.get(reverse('mapa-reportes')).data[0]
        for datos in (de_lista, de_detalle, de_mapa):
            self.assertIsInstance(datos['latitud'], float)
            self.assertIsInstance(datos['longitud'], float)
            self.assertEqual((datos['latitud'], datos['longitud']), (float(r.latitud), float(r.longitud)))

    def test_sin_consultas_n_mas_1(self):
        for _ in range(5):
            r = self.crear_reporte()
            Imagen.objects.create(reporte=r, contenido=PNG_FALSO, tipo_mime='image/png')
        # 1) COUNT de la paginación, 2) reportes con conteos, 3) prefetch de imágenes
        with self.assertNumQueries(3):
            self.client.get(reverse('reporte-lista'))

    def test_filtro_tipo_acepta_varios(self):
        b = self.crear_reporte(tipo=self.bache)
        c = self.crear_reporte(tipo=self.choque)
        self.crear_reporte(tipo=self.inundacion)
        response = self.client.get(reverse('reporte-lista'), {'tipo': [self.bache.id, self.choque.id]})
        self.assertCountEqual(self.ids(response), [b.id, c.id])

    def test_filtro_zona(self):
        norte = self.crear_reporte(dlat=0.05)
        self.crear_reporte(dlat=-0.05)   # sur
        response = self.client.get(reverse('reporte-lista'), {'zona': 'norte'})
        self.assertEqual(self.ids(response), [norte.id])

    def test_filtro_estado(self):
        self.crear_reporte()
        resuelto = self.crear_reporte()
        resuelto.resolver()
        response = self.client.get(reverse('reporte-lista'), {'estado': 'resuelto'})
        self.assertEqual(self.ids(response), [resuelto.id])

    def test_filtro_q_busca_en_titulo_y_direccion(self):
        por_titulo = self.crear_reporte(titulo='Semáforo apagado', direccion='Calle 1')
        por_direccion = self.crear_reporte(titulo='Choque', direccion='Blvd. Zaragoza')
        self.crear_reporte(titulo='Otro', direccion='Av. Juárez')
        self.assertEqual(self.ids(self.client.get(reverse('reporte-lista'), {'q': 'semáforo'})), [por_titulo.id])
        self.assertEqual(self.ids(self.client.get(reverse('reporte-lista'), {'q': 'zaragoza'})), [por_direccion.id])

    def test_filtro_fecha_7d_y_30d(self):
        hoy = self.crear_reporte(hace=timedelta(hours=2))
        semana = self.crear_reporte(hace=timedelta(days=5))
        mes = self.crear_reporte(hace=timedelta(days=20))
        self.crear_reporte(hace=timedelta(days=45))
        url = reverse('reporte-lista')
        self.assertCountEqual(self.ids(self.client.get(url, {'fecha': '7d'})), [hoy.id, semana.id])
        self.assertCountEqual(self.ids(self.client.get(url, {'fecha': '30d'})), [hoy.id, semana.id, mes.id])

    def test_filtro_hoy_usa_la_medianoche_local(self):
        """A las 00:30 en Juárez, un reporte de las 23:50 de ayer (hora local) ya no es de "hoy",
        aunque en UTC ambos momentos caigan en el mismo día."""
        ahora = datetime(2026, 10, 18, 0, 30, tzinfo=JUAREZ)
        ayer_noche = self.crear_reporte(fecha_incidente=datetime(2026, 10, 17, 23, 50, tzinfo=JUAREZ))
        recien = self.crear_reporte(fecha_incidente=datetime(2026, 10, 18, 0, 10, tzinfo=JUAREZ))
        # Mismo día en UTC: 05:50 y 06:10 del 18 de octubre.
        self.assertEqual(ayer_noche.fecha_incidente.astimezone(ZoneInfo('UTC')).day, 18)
        with mock.patch('django.utils.timezone.now', return_value=ahora):
            response = self.client.get(reverse('reporte-lista'), {'fecha': 'hoy'})
        self.assertEqual(self.ids(response), [recien.id])

    def test_filtro_invalido_responde_400(self):
        response = self.client.get(reverse('reporte-lista'), {'zona': 'marte'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('zona', response.data)


class DetalleApiTests(BaseApi):
    def test_detalle_completo_para_anonimo(self):
        r = self.crear_reporte()
        img = Imagen.objects.create(reporte=r, contenido=PNG_FALSO, tipo_mime='image/png')
        Reaccion.objects.create(reporte=r, usuario=self.vecino, tipo='sin_resolver')
        response = self.client.get(reverse('reporte-detalle', args=[r.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        d = response.data
        self.assertEqual(d['descripcion'], r.descripcion)
        self.assertEqual(d['gravedad'], 'moderado')
        self.assertIsInstance(d['latitud'], float)
        self.assertEqual(d['imagenes'][0]['id'], img.id)
        self.assertEqual(d['reacciones'], {'sin_resolver': 1, 'resuelto': 0})
        self.assertIn('actualizado_en', d)
        self.assertFalse(d['es_autor'])
        self.assertIsNone(d['mi_reaccion'])
        self.assertFalse(d['ya_denuncie'])

    def test_seguimiento_de_tres_fases(self):
        r = self.crear_reporte()
        fases = self.client.get(reverse('reporte-detalle', args=[r.id])).data['seguimiento']
        self.assertEqual([f['fase'] for f in fases], ['creado', 'confirmado', 'resuelto'])
        self.assertEqual(fases[0]['autor'], 'Ana Autora')
        self.assertFalse(fases[1]['completada'])
        self.assertIsNone(fases[1]['fecha'])
        self.assertFalse(fases[2]['completada'])

        Reaccion.objects.create(reporte=r, usuario=self.vecino, tipo='resuelto')
        r.resolver()
        fases = self.client.get(reverse('reporte-detalle', args=[r.id])).data['seguimiento']
        self.assertTrue(fases[1]['completada'])
        self.assertEqual(fases[1]['confirmaciones'], 1)
        self.assertTrue(fases[2]['completada'])
        self.assertIsNotNone(fases[2]['fecha'])

    def test_campos_personales_con_usuario(self):
        """Todavía no hay login, pero force_authenticate simula un usuario con sesión."""
        r = self.crear_reporte()
        Reaccion.objects.create(reporte=r, usuario=self.vecino, tipo='resuelto')
        Denuncia.objects.create(reporte=r, usuario=self.vecino, motivo='Parece un reporte falso')
        url = reverse('reporte-detalle', args=[r.id])

        self.client.force_authenticate(self.autor)
        self.assertTrue(self.client.get(url).data['es_autor'])

        self.client.force_authenticate(self.vecino)
        d = self.client.get(url).data
        self.assertFalse(d['es_autor'])
        self.assertEqual(d['mi_reaccion'], 'resuelto')
        self.assertTrue(d['ya_denuncie'])

    def test_inexistente_responde_404(self):
        response = self.client.get(reverse('reporte-detalle', args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MapaApiTests(BaseApi):
    def test_solo_sin_resolver_y_sin_paginar(self):
        activo = self.crear_reporte()
        resuelto = self.crear_reporte()
        resuelto.resolver()
        response = self.client.get(reverse('mapa-reportes'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(self.ids(response), [activo.id])
        self.assertEqual(
            set(response.data[0].keys()),
            {'id', 'latitud', 'longitud', 'tipo', 'tipo_etiqueta', 'fecha_incidente', 'titulo', 'direccion', 'zona'},
        )

    def test_mismos_filtros(self):
        b = self.crear_reporte(tipo=self.bache)
        self.crear_reporte(tipo=self.choque)
        response = self.client.get(reverse('mapa-reportes'), {'tipo': self.bache.id})
        self.assertEqual(self.ids(response), [b.id])


class ImagenApiTests(BaseApi):
    def test_sirve_binario_con_su_content_type(self):
        r = self.crear_reporte()
        img = Imagen.objects.create(reporte=r, contenido=PNG_FALSO, tipo_mime='image/png')
        response = self.client.get(reverse('imagen', args=[img.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response.content, PNG_FALSO)
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertIn('max-age', response['Cache-Control'])

    def test_imagen_inexistente_responde_404(self):
        response = self.client.get(reverse('imagen', args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SeedDemoTests(APITestCase):
    # El runner de pruebas pone DEBUG=False; el comando exige DEBUG=True.
    @override_settings(DEBUG=True)
    def test_es_idempotente(self):
        call_command('seed_demo', stdout=StringIO())
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Reporte.objects.count(), 11)
        self.assertEqual(set(Reporte.objects.values_list('zona', flat=True)),
                         {'centro', 'norte', 'sur', 'oriente', 'poniente'})

    @override_settings(DEBUG=True)
    def test_crea_reportes_ajenos_para_el_usuario_demo(self):
        call_command('seed_demo', stdout=StringIO())
        demo = Usuario.objects.get(email='demo@sarv.example')
        ajenos = Reporte.objects.exclude(usuario=demo)
        self.assertEqual(ajenos.count(), 3)
        self.assertTrue(ajenos.filter(estado='resuelto').exists())
        self.assertEqual(Denuncia.objects.filter(usuario=demo).count(), 1)
        self.assertEqual(Reaccion.objects.filter(usuario=demo).count(), 1)
        # Nadie reacciona a su propio reporte.
        self.assertFalse(Reaccion.objects.filter(usuario=F('reporte__usuario')).exists())

    @override_settings(DEBUG=True)
    def test_reset_no_borra_reportes_reales_con_el_mismo_titulo(self):
        call_command('seed_demo', stdout=StringIO())
        real = Usuario.objects.create_user('real@correo.mx', 'secreto1', nombre='Real')
        tipo = TipoIncidente.objects.get(nombre='Otro')
        Reporte.objects.create(
            usuario=real, tipo=tipo, tipo_otro='Semáforo', titulo='Semáforo apagado',
            descripcion='El semáforo no funciona desde ayer.', gravedad='leve',
            latitud=f'{CENTRO_LAT:.6f}', longitud=f'{CENTRO_LNG:.6f}', fecha_incidente=timezone.now(),
        )
        call_command('seed_demo', '--reset', stdout=StringIO())
        self.assertTrue(Reporte.objects.filter(usuario=real).exists())
        self.assertEqual(Reporte.objects.count(), 12)

    def test_requiere_debug(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo', stdout=StringIO())
