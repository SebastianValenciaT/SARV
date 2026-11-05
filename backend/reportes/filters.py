"""Filtros por query params para los listados de reportes (lista y mapa).

Los parámetros se validan con un serializer: si llega un valor inválido
(por ejemplo ?zona=marte), DRF responde 400 con un mensaje legible.
"""
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from .models import Reporte

FECHAS = ['hoy', '7d', '30d']
# `expirado` no es un valor guardado: se calcula con la duración del tipo (models.py).
ESTADOS_FILTRO = [*Reporte.Estado.values, Reporte.ESTADO_EXPIRADO]


class FiltrosReporteSerializer(serializers.Serializer):
    # ListField lee todos los valores repetidos: ?tipo=1&tipo=3 -> [1, 3]
    tipo = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)
    zona = serializers.ChoiceField(choices=Reporte.Zona.choices, required=False, allow_blank=True)
    fecha = serializers.ChoiceField(choices=FECHAS, required=False, allow_blank=True)
    estado = serializers.ChoiceField(choices=ESTADOS_FILTRO, required=False, allow_blank=True)
    q = serializers.CharField(required=False, allow_blank=True, max_length=100)


def inicio_de_fecha(fecha):
    """Momento desde el que se cuentan los reportes para el filtro `fecha`."""
    ahora = timezone.now()
    if fecha == 'hoy':
        # Medianoche de hoy en la hora local (America/Ciudad_Juarez), no en UTC.
        return timezone.localtime(ahora).replace(hour=0, minute=0, second=0, microsecond=0)
    dias = 7 if fecha == '7d' else 30
    return ahora - timedelta(days=dias)  # ventana móvil: ahora menos N días


def filtrar_reportes(queryset, query_params):
    """Aplica al queryset los filtros válidos que vengan en la URL.

    Expiración: por defecto se ocultan los expirados (los resueltos nunca, gana
    "resuelto"). `estado=expirado` devuelve solo los expirados y `estado=sin_resolver`
    solo los vigentes sin resolver.
    """
    filtros = FiltrosReporteSerializer(data=query_params)
    filtros.is_valid(raise_exception=True)
    datos = filtros.validated_data

    ahora = timezone.now()   # un solo "ahora" para toda la consulta
    if datos.get('estado') == Reporte.ESTADO_EXPIRADO:
        queryset = queryset.expirados(ahora)
    else:
        queryset = queryset.no_expirados(ahora)
        if datos.get('estado'):
            queryset = queryset.filter(estado=datos['estado'])
    if datos.get('tipo'):
        queryset = queryset.filter(tipo_id__in=datos['tipo'])
    if datos.get('zona'):
        queryset = queryset.filter(zona=datos['zona'])
    if datos.get('fecha'):
        queryset = queryset.filter(fecha_incidente__gte=inicio_de_fecha(datos['fecha']))
    if datos.get('q'):
        # Q permite combinar condiciones con OR (|). icontains = "contiene", sin importar mayúsculas.
        queryset = queryset.filter(Q(titulo__icontains=datos['q']) | Q(direccion__icontains=datos['q']))
    return queryset
