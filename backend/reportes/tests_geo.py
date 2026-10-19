"""Pruebas de geocodificación. NUNCA llaman a la red real: requests.get se simula
con unittest.mock.patch, y time.sleep también (para no esperar 1 s entre pruebas).
"""
from unittest import mock

import requests
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from . import geo
from .zonas import LAT_MAX, LAT_MIN, LNG_MAX, LNG_MIN

DIRECCION_JUAREZ = {
    'road': 'Avenida Tecnológico', 'house_number': '1340',
    'suburb': 'Partido Romero', 'city': 'Ciudad Juárez',
}
LUGAR_JUAREZ = {
    'lat': '31.710500', 'lon': '-106.424500',
    'display_name': 'Avenida Tecnológico, Partido Romero, Ciudad Juárez, Chihuahua, México',
    'address': DIRECCION_JUAREZ,
}
LUGAR_CHIHUAHUA = {   # Chihuahua capital: fuera de Juárez
    'lat': '28.632000', 'lon': '-106.069000',
    'display_name': 'Avenida Tecnológico, Chihuahua, México', 'address': {'road': 'Avenida Tecnológico'},
}


def respuesta(json_data, status_code=200):
    """Objeto que imita a requests.Response con lo que usa geo.py."""
    falsa = mock.Mock()
    falsa.status_code = status_code
    falsa.json.return_value = json_data
    if status_code >= 400:
        falsa.raise_for_status.side_effect = requests.HTTPError(f'{status_code} Error')
    return falsa


class BaseGeo(APITestCase):
    def setUp(self):
        cache.clear()                  # caché de geocodificación y contadores del throttle
        geo._ultima_peticion = None    # reinicia el espaciado de 1 s
        patcher_get = mock.patch('reportes.geo.requests.get')
        patcher_sleep = mock.patch('reportes.geo.time.sleep')
        self.get = patcher_get.start()
        self.sleep = patcher_sleep.start()
        self.addCleanup(patcher_get.stop)
        self.addCleanup(patcher_sleep.stop)

    def buscar(self, q):
        return self.client.get(reverse('geo-buscar'), {'q': q})

    def inversa(self, lat, lng):
        return self.client.get(reverse('geo-inversa'), {'lat': lat, 'lng': lng})


class BuscarTests(BaseGeo):
    def test_busqueda_exitosa(self):
        self.get.return_value = respuesta([LUGAR_JUAREZ])
        response = self.buscar('Av. Tecnológico 1340')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'lat': 31.7105, 'lng': -106.4245, 'direccion': 'Avenida Tecnológico 1340, Col. Partido Romero',
        })

    def test_parametros_que_exige_la_politica_de_nominatim(self):
        self.get.return_value = respuesta([LUGAR_JUAREZ])
        self.buscar('Av. Tecnológico')
        args, kwargs = self.get.call_args
        self.assertTrue(args[0].endswith('/search'))
        self.assertEqual(kwargs['timeout'], 5)
        self.assertIn('User-Agent', kwargs['headers'])
        params = kwargs['params']
        self.assertEqual(params['countrycodes'], 'mx')
        self.assertEqual(params['viewbox'], f'{LNG_MIN},{LAT_MAX},{LNG_MAX},{LAT_MIN}')
        self.assertEqual(params['bounded'], 1)
        self.assertEqual(params['limit'], 1)
        self.assertEqual(params['format'], 'jsonv2')
        self.assertEqual(params['addressdetails'], 1)

    def test_sin_resultado_responde_404(self):
        self.get.return_value = respuesta([])
        response = self.buscar('Calle que no existe')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Ciudad Juárez', response.data['detail'])

    def test_resultado_fuera_de_juarez_se_descarta(self):
        self.get.return_value = respuesta([LUGAR_CHIHUAHUA])
        response = self.buscar('Av. Tecnológico')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_q_invalido_responde_400_sin_llamar_a_nominatim(self):
        for q in ['', '   ', 'ab', 'x' * 201]:
            with self.subTest(q=q):
                response = self.buscar(q)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('q', response.data)
        self.assertEqual(self.client.get(reverse('geo-buscar')).status_code, status.HTTP_400_BAD_REQUEST)
        self.get.assert_not_called()

    def test_cache_evita_la_segunda_llamada(self):
        self.get.return_value = respuesta([LUGAR_JUAREZ])
        primera = self.buscar('Av. Tecnológico 1340')
        # Mismo texto con otras mayúsculas y espacios: misma clave de caché
        segunda = self.buscar('  av. tecnológico   1340 ')
        self.assertEqual(self.get.call_count, 1)
        self.assertEqual(primera.data, segunda.data)

    def test_resultado_vacio_tambien_se_guarda_en_cache(self):
        self.get.return_value = respuesta([])
        self.buscar('Calle que no existe')
        response = self.buscar('Calle que no existe')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.get.call_count, 1)


