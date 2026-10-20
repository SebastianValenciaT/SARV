"""Zona de un reporte, calculada a partir de las coordenadas del pin.

Regla del MVP: se toma un punto de referencia (el centro de la ciudad).
- A menos de RADIO_CENTRO_KM del punto -> "centro".
- Si no, se compara el desplazamiento este-oeste con el norte-sur y gana el mayor.

Los valores de abajo son APROXIMADOS y se calibran con puntos conocidos
(ver reportes/tests.py y docs/Modelo_datos_y_API.md, sección 4.3).
"""
import math

# Punto de referencia: centro de Ciudad Juárez (aprox., calibrar).
CENTRO_LAT = 31.7385
CENTRO_LNG = -106.4870
RADIO_CENTRO_KM = 2.5

# Rectángulo que contiene a Ciudad Juárez (RN-09). Aprox., ajustar si hace falta.
LAT_MIN, LAT_MAX = 31.50, 31.80
LNG_MIN, LNG_MAX = -106.70, -106.15

KM_POR_GRADO = 111.32


def zona_de(latitud, longitud):
    """Devuelve 'centro', 'norte', 'sur', 'oriente' o 'poniente'."""
    dy = (float(latitud) - CENTRO_LAT) * KM_POR_GRADO  # + = norte
    dx = (float(longitud) - CENTRO_LNG) * KM_POR_GRADO * math.cos(math.radians(CENTRO_LAT))  # + = oriente
    if math.hypot(dx, dy) <= RADIO_CENTRO_KM:
        return 'centro'
    if abs(dx) >= abs(dy):
        return 'oriente' if dx > 0 else 'poniente'
    return 'norte' if dy > 0 else 'sur'


def dentro_de_juarez(latitud, longitud):
    return LAT_MIN <= float(latitud) <= LAT_MAX and LNG_MIN <= float(longitud) <= LNG_MAX
