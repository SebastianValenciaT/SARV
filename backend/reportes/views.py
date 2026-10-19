"""Vistas de solo lectura (públicas) de reportes, mapa e imágenes.

Las vistas genéricas de DRF (ListAPIView, RetrieveAPIView) ya saben listar,
paginar y devolver 404; solo les decimos qué queryset y qué serializer usar.
"""
from django.db.models import Count, F, Min, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .filters import filtrar_reportes
from .models import Imagen, Reaccion, Reporte, TipoIncidente
from .serializers import (
    ReporteDetailSerializer,
    ReporteListSerializer,
    ReporteMapaSerializer,
    TipoIncidenteSerializer,
)


def reportes_con_conteos():
    """Queryset base de lista y detalle, preparado para evitar consultas N+1.

    - select_related('tipo'): trae el tipo en la misma consulta (JOIN).
    - annotate(Count(...)): la base de datos cuenta reacciones e imágenes.
      distinct=True evita contar doble al unir dos tablas a la vez.
    - Prefetch de imágenes con only(): solo id, nunca el binario `contenido`.
    """
    return (
        Reporte.objects.select_related('tipo')
        .annotate(
            confirmaciones=Count('reacciones', distinct=True),
            total_imagenes=Count('imagenes', distinct=True),
        )
        .prefetch_related(Prefetch('imagenes', queryset=Imagen.objects.only('id', 'reporte_id')))
    )


class TipoListView(generics.ListAPIView):
    """GET /api/tipos/ — catálogo de tipos de incidente (sin paginar)."""

    queryset = TipoIncidente.objects.all()
    serializer_class = TipoIncidenteSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class ReporteListView(generics.ListAPIView):
    """GET /api/reportes/ — listado paginado, del más reciente al más antiguo."""

    serializer_class = ReporteListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = filtrar_reportes(reportes_con_conteos(), self.request.query_params)
        return queryset.order_by('-creado_en', '-id')


class ReporteDetailView(generics.RetrieveAPIView):
    """GET /api/reportes/{id}/ — detalle con reacciones y seguimiento."""

    serializer_class = ReporteDetailSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return reportes_con_conteos().select_related('usuario').annotate(
            reacciones_sin_resolver=Count(
                'reacciones', filter=Q(reacciones__tipo=Reaccion.Tipo.SIN_RESOLVER), distinct=True
            ),
            reacciones_resuelto=Count(
                'reacciones', filter=Q(reacciones__tipo=Reaccion.Tipo.RESUELTO), distinct=True
            ),
            # Fase 2 del seguimiento: primera reacción de alguien distinto al autor.
            primera_confirmacion=Min(
                'reacciones__creada_en', filter=~Q(reacciones__usuario=F('usuario'))
            ),
        )


class MapaReportesView(generics.ListAPIView):
    """GET /api/mapa/reportes/ — pines ligeros, solo `sin_resolver`, sin paginar."""

    serializer_class = ReporteMapaSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = Reporte.objects.select_related('tipo').filter(estado=Reporte.Estado.SIN_RESOLVER)
        return filtrar_reportes(queryset, self.request.query_params).order_by('-creado_en', '-id')


@api_view(['GET'])
@permission_classes([AllowAny])
def imagen_view(request, pk):
    """GET /api/imagenes/{id}/ — devuelve el binario de la imagen, no JSON."""
    imagen = get_object_or_404(Imagen.objects.only('contenido', 'tipo_mime'), pk=pk)
    # PostgreSQL devuelve el BinaryField como memoryview; bytes() lo convierte.
    response = HttpResponse(bytes(imagen.contenido), content_type=imagen.tipo_mime)
    # Las imágenes no se editan: el navegador puede guardarlas en caché un día.
    response['Cache-Control'] = 'public, max-age=86400'
    # Evita que el navegador "adivine" otro tipo de contenido distinto a tipo_mime.
    response['X-Content-Type-Options'] = 'nosniff'
    return response