class InversaTests(BaseGeo):
    def test_inversa_exitosa_con_direccion_corta(self):
        self.get.return_value = respuesta({
            'display_name': 'Avenida Tecnológico, Partido Romero, Ciudad Juárez, Chihuahua, México',
            'address': DIRECCION_JUAREZ,
        })
        response = self.inversa('31.7105', '-106.4245')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'direccion': 'Avenida Tecnológico 1340, Col. Partido Romero'})
        self.assertTrue(self.get.call_args.args[0].endswith('/reverse'))

    def test_sin_resultado_responde_404(self):
        self.get.return_value = respuesta({'error': 'Unable to geocode'})
        self.assertEqual(self.inversa('31.7105', '-106.4245').status_code, status.HTTP_404_NOT_FOUND)

    def test_parametros_invalidos_o_fuera_de_juarez_responden_400(self):
        casos = [('abc', '-106.4'), ('31.7', ''), ('31.9', '-106.4'), ('28.63', '-106.07')]
        for lat, lng in casos:
            with self.subTest(lat=lat, lng=lng):
                self.assertEqual(self.inversa(lat, lng).status_code, status.HTTP_400_BAD_REQUEST)
        self.get.assert_not_called()

    def test_cache_por_coordenadas_redondeadas_a_5_decimales(self):
        self.get.return_value = respuesta({'address': DIRECCION_JUAREZ})
        self.inversa('31.7105001', '-106.4245001')
        self.inversa('31.7104999', '-106.4244999')   # redondea igual: 31.71050, -106.42450
        self.assertEqual(self.get.call_count, 1)


class DireccionCortaTests(APITestCase):
    def test_formatos(self):
        self.assertEqual(geo.direccion_corta({'road': 'Calle Ramón Corona'}), 'Calle Ramón Corona')
        self.assertEqual(geo.direccion_corta({'suburb': 'Centro'}), 'Col. Centro')
        self.assertEqual(geo.direccion_corta({'road': 'Calle 1', 'neighbourhood': 'Colonia Bellavista'}),
                         'Calle 1, Colonia Bellavista')
        self.assertEqual(geo.direccion_corta({}, 'Parque Central, Ciudad Juárez, México'),
                         'Parque Central, Ciudad Juárez')


class FallasDeNominatimTests(BaseGeo):
    def test_timeout_responde_503(self):
        self.get.side_effect = requests.Timeout('tardó más de 5 s')
        response = self.buscar('Av. Tecnológico')
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('detail', response.data)

    def test_error_de_red_responde_503(self):
        self.get.side_effect = requests.ConnectionError('sin red')
        self.assertEqual(self.inversa('31.7105', '-106.4245').status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_error_http_o_json_invalido_responde_503(self):
        self.get.return_value = respuesta(None, status_code=502)
        self.assertEqual(self.buscar('Av. Tecnológico').status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        roto = respuesta(None)
        roto.json.side_effect = ValueError('no es JSON')
        self.get.return_value = roto
        self.assertEqual(self.buscar('Av. Juárez').status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_los_errores_nunca_se_guardan_en_cache(self):
        self.get.side_effect = [requests.Timeout('lento'), respuesta([LUGAR_JUAREZ])]
        self.assertEqual(self.buscar('Av. Tecnológico').status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        # El reintento SÍ vuelve a llamar a Nominatim y ahora obtiene resultado
        self.assertEqual(self.buscar('Av. Tecnológico').status_code, status.HTTP_200_OK)
        self.assertEqual(self.get.call_count, 2)

        self.get.side_effect = [requests.ConnectionError('sin red'), respuesta({'address': DIRECCION_JUAREZ})]
        self.assertEqual(self.inversa('31.72', '-106.45').status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(self.inversa('31.72', '-106.45').status_code, status.HTTP_200_OK)


class PoliticaDeUsoTests(BaseGeo):
    def test_espacia_las_peticiones_un_segundo(self):
        self.get.return_value = respuesta([LUGAR_JUAREZ])
        self.buscar('Primera búsqueda')
        self.sleep.assert_not_called()          # la primera no espera
        self.buscar('Segunda búsqueda')         # llega enseguida: debe esperar casi 1 s
        self.sleep.assert_called_once()
        espera = self.sleep.call_args.args[0]
        self.assertTrue(0.9 < espera <= 1.0, espera)

    def test_limite_de_peticiones_por_ip(self):
        self.get.return_value = respuesta([LUGAR_JUAREZ])
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'geo': '2/min'}):
            self.assertEqual(self.buscar('Av. Tecnológico').status_code, status.HTTP_200_OK)
            self.assertEqual(self.buscar('Av. Tecnológico').status_code, status.HTTP_200_OK)
            self.assertEqual(self.buscar('Av. Tecnológico').status_code, status.HTTP_429_TOO_MANY_REQUESTS)
