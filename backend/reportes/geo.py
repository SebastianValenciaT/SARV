"""Cliente de Nominatim (geocodificación de OpenStreetMap).

El navegador nunca llama a Nominatim: siempre pasa por este módulo, que aplica
la política de uso de la instancia pública:
- Máximo 1 petición por segundo en todo el servidor (candado + time.monotonic).
- User-Agent que identifica la app y un contacto (NOMINATIM_USER_AGENT en .env).
- Caché de 24 h: una búsqueda repetida no vuelve a llamar a Nominatim.
- Sin autocompletado: solo búsquedas puntuales (Enter o botón).

Limitación: el candado y la caché (LocMemCache) viven dentro de UN proceso.
Con varios workers en producción harían falta Redis y un candado compartido.
"""
import hashlib
import threading
import time

import requests
from django.conf import settings
from django.core.cache import cache

from .zonas import LAT_MAX, LAT_MIN, LNG_MAX, LNG_MIN, dentro_de_juarez

TIMEOUT_SEGUNDOS = 5
INTERVALO_MINIMO = 1.0               # segundos entre peticiones a Nominatim
CACHE_SEGUNDOS = 60 * 60 * 24        # 24 horas
SIN_RESULTADO = {}                   # se guarda en caché: "Nominatim respondió, pero vacío"

# Llaves de dirección que en México suelen traer la colonia, en orden de preferencia
LLAVES_COLONIA = ('neighbourhood', 'suburb', 'quarter', 'city_district')


class NominatimNoDisponible(Exception):
    """Nominatim no respondió, tardó demasiado o devolvió algo inválido."""


# Estado compartido por todos los hilos del proceso
_candado = threading.Lock()
_ultima_peticion = None


def _esperar_turno():
    """Duerme lo necesario para que pase al menos 1 s desde la petición anterior.

    Se llama con el candado tomado, así dos hilos no pueden calcular la espera a la vez.
    time.monotonic() es un reloj que nunca retrocede (a diferencia de la hora del sistema).
    """
    global _ultima_peticion
    if _ultima_peticion is not None:
        espera = INTERVALO_MINIMO - (time.monotonic() - _ultima_peticion)
        if espera > 0:
            time.sleep(espera)
    _ultima_peticion = time.monotonic()


def _consultar(ruta, params):
    """Hace la petición GET a Nominatim y devuelve el JSON. Nunca deja escapar errores de red."""
    url = f'{settings.NOMINATIM_BASE_URL.rstrip("/")}/{ruta}'
    headers = {'User-Agent': settings.NOMINATIM_USER_AGENT, 'Accept-Language': 'es'}
    with _candado:  # una petición a la vez en todo el proceso
        _esperar_turno()
        try:
            respuesta = requests.get(url, params=params, headers=headers, timeout=TIMEOUT_SEGUNDOS)
            respuesta.raise_for_status()  # 4xx/5xx de Nominatim -> excepción
            return respuesta.json()
        except (requests.RequestException, ValueError) as error:  # ValueError: JSON inválido
            raise NominatimNoDisponible(str(error)) from error


def direccion_corta(address, display_name=''):
    """Arma "Calle Número, Col. Colonia" con el `address` de Nominatim.

    Si no hay calle ni colonia, usa las dos primeras partes de display_name.
    """
    calle = address.get('road') or address.get('pedestrian')
    numero = address.get('house_number')
    colonia = next((address[llave] for llave in LLAVES_COLONIA if address.get(llave)), None)

    partes = []
    if calle:
        partes.append(f'{calle} {numero}' if numero else calle)
    if colonia:
        partes.append(colonia if colonia.lower().startswith('col') else f'Col. {colonia}')
    if partes:
        return ', '.join(partes)
    return ', '.join(display_name.split(', ')[:2])


def _clave_busqueda(texto):
    # Normaliza ("  AV.  Juárez " == "av. juárez") y usa un hash: la clave queda corta y sin espacios.
    normalizado = ' '.join(texto.lower().split())
    return 'geo:buscar:' + hashlib.sha256(normalizado.encode()).hexdigest()


def buscar(texto):
    """Dirección escrita -> {'lat', 'lng', 'direccion'} dentro de Juárez, o None si no hay resultado."""
    clave = _clave_busqueda(texto)
    en_cache = cache.get(clave)
    if en_cache is not None:
        return en_cache or None

    datos = _consultar('search', {
        'q': texto,
        'format': 'jsonv2',
        'addressdetails': 1,
        'limit': 1,
        'countrycodes': 'mx',
        # viewbox: lon_min, lat_max, lon_max, lat_min; bounded=1 = solo dentro del rectángulo
        'viewbox': f'{LNG_MIN},{LAT_MAX},{LNG_MAX},{LAT_MIN}',
        'bounded': 1,
    })

    resultado = SIN_RESULTADO
    try:
        for lugar in datos:
            lat, lng = float(lugar['lat']), float(lugar['lon'])
            if dentro_de_juarez(lat, lng):  # doble control: descartamos lo que caiga fuera
                direccion = direccion_corta(lugar.get('address', {}), lugar.get('display_name', ''))
                resultado = {'lat': lat, 'lng': lng, 'direccion': direccion}
                break
    except (KeyError, TypeError, ValueError) as error:  # respuesta con forma inesperada
        raise NominatimNoDisponible(str(error)) from error

    # Solo llegamos aquí si Nominatim respondió bien: los errores nunca se guardan en caché.
    cache.set(clave, resultado, CACHE_SEGUNDOS)
    return resultado or None


def inversa(lat, lng):
    """Coordenadas -> {'direccion'} corta, o None si Nominatim no encuentra nada."""
    # Redondear a 5 decimales (~1 m): pines casi en el mismo lugar comparten caché.
    lat, lng = round(lat, 5), round(lng, 5)
    clave = f'geo:inversa:{lat:.5f},{lng:.5f}'
    en_cache = cache.get(clave)
    if en_cache is not None:
        return en_cache or None

    datos = _consultar('reverse', {
        'lat': f'{lat:.5f}',
        'lon': f'{lng:.5f}',
        'format': 'jsonv2',
        'addressdetails': 1,
        'zoom': 18,  # nivel de detalle: calle / número
    })

    if not isinstance(datos, dict):
        raise NominatimNoDisponible('Respuesta inesperada de Nominatim.')
    # Sin resultado, Nominatim responde 200 con {"error": "Unable to geocode"}
    if 'error' in datos:
        resultado = SIN_RESULTADO
    else:
        direccion = direccion_corta(datos.get('address', {}), datos.get('display_name', ''))
        resultado = {'direccion': direccion} if direccion else SIN_RESULTADO

    cache.set(clave, resultado, CACHE_SEGUNDOS)
    return resultado or None
